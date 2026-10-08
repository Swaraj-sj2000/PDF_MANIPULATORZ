# Manual GUI Workflow Plan

The automatic page-selection attempt is not reliable enough for real use yet. The safe product direction is now a manual-first desktop app with reversible decisions and bounded rendering.

## Current Product Direction

Use a native C++/Qt desktop app.

Why:

- Native GUI responsiveness.
- Lower overhead than a Python GUI.
- No browser/server lifecycle.
- Uses `pdfinfo` and `pdftoppm` from Poppler, which are mature and fast.
- Renders one page at a time, so large lecture folders do not blow up RAM.
- Uses Qt's `QPdfWriter` for final PDFs.

## Workflow

1. Open a folder containing lecture PDFs.
2. App scans PDF page counts and stores metadata only.
3. App displays a working window around the current PDF: lookback PDFs, current PDF, and lookahead PDFs.
4. User marks page as selected or rejected.
5. User toggles view inversion manually per page for readability.
6. Decisions are reversible with undo.
7. Session can be saved and loaded as JSON.
8. User proceeds to Normalize stage.
9. User chooses final inversion per selected page, or bulk inverts/resets selected pages.
10. User chooses output layout:
   - 1 slide per page
   - 2 slides per page
   - 4 slides per page
11. User renders final PDF parts.
12. App keeps memory bounded by rendering source pages one by one.

## Working Window Behavior

The app avoids the "too little future context" problem by showing PDF windows instead of tiny page windows.

- Default lookback: 1 PDF.
- Default lookahead: 4 PDFs.
- Future PDFs are lookup-only until touched.
- Selecting/rejecting/inverting any page in a lookup PDF activates that PDF.
- There is also an explicit "Activate PDF" button.
- Random navigation is allowed.
- Final output order remains source PDF order and page order.

Memory remains bounded because the app renders only:

- current full-resolution preview
- a small low-DPI thumbnail cache
- one page at a time during final rendering

## Important UX Gaps To Improve Next

These are not blockers for the first native app, but they matter for making it pleasant.

### Page Navigation

- Add jump-to-page.
- Add search/filter by PDF name.
- Add keyboard help.
- Add "select current and all until next PDF" for fast contiguous review.
- Add a bigger selected-page filmstrip when in Normalize stage.

### Batch Actions

- Select/reject all pages in a PDF.
- Invert all pages in a PDF.
- Apply inversion to a range.
- Mark a range as selected/rejected.

### Visual Review

- Add thumbnail strip for nearby pages. Initial prototype keeps only a small low-DPI window cached.
- Add side-by-side previous/current page comparison.
- Add zoom controls.
- Add fit-width and fit-page modes.

### Output Preview

- Preview the final 2-up/4-up collage page before rendering.
- Show estimated output part count.
- Show selected page count per source PDF.

### Safety

- Warn before rendering if no session was saved.
- Autosave session periodically.
- Keep a recovery session file.
- Show temp/output disk usage before rendering.

### Future Assistive Automation

Automation should assist, not decide:

- Suggest likely dark pages for inversion.
- Suggest likely duplicates.
- Suggest blank pages.
- Let the user accept/reject suggestions.

The app should not auto-delete pages until we have a proper feedback loop and enough reviewed examples.

## Container Strategy

The app is containerized with a pinned Ubuntu base image. The container installs:

- Qt 5 runtime/build tools
- Poppler utilities
- CMake/g++

The GUI runs through the host display using X11 volume forwarding.

Commands:

```bash
./scripts/build_container.sh
./scripts/run_container_gui.sh
```

Extract a `.deb` built inside the container:

```bash
./scripts/extract_deb_from_container.sh
```

If Docker cannot pull `ubuntu:24.04`, fix network/DNS or pre-load the base image.
