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

## Stages

1. Select pages.
   - Mark pages selected/rejected.
   - Toggle view inversion for readability.
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
