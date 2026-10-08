# Manual Notes Compiler Native App

This is the manual-first desktop workflow for screenshot/blackboard lecture PDFs.

It deliberately avoids automatic page skipping. The user reviews pages one by one, marks them selected/rejected, uses view-only inversion while selecting, proceeds to a final normalization stage, chooses final inversion/layout, and renders final PDF parts.

## Runtime Model

- Native C++/Qt 5 Widgets UI.
- Uses `pdfinfo` to count pages.
- Uses `pdftoppm` to render only one page at a time.
- Uses `QPdfWriter` to write final PDFs.
- Does not ingest an entire folder of rendered pages into memory.
- Keeps only one full-resolution preview and a small low-resolution thumbnail cache.
- Autosaves review sessions to `.manual_notes_autosave.json` in the opened folder.
- Writes each render into a timestamped output folder to avoid overwriting older outputs.

## Stages

1. Select pages.
   - Mark pages selected/rejected.
   - Toggle view inversion for readability.
   - The left list shows a working window: previous PDFs, current PDF, and future PDFs.
   - Future PDFs are lookup-only until you select/reject/invert a page or press "Activate PDF".
   - Use the right thumbnail strip to compare nearby pages without loading the whole folder.

2. Normalize selected pages.
   - Only selected pages are reviewed.
   - Toggle final inversion per page.
   - Use "Invert All Selected" or "Reset Final Invert" for consistent background.

3. Render final.
   - Choose 1/2/4 slides per page.
   - Render chunked PDF parts.
   - Open output folder after render.

## Shortcuts

- Right arrow: next page
- Left arrow: previous page
- `K`: select page
- `R`: reject page
- `I`: invert current page
- `Ctrl+Z`: undo last decision
- `Ctrl+Enter`: proceed from Select to Normalize
- `Ctrl+S`: save session
- `P`: pin current page for side-by-side comparison

## Working Window

The app scans page counts for all PDFs, but it does not render all pages.

Controls:

- `Back PDFs`: how many previous PDFs are visible.
- `Ahead PDFs`: how many future PDFs are visible.
- `Activate PDF`: mark the current PDF as part of the review session.
- `Select PDF`: select every page in the current PDF.
- `Reject PDF`: reject every page in the current PDF.
- `Invert PDF`: invert every page in the current PDF for the current stage.
- `Mark PDF Done`: mark the current PDF as reviewed.

Rows are marked:

- `[A]`: active PDF
- `[L]`: lookup-only PDF

If you select, reject, or invert a lookup page, that PDF is activated automatically. Final output order is always original PDF/page order, even if you jump around randomly.

## Build Locally

```bash
cmake -S native_app -B build/native_app
cmake --build build/native_app
./build/native_app/manual-notes-compiler
```

## Required System Packages

On Debian/Ubuntu-like systems:

```bash
sudo apt install qtbase5-dev poppler-utils cmake g++
```

## Packaging

Use:

```bash
./packaging/build_deb.sh
```

The `.deb` will be written to `dist/`.
