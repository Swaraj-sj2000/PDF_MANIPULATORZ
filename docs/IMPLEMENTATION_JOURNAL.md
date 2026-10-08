# Implementation Journal

This journal records the practical evolution of the project after the original automation attempt.

## Manual GUI Pivot

The automatic duplicate/annotation selector was not reliable enough for handwritten blackboard PDFs. It grouped unrelated blackboard pages and made selection feel random.

The project pivoted to a manual-first native app:

- C++/Qt 5 Widgets UI.
- Poppler CLI tools for PDF metadata/rendering.
- No bulk rendered-page ingestion.
- One full preview at a time.
- Small low-DPI thumbnail cache.
- Chunked final rendering.

## Working Window Model

The user needs to look ahead across lecture overlap. A tiny page window is not enough.

Implemented model:

- Scan all PDFs for page counts only.
- Keep all page decisions as lightweight metadata.
- Show a working window around the current PDF:
  - previous PDFs
  - current PDF
  - future PDFs
- Future PDFs are lookup-only until touched.
- Selecting/rejecting/inverting a lookup PDF activates it.
- Output order always remains original PDF/page order.

## Staged Workflow

The app separates:

1. Selection stage.
   View pages, select/reject, and use view inversion for readability.

2. Normalize stage.
   Review only selected pages and decide final inversion.

3. Render stage.
   Export 1/2/4-up PDF parts.

This prevents view-time inversion from accidentally becoming final-output inversion.

## Daily-Use Reliability Pass

Added:

- startup dependency check for `pdfinfo` and `pdftoppm`
- autosave every 60 seconds to `.manual_notes_autosave.json`
- recovery prompt when reopening a folder with autosave data
- PDF-level actions:
  - activate PDF
  - select PDF
  - reject PDF
  - invert PDF
  - mark PDF done
  - previous/next PDF
- pin current page for side-by-side comparison
- zoom control
- timestamped render output folders to prevent overwrite
- generated PDF open button
- output folder open button
- `selected_pages_report.csv` for every render
- logo drop-zone at `assets/logo_dropzone/`

## Rebuild Commands

Native build:

```bash
cmake --build build/native_app_release --parallel
```

Debian package:

```bash
./packaging/build_deb.sh
```

Run app:

```bash
./build/native_app_release/manual-notes-compiler
```

## Remaining Future Improvements

- true async thumbnail worker queue
- jump-to-page/search
- explicit keyboard help dialog
- range actions
- output collage preview before render
- proper icon integration from `assets/logo_dropzone/`
- CI/release workflow
