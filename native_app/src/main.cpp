#include <QApplication>
#include <QBoxLayout>
#include <QComboBox>
#include <QDateTime>
#include <QDirIterator>
#include <QFile>
#include <QFileDialog>
#include <QFileInfo>
#include <QImage>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QKeySequence>
#include <QLabel>
#include <QListWidget>
#include <QMainWindow>
#include <QMessageBox>
#include <QPainter>
#include <QPageSize>
#include <QPdfWriter>
#include <QProcess>
#include <QProgressDialog>
#include <QPushButton>
#include <QShortcut>
#include <QSpinBox>
#include <QSplitter>
#include <QStatusBar>
#include <QTemporaryDir>
#include <QTextStream>
#include <QToolBar>

#include <algorithm>
#include <cmath>
#include <optional>

struct PageRef {
    QString pdfPath;
    QString pdfName;
    int pageNumber = 1;
};

struct Decision {
    bool selected = false;
    bool inverted = false;
};

struct UndoItem {
    int index = 0;
    Decision decision;
};

static QStringList excludedDirs()
{
    return {
        "/op/",
        "/OUTPUT/",
        "/TEMP_OUTPUT/",
        "/temp_pages/",
        "/__temp__/",
        "/compiled/",
        "/review/",
        "/COMPRESSED/",
        "/ENHANCED/"
    };
}

static bool isGeneratedPdf(const QString& path)
{
    const QString normalized = "/" + QDir::fromNativeSeparators(path);
    for (const QString& excluded : excludedDirs()) {
        if (normalized.contains(excluded)) {
            return true;
        }
    }
    return false;
}

static std::optional<int> pdfPageCount(const QString& pdfPath, QString* error)
{
    QProcess process;
    process.start("pdfinfo", {pdfPath});
    if (!process.waitForFinished(15000)) {
        if (error) {
            *error = "pdfinfo timed out for " + pdfPath;
        }
        return std::nullopt;
    }
    if (process.exitCode() != 0) {
        if (error) {
            *error = QString::fromUtf8(process.readAllStandardError());
        }
        return std::nullopt;
    }
    const QString output = QString::fromUtf8(process.readAllStandardOutput());
    for (const QString& line : output.split('\n')) {
        if (line.startsWith("Pages:")) {
            bool ok = false;
            const int pages = line.mid(QString("Pages:").size()).trimmed().toInt(&ok);
            if (ok) {
                return pages;
            }
        }
    }
    if (error) {
        *error = "Could not read page count from pdfinfo output.";
    }
    return std::nullopt;
}

static QImage renderPage(const PageRef& page, int dpi, bool inverted, QString* error)
{
    QTemporaryDir dir;
    if (!dir.isValid()) {
        if (error) {
            *error = "Could not create temporary render directory.";
        }
        return {};
    }

    const QString prefix = dir.path() + "/page";
    QProcess process;
    process.start("pdftoppm", {
        "-f", QString::number(page.pageNumber),
        "-l", QString::number(page.pageNumber),
        "-r", QString::number(dpi),
        "-jpeg",
        "-singlefile",
        page.pdfPath,
        prefix
    });
    if (!process.waitForFinished(30000)) {
        if (error) {
            *error = "pdftoppm timed out while rendering.";
        }
        return {};
    }
    if (process.exitCode() != 0) {
        if (error) {
            *error = QString::fromUtf8(process.readAllStandardError());
        }
        return {};
    }

    QImage image(prefix + ".jpg");
    if (image.isNull()) {
        if (error) {
            *error = "Rendered image could not be loaded.";
        }
        return {};
    }
    image = image.convertToFormat(QImage::Format_RGB888);
    if (inverted) {
        image.invertPixels(QImage::InvertRgb);
    }
    return image;
}

static QString humanSize(qint64 bytes)
{
    const QStringList units = {"B", "KB", "MB", "GB"};
    double value = static_cast<double>(bytes);
    int unit = 0;
    while (value >= 1024.0 && unit < units.size() - 1) {
        value /= 1024.0;
        ++unit;
    }
    return QString::number(value, 'f', 1) + " " + units[unit];
}

class MainWindow : public QMainWindow {
public:
    MainWindow()
    {
        setWindowTitle("Manual Notes Compiler");
        resize(1220, 780);
        buildUi();
        bindShortcuts();
        setStatus("Choose a folder to begin.");
    }

private:
    QListWidget* list = nullptr;
    QLabel* preview = nullptr;
    QLabel* pageStatus = nullptr;
    QSpinBox* dpiSpin = nullptr;
    QSpinBox* maxMbSpin = nullptr;
    QSpinBox* chunkSlidesSpin = nullptr;
    QComboBox* layoutCombo = nullptr;

    QString inputDir;
    QVector<PageRef> pages;
    QVector<Decision> decisions;
    QVector<UndoItem> undoStack;
    int currentIndex = 0;

    void buildUi()
    {
        auto* root = new QWidget(this);
        auto* rootLayout = new QVBoxLayout(root);
        rootLayout->setContentsMargins(10, 10, 10, 10);

        auto* toolbar = new QToolBar(this);
        toolbar->setMovable(false);
        addToolBar(toolbar);

        auto* openButton = new QPushButton("Open Folder");
        auto* saveButton = new QPushButton("Save Session");
        auto* loadButton = new QPushButton("Load Session");
        auto* exportButton = new QPushButton("Render Final");
        toolbar->addWidget(openButton);
        toolbar->addWidget(saveButton);
        toolbar->addWidget(loadButton);
        toolbar->addSeparator();
        toolbar->addWidget(new QLabel("Layout "));
        layoutCombo = new QComboBox();
        layoutCombo->addItem("1 slide", 1);
        layoutCombo->addItem("2 slides", 2);
        layoutCombo->addItem("4 slides", 4);
        layoutCombo->setCurrentIndex(2);
        toolbar->addWidget(layoutCombo);
        toolbar->addSeparator();
        toolbar->addWidget(new QLabel("DPI "));
        dpiSpin = new QSpinBox();
        dpiSpin->setRange(72, 220);
        dpiSpin->setValue(110);
        toolbar->addWidget(dpiSpin);
        toolbar->addWidget(new QLabel(" Max MB "));
        maxMbSpin = new QSpinBox();
        maxMbSpin->setRange(5, 100);
        maxMbSpin->setValue(20);
        toolbar->addWidget(maxMbSpin);
        toolbar->addWidget(new QLabel(" Slides/try "));
        chunkSlidesSpin = new QSpinBox();
        chunkSlidesSpin->setRange(4, 500);
        chunkSlidesSpin->setValue(80);
        toolbar->addWidget(chunkSlidesSpin);
        toolbar->addSeparator();
        toolbar->addWidget(exportButton);

        auto* splitter = new QSplitter();
        list = new QListWidget();
        list->setMinimumWidth(360);
        splitter->addWidget(list);

        preview = new QLabel("No page loaded");
        preview->setAlignment(Qt::AlignCenter);
        preview->setMinimumSize(500, 420);
        preview->setStyleSheet("background: #202020; color: #dddddd;");
        splitter->addWidget(preview);
        splitter->setStretchFactor(1, 1);
        rootLayout->addWidget(splitter, 1);

        auto* controls = new QHBoxLayout();
        auto* prevButton = new QPushButton("Prev");
        auto* nextButton = new QPushButton("Next");
        auto* selectButton = new QPushButton("Select");
        auto* rejectButton = new QPushButton("Reject");
        auto* invertButton = new QPushButton("Invert");
        auto* undoButton = new QPushButton("Undo");
        pageStatus = new QLabel("0 / 0");
        controls->addWidget(prevButton);
        controls->addWidget(nextButton);
        controls->addSpacing(12);
        controls->addWidget(selectButton);
        controls->addWidget(rejectButton);
        controls->addWidget(invertButton);
        controls->addSpacing(12);
        controls->addWidget(undoButton);
        controls->addStretch(1);
        controls->addWidget(pageStatus);
        rootLayout->addLayout(controls);

        setCentralWidget(root);

        connect(openButton, &QPushButton::clicked, this, [this]() { openFolder(); });
        connect(saveButton, &QPushButton::clicked, this, [this]() { saveSession(); });
        connect(loadButton, &QPushButton::clicked, this, [this]() { loadSession(); });
        connect(exportButton, &QPushButton::clicked, this, [this]() { exportFinal(); });
        connect(prevButton, &QPushButton::clicked, this, [this]() { previousPage(); });
        connect(nextButton, &QPushButton::clicked, this, [this]() { nextPage(); });
        connect(selectButton, &QPushButton::clicked, this, [this]() { selectPage(); });
        connect(rejectButton, &QPushButton::clicked, this, [this]() { rejectPage(); });
        connect(invertButton, &QPushButton::clicked, this, [this]() { toggleInvert(); });
        connect(undoButton, &QPushButton::clicked, this, [this]() { undo(); });
        connect(list, &QListWidget::currentRowChanged, this, [this](int row) {
            if (row >= 0 && row < pages.size()) {
                currentIndex = row;
                updatePreview();
            }
        });
        connect(dpiSpin, qOverload<int>(&QSpinBox::valueChanged), this, [this]() { updatePreview(); });
    }

    void bindShortcuts()
    {
        new QShortcut(QKeySequence(Qt::Key_Left), this, [this]() { previousPage(); });
        new QShortcut(QKeySequence(Qt::Key_Right), this, [this]() { nextPage(); });
        new QShortcut(QKeySequence(Qt::Key_K), this, [this]() { selectPage(); });
        new QShortcut(QKeySequence(Qt::Key_R), this, [this]() { rejectPage(); });
        new QShortcut(QKeySequence(Qt::Key_I), this, [this]() { toggleInvert(); });
        new QShortcut(QKeySequence::Undo, this, [this]() { undo(); });
    }

    void setStatus(const QString& text)
    {
        statusBar()->showMessage(text);
    }

    void openFolder()
    {
        const QString folder = QFileDialog::getExistingDirectory(this, "Choose folder with lecture PDFs");
        if (folder.isEmpty()) {
            return;
        }
        scanFolder(folder);
    }

    void scanFolder(const QString& folder)
    {
        setStatus("Scanning PDFs...");
        QApplication::setOverrideCursor(Qt::WaitCursor);
        QVector<QFileInfo> pdfs;
        QDirIterator it(folder, {"*.pdf", "*.PDF"}, QDir::Files, QDirIterator::Subdirectories);
        while (it.hasNext()) {
            it.next();
            const QFileInfo info = it.fileInfo();
            if (!isGeneratedPdf(info.absoluteFilePath())) {
                pdfs.push_back(info);
            }
        }
        std::sort(pdfs.begin(), pdfs.end(), [](const QFileInfo& left, const QFileInfo& right) {
            if (left.lastModified() == right.lastModified()) {
                return left.fileName() < right.fileName();
            }
            return left.lastModified() < right.lastModified();
        });

        QVector<PageRef> scanned;
        for (const QFileInfo& info : pdfs) {
            QString error;
            const auto count = pdfPageCount(info.absoluteFilePath(), &error);
            if (!count) {
                QApplication::restoreOverrideCursor();
                QMessageBox::warning(this, "PDF skipped", info.fileName() + "\n" + error);
                QApplication::setOverrideCursor(Qt::WaitCursor);
                continue;
            }
            for (int page = 1; page <= *count; ++page) {
                scanned.push_back({info.absoluteFilePath(), info.fileName(), page});
            }
        }
        QApplication::restoreOverrideCursor();

        inputDir = folder;
        pages = scanned;
        decisions = QVector<Decision>(pages.size());
        undoStack.clear();
        currentIndex = 0;
        refreshList();
        updatePreview();
        setStatus(QString("Loaded %1 pages from %2").arg(pages.size()).arg(folder));
    }

    QString rowLabel(int index) const
    {
        const Decision decision = decisions.value(index);
        const PageRef page = pages.value(index);
        const QString mark = decision.selected ? "✓" : "×";
        const QString inv = decision.inverted ? " inv" : "";
        return QString("%1%2  %3  %4  p%5")
            .arg(mark, inv)
            .arg(index + 1, 4, 10, QChar('0'))
            .arg(page.pdfName)
            .arg(page.pageNumber);
    }

    void refreshList()
    {
        list->clear();
        for (int i = 0; i < pages.size(); ++i) {
            list->addItem(rowLabel(i));
        }
        if (!pages.isEmpty()) {
            list->setCurrentRow(0);
        }
    }

    void refreshRow(int index)
    {
        if (index < 0 || index >= list->count()) {
            return;
        }
        list->item(index)->setText(rowLabel(index));
        list->setCurrentRow(index);
    }

    void updatePreview()
    {
        if (pages.isEmpty()) {
            preview->setText("No page loaded");
            pageStatus->setText("0 / 0");
            return;
        }
        QString error;
        QImage image = renderPage(pages[currentIndex], dpiSpin->value(), decisions[currentIndex].inverted, &error);
        if (image.isNull()) {
            preview->setText("Render failed");
            setStatus(error);
            return;
        }
        const QPixmap pixmap = QPixmap::fromImage(image).scaled(
            preview->size() - QSize(20, 20),
            Qt::KeepAspectRatio,
            Qt::SmoothTransformation
        );
        preview->setPixmap(pixmap);
        const int selected = std::count_if(decisions.begin(), decisions.end(), [](const Decision& item) {
            return item.selected;
        });
        pageStatus->setText(QString("%1 / %2 | selected %3").arg(currentIndex + 1).arg(pages.size()).arg(selected));
        setStatus(QString("%1 page %2").arg(pages[currentIndex].pdfName).arg(pages[currentIndex].pageNumber));
    }

    void snapshot()
    {
        if (currentIndex >= 0 && currentIndex < decisions.size()) {
            undoStack.push_back({currentIndex, decisions[currentIndex]});
        }
    }

    void selectPage()
    {
        if (pages.isEmpty()) {
            return;
        }
        snapshot();
        decisions[currentIndex].selected = true;
        refreshRow(currentIndex);
        nextPage();
    }

    void rejectPage()
    {
        if (pages.isEmpty()) {
            return;
        }
        snapshot();
        decisions[currentIndex].selected = false;
        refreshRow(currentIndex);
        nextPage();
    }

    void toggleInvert()
    {
        if (pages.isEmpty()) {
            return;
        }
        snapshot();
        decisions[currentIndex].inverted = !decisions[currentIndex].inverted;
        refreshRow(currentIndex);
        updatePreview();
    }

    void undo()
    {
        if (undoStack.isEmpty()) {
            return;
        }
        const UndoItem item = undoStack.takeLast();
        if (item.index >= 0 && item.index < decisions.size()) {
            currentIndex = item.index;
            decisions[item.index] = item.decision;
            refreshRow(item.index);
            updatePreview();
        }
    }

    void previousPage()
    {
        if (pages.isEmpty()) {
            return;
        }
        currentIndex = std::max(0, currentIndex - 1);
        list->setCurrentRow(currentIndex);
        updatePreview();
    }

    void nextPage()
    {
        if (pages.isEmpty()) {
            return;
        }
        currentIndex = std::min(pages.size() - 1, currentIndex + 1);
        list->setCurrentRow(currentIndex);
        updatePreview();
    }

    void saveSession()
    {
        if (pages.isEmpty()) {
            QMessageBox::information(this, "Nothing to save", "Open a folder first.");
            return;
        }
        const QString path = QFileDialog::getSaveFileName(this, "Save session", "", "Notes session (*.json)");
        if (path.isEmpty()) {
            return;
        }
        QJsonObject root;
        root["input_dir"] = inputDir;
        QJsonArray pageArray;
        for (const PageRef& page : pages) {
            QJsonObject item;
            item["pdf_path"] = page.pdfPath;
            item["pdf_name"] = page.pdfName;
            item["page_number"] = page.pageNumber;
            pageArray.push_back(item);
        }
        QJsonArray decisionArray;
        for (const Decision& decision : decisions) {
            QJsonObject item;
            item["selected"] = decision.selected;
            item["inverted"] = decision.inverted;
            decisionArray.push_back(item);
        }
        root["pages"] = pageArray;
        root["decisions"] = decisionArray;
        QFile file(path);
        if (!file.open(QIODevice::WriteOnly | QIODevice::Truncate)) {
            QMessageBox::warning(this, "Save failed", file.errorString());
            return;
        }
        file.write(QJsonDocument(root).toJson(QJsonDocument::Indented));
        setStatus("Saved session: " + path);
    }

    void loadSession()
    {
        const QString path = QFileDialog::getOpenFileName(this, "Load session", "", "Notes session (*.json)");
        if (path.isEmpty()) {
            return;
        }
        QFile file(path);
        if (!file.open(QIODevice::ReadOnly)) {
            QMessageBox::warning(this, "Load failed", file.errorString());
            return;
        }
        const QJsonDocument document = QJsonDocument::fromJson(file.readAll());
        const QJsonObject root = document.object();
        QVector<PageRef> loadedPages;
        for (const QJsonValue& value : root["pages"].toArray()) {
            const QJsonObject item = value.toObject();
            loadedPages.push_back({
                item["pdf_path"].toString(),
                item["pdf_name"].toString(),
                item["page_number"].toInt()
            });
        }
        QVector<Decision> loadedDecisions;
        for (const QJsonValue& value : root["decisions"].toArray()) {
            const QJsonObject item = value.toObject();
            loadedDecisions.push_back({item["selected"].toBool(), item["inverted"].toBool()});
        }
        if (loadedDecisions.size() != loadedPages.size()) {
            loadedDecisions = QVector<Decision>(loadedPages.size());
        }
        inputDir = root["input_dir"].toString();
        pages = loadedPages;
        decisions = loadedDecisions;
        undoStack.clear();
        currentIndex = 0;
        refreshList();
        updatePreview();
        setStatus("Loaded session: " + path);
    }

    QVector<int> selectedIndexes() const
    {
        QVector<int> selected;
        for (int i = 0; i < decisions.size(); ++i) {
            if (decisions[i].selected) {
                selected.push_back(i);
            }
        }
        return selected;
    }

    void exportFinal()
    {
        if (pages.isEmpty()) {
            QMessageBox::information(this, "Nothing to render", "Open a folder first.");
            return;
        }
        const QVector<int> selected = selectedIndexes();
        if (selected.isEmpty()) {
            QMessageBox::information(this, "No selected pages", "Select at least one page.");
            return;
        }
        const QString outputDir = QFileDialog::getExistingDirectory(this, "Choose output folder");
        if (outputDir.isEmpty()) {
            return;
        }

        QProgressDialog progress("Rendering selected pages...", "Cancel", 0, selected.size(), this);
        progress.setWindowModality(Qt::ApplicationModal);
        progress.show();

        QStringList outputs;
        int start = 0;
        int part = 1;
        int chunkSize = std::min(chunkSlidesSpin->value(), selected.size());
        const qint64 maxBytes = static_cast<qint64>(maxMbSpin->value()) * 1024 * 1024;
        while (start < selected.size()) {
            if (progress.wasCanceled()) {
                break;
            }
            const int count = std::min(chunkSize, selected.size() - start);
            const QString path = QString("%1/%2_compiled_part_%3.pdf")
                .arg(outputDir)
                .arg(QFileInfo(inputDir).fileName().replace(' ', '_'))
                .arg(part, 2, 10, QChar('0'));
            QString error;
            if (!writePart(selected, start, count, path, &progress, &error)) {
                QMessageBox::warning(this, "Render failed", error);
                return;
            }
            const qint64 size = QFileInfo(path).size();
            if (size > maxBytes && count > layoutCombo->currentData().toInt()) {
                QFile::remove(path);
                chunkSize = std::max(layoutCombo->currentData().toInt(), count / 2);
                continue;
            }
            outputs.push_back(path + " (" + humanSize(size) + ")");
            start += count;
            ++part;
            if (size < maxBytes / 2 && chunkSize < chunkSlidesSpin->value()) {
                chunkSize = std::min(chunkSlidesSpin->value(), chunkSize + layoutCombo->currentData().toInt());
            }
        }
        progress.close();
        if (!outputs.isEmpty()) {
            QMessageBox::information(this, "Render complete", outputs.join("\n"));
            setStatus(QString("Rendered %1 part(s).").arg(outputs.size()));
        }
    }

    bool writePart(
        const QVector<int>& selected,
        int start,
        int count,
        const QString& outputPath,
        QProgressDialog* progress,
        QString* error)
    {
        const int layout = layoutCombo->currentData().toInt();
        const int dpi = dpiSpin->value();
        QImage first = renderPage(pages[selected[start]], dpi, decisions[selected[start]].inverted, error);
        if (first.isNull()) {
            return false;
        }

        QPdfWriter writer(outputPath);
        writer.setResolution(dpi);
        const QSizeF pageSizeMm(
            first.width() * 25.4 / dpi,
            first.height() * 25.4 / dpi
        );
        writer.setPageSize(QPageSize(pageSizeMm, QPageSize::Millimeter));
        writer.setPageMargins(QMarginsF(0, 0, 0, 0));

        QPainter painter(&writer);
        if (!painter.isActive()) {
            if (error) {
                *error = "Could not open PDF writer.";
            }
            return false;
        }

        for (int offset = 0; offset < count; ++offset) {
            if (progress && progress->wasCanceled()) {
                break;
            }
            if (offset > 0 && offset % layout == 0) {
                writer.newPage();
            }
            const int pageIndex = selected[start + offset];
            QImage image;
            if (offset == 0) {
                image = first;
            } else {
                image = renderPage(pages[pageIndex], dpi, decisions[pageIndex].inverted, error);
                if (image.isNull()) {
                    return false;
                }
            }
            const QRect target = slotRect(offset % layout, layout, writer.width(), writer.height(), image.size());
            painter.drawImage(target, image);
            if (progress) {
                progress->setValue(progress->value() + 1);
                QApplication::processEvents();
            }
        }
        painter.end();
        return true;
    }

    static QRect slotRect(int slot, int layout, int pageWidth, int pageHeight, const QSize& imageSize)
    {
        int cellX = 0;
        int cellY = 0;
        int cellW = pageWidth;
        int cellH = pageHeight;
        if (layout == 2) {
            cellH = pageHeight / 2;
            cellY = slot * cellH;
        } else if (layout == 4) {
            cellW = pageWidth / 2;
            cellH = pageHeight / 2;
            cellX = (slot % 2) * cellW;
            cellY = (slot / 2) * cellH;
        }

        QSize fitted = imageSize;
        fitted.scale(cellW, cellH, Qt::KeepAspectRatio);
        return QRect(
            cellX + (cellW - fitted.width()) / 2,
            cellY + (cellH - fitted.height()) / 2,
            fitted.width(),
            fitted.height()
        );
    }
};

int main(int argc, char** argv)
{
    QApplication app(argc, argv);
    MainWindow window;
    window.show();
    return app.exec();
}
