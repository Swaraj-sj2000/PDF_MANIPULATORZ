from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .image_tools import PageAnalysis, analyze_page, save_thumbnail, similarity
from .pdf_tools import max_size_bytes, pdfs_in_lecture_order, render_pdf_pages, split_pdf_by_size, write_four_up_pdf


@dataclass(frozen=True)
class CompilerConfig:
    input_dir: Path
    output_dir: Path
    output_name: str | None = None
    max_size_mb: float = 20.0
    dpi: int = 160
    dry_run: bool = False
    keep_unannotated_unique: bool = False
    annotation_threshold: float = 0.022
    duplicate_threshold: float = 0.82
    write_review_thumbnails: bool = False


@dataclass
class PageCandidate:
    id: str
    pdf_path: Path
    pdf_name: str
    page_number: int
    order_index: int
    display_image: Image.Image
    analysis: PageAnalysis


@dataclass
class PageGroup:
    group_id: int
    first_order_index: int
    best: PageCandidate
    members: list[PageCandidate]


@dataclass(frozen=True)
class CompileResult:
    total_pages: int
    selected_pages: int
    skipped_pages: int
    report_path: Path
    output_parts: list[Path]


def compile_notes(config: CompilerConfig) -> CompileResult:
    input_dir = config.input_dir.resolve()
    output_name = config.output_name or input_dir.name
    run_dir = config.output_dir.resolve() / output_name
    review_dir = run_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)

    candidates = load_candidates(input_dir, config.dpi)
    groups = group_candidates(candidates, config.duplicate_threshold)
    selected, skipped = select_pages(groups, config)

    report_path = write_reports(
        run_dir=run_dir,
        review_dir=review_dir,
        candidates=candidates,
        groups=groups,
        selected=selected,
        skipped=skipped,
        config=config,
    )

    if config.write_review_thumbnails:
        write_review_thumbs(review_dir, selected, skipped)

    output_parts: list[Path] = []
    if selected and not config.dry_run:
        temp_pdf = run_dir / f"{output_name}_compiled_full.pdf"
        write_four_up_pdf([page.display_image for page in selected], temp_pdf, dpi=config.dpi)
        output_parts = split_pdf_by_size(
            temp_pdf,
            run_dir / f"{output_name}_compiled",
            max_size_bytes(config.max_size_mb),
        )

    return CompileResult(
        total_pages=len(candidates),
        selected_pages=len(selected),
        skipped_pages=len(skipped),
        report_path=report_path,
        output_parts=output_parts,
    )


def load_candidates(input_dir: Path, dpi: int) -> list[PageCandidate]:
    pdfs = pdfs_in_lecture_order(input_dir)
    candidates: list[PageCandidate] = []
    for pdf_path in pdfs:
        for page_number, raw_image in render_pdf_pages(pdf_path, dpi=dpi):
            display, analysis = analyze_page(raw_image)
            order_index = len(candidates)
            candidates.append(PageCandidate(
                id=f"{order_index + 1:05d}",
                pdf_path=pdf_path,
                pdf_name=pdf_path.name,
                page_number=page_number,
                order_index=order_index,
                display_image=display,
                analysis=analysis,
            ))
    return candidates


def group_candidates(candidates: list[PageCandidate], duplicate_threshold: float) -> list[PageGroup]:
    groups: list[PageGroup] = []
    for candidate in candidates:
        match = best_group_match(candidate, groups, duplicate_threshold)
        if match is None:
            groups.append(PageGroup(
                group_id=len(groups) + 1,
                first_order_index=candidate.order_index,
                best=candidate,
                members=[candidate],
            ))
            continue

        match.members.append(candidate)
        if is_better_candidate(candidate, match.best):
            match.best = candidate
    return groups


def best_group_match(
    candidate: PageCandidate,
    groups: list[PageGroup],
    duplicate_threshold: float,
) -> PageGroup | None:
    best_score = 0.0
    best_group: PageGroup | None = None
    for group in groups:
        representative = group.best.analysis
        score = similarity(candidate.analysis, representative)
        if score > best_score:
            best_score = score
            best_group = group
    if best_score >= duplicate_threshold:
        return best_group
    return None


def is_better_candidate(candidate: PageCandidate, current: PageCandidate) -> bool:
    detail_delta = candidate.analysis.detail_score - current.analysis.detail_score
    if detail_delta > 0.004:
        return True
    if abs(detail_delta) <= 0.004:
        return candidate.order_index > current.order_index
    return False


def select_pages(
    groups: list[PageGroup],
    config: CompilerConfig,
) -> tuple[list[PageCandidate], list[PageCandidate]]:
    selected: list[PageCandidate] = []
    skipped: list[PageCandidate] = []
    for group in sorted(groups, key=lambda item: item.first_order_index):
        best = group.best
        annotated_enough = best.analysis.detail_score >= config.annotation_threshold
        if annotated_enough or config.keep_unannotated_unique:
            selected.append(best)
        else:
            skipped.append(best)

        for member in group.members:
            if member is not best:
                skipped.append(member)
    return selected, sorted(skipped, key=lambda item: item.order_index)


def write_reports(
    run_dir: Path,
    review_dir: Path,
    candidates: list[PageCandidate],
    groups: list[PageGroup],
    selected: list[PageCandidate],
    skipped: list[PageCandidate],
    config: CompilerConfig,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    selected_ids = {page.id for page in selected}
    skipped_ids = {page.id for page in skipped}
    csv_path = review_dir / "page_decisions.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "decision",
            "page_id",
            "source_pdf",
            "page_number",
            "detail_score",
            "dark_background_inverted",
            "duplicate_group",
            "group_size",
        ])
        for group in groups:
            for page in group.members:
                decision = "selected" if page.id in selected_ids else "skipped"
                if page.id not in selected_ids and page.id not in skipped_ids:
                    decision = "ignored"
                writer.writerow([
                    decision,
                    page.id,
                    page.pdf_name,
                    page.page_number,
                    f"{page.analysis.detail_score:.6f}",
                    page.analysis.is_dark_background,
                    group.group_id,
                    len(group.members),
                ])

    summary = {
        "input_dir": str(config.input_dir),
        "output_dir": str(config.output_dir),
        "dry_run": config.dry_run,
        "dpi": config.dpi,
        "max_size_mb": config.max_size_mb,
        "annotation_threshold": config.annotation_threshold,
        "duplicate_threshold": config.duplicate_threshold,
        "keep_unannotated_unique": config.keep_unannotated_unique,
        "total_pages": len(candidates),
        "duplicate_groups": len(groups),
        "selected_pages": len(selected),
        "skipped_pages": len(skipped),
        "reports": {
            "page_decisions_csv": str(csv_path),
        },
    }
    summary_path = review_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def write_review_thumbs(
    review_dir: Path,
    selected: list[PageCandidate],
    skipped: list[PageCandidate],
) -> None:
    for page in selected:
        save_thumbnail(
            page.display_image,
            review_dir / "selected" / f"{page.id}_{page.pdf_path.stem}_p{page.page_number}.jpg",
        )
    for page in skipped:
        save_thumbnail(
            page.display_image,
            review_dir / "skipped" / f"{page.id}_{page.pdf_path.stem}_p{page.page_number}.jpg",
        )
