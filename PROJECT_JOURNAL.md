# Self-Help Notes Compiler Journal

This journal is the rebuild document for the project. If the source folder were lost but this document remained, the project can be recreated by following the problem statement, architecture, file layout, code responsibilities, and command history below.

## 1. Problem Being Solved

The folder started as a manual PDF manipulation workspace for lecture notes. The input PDFs are not normal text PDFs. They are mostly screenshots of handwritten or blackboard-style lecture boards, often dark backgrounds with light writing.

The real note-making problem has four important properties:

1. Lecture PDFs overlap.
   Consecutive classes often share repeated pages. For example, the last 10 pages of lecture 1 may also appear as the first 10 pages of lecture 2.

2. Repeated pages are not equally useful.
   A slide may be present but unattended/unannotated in one PDF, then attended and annotated in a later PDF. The final notes should keep the more useful annotated version.

3. Printing dark blackboard pages is painful.
   Black background with light writing consumes ink and prints poorly. These pages should be detected and inverted automatically.

4. Final output must be print-friendly.
   The desired output should keep only useful pages, preserve logical lecture order, place 4 slides on each PDF page, and split the final PDF into parts no larger than 20 MB.

The old workflow worked manually, but it required repeatedly entering page ranges, choosing whether to invert, merging, packing, compressing, and splitting by hand.

## 2. Original Repository State

Before automation, the source files were loose Python scripts:

- `invert_col.py`
  Manual script that asks whether to process each PDF, whether to keep or exclude page ranges, and whether to invert selected pages.

- `UP_4_pdf_print.py`
  Manual script that packs 4 source pages into 1 output page.

- `merge_pdf.py`
  Merges PDFs from a hard-coded folder in modification-time order.

- `find_duplicates.py`
  Merges PDFs from `INPUT` in modification-time order. Despite the name, it does not truly identify visual duplicates.

- `contrast.py`
  Converts pages to images and applies grayscale/contrast/binarization enhancement.

- `compress.py`
  Uses Ghostscript to compress PDFs in a hard-coded folder.

- `divide.py`
  Splits one hard-coded PDF into parts near 20 MB.

- `mail.py`
  Sends PDFs from a hard-coded folder by email. It currently contains a hard-coded Gmail app password and should not be used as-is. Rotate that credential if it was real.

The directory also contains many PDF files in folders such as `computer_networks`, `datawarehousing`, and `dsa_solutions`. These PDFs are treated as input/output data, not source code.

## 3. Git Safety Strategy

The user asked for a separate branch and a clean Git history before changing the system.

The project initially contained a broken empty `.git/` directory that was read-only inside the sandbox. It had no repository metadata, so the safe action was:

```bash
rm -rf /home/swaraj/sj_code/miscellaneous/pdf_manipulatorz/.git
git init /home/swaraj/sj_code/miscellaneous/pdf_manipulatorz
```

Then the initial branch was renamed:

```bash
git branch -m main
```

The first commit captured the old manual workflow without adding PDFs:

```bash
git add -A
git commit -m "Capture manual PDF workflow baseline"
```

Then the automation branch was created:

```bash
git checkout -b feature/auto-notes-compiler
```

The `.gitignore` intentionally excludes PDFs, output folders, temp folders, caches, and local environment files. This keeps Git history focused on source code and documentation.

## 4. Proposed Automated Solution

The new system is added beside the old scripts. The manual scripts remain untouched.

The automated workflow is:

1. Scan an input folder for lecture PDFs.
2. Ignore generated folders such as `op`, `OUTPUT`, `TEMP_OUTPUT`, `compiled`, and `review`.
3. Sort PDFs in lecture order using modification time, then natural filename order.
4. Render each PDF page as an image.
5. Detect dark-background blackboard pages.
6. Invert dark pages into print-friendly light-background pages.
7. Normalize each page into a small comparison image.
8. Compute visual hashes and image similarity.
9. Group repeated or near-repeated slides.
10. Within each duplicate group, select the best page version.
11. Prefer the page with higher detail/ink/edge score, because it is more likely to be annotated.
12. Preserve logical order using the first occurrence of each duplicate group.
13. Skip lightly annotated pages by default.
14. Write review reports so decisions can be audited.
15. Generate the final notes PDF with 4 slides per page.
16. Split final output into PDF parts of max 20 MB.

## 5. New File Layout

The automation adds these files:

```text
compile_notes.py
requirements.txt
notes_compiler/
  __init__.py
  cli.py
  image_tools.py
  pdf_tools.py
  pipeline.py
PROJECT_JOURNAL.md
```

### `requirements.txt`

Dependencies:

```text
Pillow>=10.0.0
PyMuPDF>=1.24.0
```

Pillow handles image normalization, inversion, thumbnails, and PDF output. PyMuPDF renders input PDF pages and splits output PDFs reliably.

### `compile_notes.py`

Small command-line entry point:

```python
from notes_compiler.cli import main
```

Run it with:

```bash
python3 compile_notes.py computer_networks --out compiled --review-thumbnails
```

### `notes_compiler/cli.py`

Defines the command-line interface.

Important options:

- `input_dir`: folder containing lecture PDFs.
- `--out`: output folder. Defaults to `compiled`.
- `--name`: optional base name for output files.
- `--max-size-mb`: final part size limit. Defaults to `20`.
- `--dpi`: render DPI. Defaults to `160`.
- `--dry-run`: analyze only, write reports, do not write final PDFs.
- `--keep-unannotated-unique`: keep unique pages even if the annotation/detail score is low.
- `--annotation-threshold`: minimum score for a page to count as useful.
- `--duplicate-threshold`: similarity threshold for grouping repeated slides.
- `--review-thumbnails`: write selected/skipped page thumbnails for manual checking.

### `notes_compiler/image_tools.py`

Handles page image analysis.

Main functions:

- `is_dark_background(image)`
  Detects whether a page has a dark background using grayscale mean and dark-pixel ratio.

- `normalize_display(image)`
  Converts the page to RGB, inverts it if dark, and applies mild contrast/sharpness enhancement.

- `comparison_image(image)`
  Creates a normalized 96x96 grayscale image for comparing pages.

- `dhash(image)` and `ahash(image)`
  Compute simple perceptual hashes without external hash libraries.

- `similarity(left, right)`
  Combines dHash similarity, aHash similarity, and pixel MSE similarity into one score.

- `ink_density(image)` and `edge_density(image)`
  Estimate how much visible writing/detail exists on the page.

- `analyze_page(image)`
  Produces:
  - print-ready display image
  - dark-background inversion flag
  - detail score
  - hashes
  - comparison image

The detail score is the current proxy for annotation usefulness:

```text
detail_score = ink_density * 0.65 + edge_density * 0.35
```

This is intentionally simple and auditable. Later, a vision model or embedding model can replace or augment it without changing the whole pipeline.

### `notes_compiler/pdf_tools.py`

Handles PDF discovery, rendering, writing, and splitting.

Main functions:

- `pdfs_in_lecture_order(input_dir)`
  Recursively finds PDFs while skipping generated folders.

- `render_pdf_pages(pdf_path, dpi)`
  Uses PyMuPDF to render each page into a PIL image.

- `write_four_up_pdf(images, output_path, dpi)`
  Places 4 selected slides onto each output PDF page in a 2x2 grid.

- `split_pdf_by_size(input_pdf, output_prefix, max_size_bytes)`
  Uses PyMuPDF to split output PDFs into parts below the configured size limit.

### `notes_compiler/pipeline.py`

Coordinates the full compiler.

Important data classes:

- `CompilerConfig`
  Runtime options from the CLI.

- `PageCandidate`
  One rendered PDF page plus analysis metadata.

- `PageGroup`
  A duplicate/near-duplicate slide group.

- `CompileResult`
  Summary returned after a run.

Main functions:

- `compile_notes(config)`
  Full pipeline entry point.

- `load_candidates(input_dir, dpi)`
  Renders all PDF pages and analyzes them.

- `group_candidates(candidates, duplicate_threshold)`
  Groups pages that look visually similar.

- `best_group_match(candidate, groups, duplicate_threshold)`
  Finds the most similar existing slide group.

- `is_better_candidate(candidate, current)`
  Chooses the better page version. Higher detail score wins; near-ties prefer later pages because annotations usually appear in later attended lectures.

- `select_pages(groups, config)`
  Selects best pages and skips duplicates or low-detail pages.

- `write_reports(...)`
  Writes:
  - `review/summary.json`
  - `review/page_decisions.csv`

- `write_review_thumbs(...)`
  Optionally writes selected/skipped thumbnails.

## 6. How To Recreate The Project

From an empty folder:

1. Create the old manual scripts if needed, or copy them from backup.
2. Create `.gitignore` with PDF/output/cache exclusions.
3. Initialize Git:

```bash
git init
git branch -m main
git add -A
git commit -m "Capture manual PDF workflow baseline"
git checkout -b feature/auto-notes-compiler
```

4. Add `requirements.txt`:

```text
Pillow>=10.0.0
PyMuPDF>=1.24.0
```

5. Create `compile_notes.py` as the CLI entry point.
6. Create the `notes_compiler` package with:
   - `cli.py`
   - `image_tools.py`
   - `pdf_tools.py`
   - `pipeline.py`
7. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

8. Validate syntax:

```bash
python3 -m compileall compile_notes.py notes_compiler
```

9. Run a dry-run audit first:

```bash
python3 compile_notes.py computer_networks --out compiled --dry-run --review-thumbnails
```

10. Inspect:

```text
compiled/computer_networks/review/summary.json
compiled/computer_networks/review/page_decisions.csv
compiled/computer_networks/review/selected/
compiled/computer_networks/review/skipped/
```

11. Tune thresholds if needed:

```bash
python3 compile_notes.py computer_networks \
  --out compiled \
  --dry-run \
  --review-thumbnails \
  --annotation-threshold 0.018 \
  --duplicate-threshold 0.80
```

12. Generate final PDFs:

```bash
python3 compile_notes.py computer_networks --out compiled --review-thumbnails
```

Expected final output:

```text
compiled/computer_networks/computer_networks_compiled_part_01.pdf
compiled/computer_networks/computer_networks_compiled_part_02.pdf
...
```

Each part should be at most 20 MB unless a single page itself exceeds the limit.

## 7. Quality Notes And Known Limitations

This first automated version is intentionally conservative and auditable.

Current duplicate detection uses perceptual hashes plus pixel similarity. It should catch many repeated screenshot slides, especially when the base slide is mostly the same. It may need threshold tuning for heavily annotated slides.

Current annotation detection uses detail score, not true semantic understanding. This means it can confuse dense printed/blackboard content with annotation. The review CSV and thumbnails are therefore important before trusting a full run.

The best future upgrade is to add optional vision embeddings:

- render normalized page images
- embed each page with a local or API vision model
- group by embedding similarity
- use a model or learned heuristic to choose annotated pages

That upgrade should be added behind an option, not forced into the default local pipeline.

## 8. Scaling Fix: Streaming Window Traversal

The first implementation loaded all rendered page images into memory before grouping and writing output. That is unsafe for large scanned PDF folders because each rendered page can be several megabytes in memory.

The compiler was changed to stream pages one at a time:

1. Render one page.
2. Analyze and normalize it.
3. Compare it only against a recent sliding window of groups.
4. Save the current best page image for each group to disk under `compiled/<name>/page_store/`.
5. Drop the large in-memory image before moving to the next page.
6. Delete temporary `page_store/` images after reports/thumbnails/final PDFs are written.

The key CLI options are:

```bash
--window-pages 120
```

Only compare with recent groups. This bounds comparison cost and memory. Increase it when overlap spans many pages; decrease it for faster tests.

```bash
--limit-pages 20
```

Stop after a small number of pages. This is the safe smoke-test mode and should be used before any full-folder run.

```bash
--keep-temp
```

Keep `page_store/` images for debugging. Do not use this for ordinary runs, because it can grow large. By default temporary page images are deleted automatically.

Safe smoke test command:

```bash
.venv/bin/python compile_notes.py computer_networks \
  --out compiled \
  --dry-run \
  --review-thumbnails \
  --limit-pages 20 \
  --window-pages 30 \
  --dpi 90
```

The test completed successfully with:

```text
Analyzed pages: 20
Selected pages: 4
Skipped pages: 16
Review report: compiled/computer_networks/review/summary.json
```

The output folder size after this test was about `1.4M`.

## 9. Commit History To Maintain

The intended clean history is:

```text
main
  Capture manual PDF workflow baseline

feature/auto-notes-compiler
  Add automated notes compiler pipeline
  Document automated notes compiler rebuild process
  Allow CLI help without PDF dependency
  Show friendly missing dependency errors
  Stream compiler with bounded window traversal
  Clean temporary page store after compiler runs
```

No remote is required at this stage.
