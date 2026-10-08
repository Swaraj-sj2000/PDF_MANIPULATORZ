import fitz  # PyMuPDF
from pathlib import Path
from PyPDF2 import PdfMerger
from tqdm import tqdm
from PIL import Image
import io

# --- User input ---
number_pages_input = input("Do you want to add page numbers to all PDFs? (y/n): ").strip().lower()
number_pages = number_pages_input == "y"

# --- Folders ---
input_folder = Path("/home/swaraj/sj_code/miscellaneous/pdf_manipulatorz/computer_networks/op")
temp_folder = Path("TEMP_OUTPUT")
final_output = "comp_net1.pdf"
temp_folder.mkdir(exist_ok=True)

# --- Compression settings ---
zoom = 0.7           # scale factor for each page
jpeg_quality = 75    # JPEG quality (0-100)

# --- Get PDFs in chronological order ---
pdf_files = sorted(input_folder.glob("*.pdf"), key=lambda x: x.stat().st_mtime)
temp_pdfs = []

global_page_counter = 1  # continuous numbering across all PDFs

for idx, pdf_file in enumerate(pdf_files, start=1):
    print(f"\nProcessing {idx}/{len(pdf_files)}: {pdf_file.name}")
    doc = fitz.open(pdf_file)
    new_doc = fitz.open()
    cols, rows = 2, 2
    page_width, page_height = doc[0].rect.width, doc[0].rect.height
    total_pages = len(doc)

    for i in tqdm(range(0, total_pages, 4), desc="Pages", unit="block"):
        new_page = new_doc.new_page(width=page_width, height=page_height)
        for j in range(4):
            if i + j >= total_pages:
                break
            src_page = doc[i + j]
            mat = fitz.Matrix(zoom, zoom)
            pix = src_page.get_pixmap(matrix=mat, alpha=False)

            # Convert Pixmap to PIL Image for JPEG compression
            img_bytes = pix.samples
            mode = "RGB" if pix.n < 4 else "RGBA"
            img = Image.frombytes(mode, [pix.width, pix.height], img_bytes)

            # Save to in-memory JPEG
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="JPEG", quality=jpeg_quality)
            buf.seek(0)

            # Calculate 2x2 grid position
            col = j % cols
            row = j // cols
            rect = fitz.Rect(
                col * page_width / 2,
                row * page_height / 2,
                (col + 1) * page_width / 2,
                (row + 1) * page_height / 2
            )
            new_page.insert_image(rect, stream=buf.read())

            # --- Add page number if enabled ---
            if number_pages:
                # small font at top-right corner of the inserted page
                text = str(global_page_counter)
                fontsize = 10  # adjust as needed
                # position relative to the page quadrant
                x0 = col * page_width / 2 + page_width / 2 - 20
                y0 = row * page_height / 2 + 10
                new_page.insert_text(
                    (x0, y0),
                    text,
                    fontsize=fontsize,
                    fontname="helv",
                    color=(0, 0, 0)  # black
                )
                global_page_counter += 1

    temp_pdf = temp_folder / f"processed_{idx:03d}.pdf"
    new_doc.save(temp_pdf)
    new_doc.close()
    doc.close()
    temp_pdfs.append(temp_pdf)
    print(f"Saved processed PDF: {temp_pdf.name}")

# --- Merge all processed PDFs ---
merger = PdfMerger()
for temp_pdf in temp_pdfs:
    merger.append(str(temp_pdf))
merger.write(final_output)
merger.close()
print(f"\nAll PDFs merged into: {final_output}")

# Optional cleanup
for temp_pdf in temp_pdfs:
    temp_pdf.unlink()
print("Temporary PDFs deleted.")
