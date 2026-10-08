from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .image_tools import PageAnalysis, analyze_page, save_thumbnail, similarity
from .pdf_tools import (
    max_size_bytes,
    pdfs_in_lecture_order,
    render_pdf_pages,
    split_pdf_by_size,
    write_four_up_pdf_from_paths,
)


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
    window_pages: int = 120
    limit_pages: int | None = None


@dataclass
class PageRecord:
    id: str
    pdf_name: str
    page_number: int
    order_index: int
    detail_score: float
    is_dark_background: bool
    group_id: int
    decision: str = "pending"
    image_path: Path | None = None


@dataclass
class ActiveGroup:
    group_id: int
    first_order_index: int
    last_order_index: int
    best_record: PageRecord
    best_analysis: PageAnalysis
    size: int = 1


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
    page_store = run_dir / "page_store"
    review_dir.mkdir(parents=True, exist_ok=True)
    page_store.mkdir(parents=True, exist_ok=True)

    records, groups = stream_pages(input_dir, page_store, config)
    selected = [
        group.best_record
        for group in sorted(groups, key=lambda item: item.first_order_index)
        if group.best_record.decision == "selected"
    ]
    skipped = [record for record in records if record.decision == "skipped"]

    report_path = write_reports(
        run_dir=run_dir,
        review_dir=review_dir,
        records=records,
        groups=groups,
        config=config,
    )

    if config.write_review_thumbnails:
        write_review_thumbs(review_dir, records)

    output_parts: list[Path] = []
    if selected and not config.dry_run:
        image_paths = [record.image_path for record in selected if record.image_path is not None]
        temp_pdf = run_dir / f"{output_name}_compiled_full.pdf"
        write_four_up_pdf_from_paths(image_paths, temp_pdf, dpi=config.dpi)
        output_parts = split_pdf_by_size(
            temp_pdf,
            run_dir / f"{output_name}_compiled",
            max_size_bytes(config.max_size_mb),
        )

    return CompileResult(
        total_pages=len(records),
        selected_pages=len(selected),
        skipped_pages=len(skipped),
        report_path=report_path,
        output_parts=output_parts,
    )


def stream_pages(
    input_dir: Path,
    page_store: Path,
    config: CompilerConfig,
) -> tuple[list[PageRecord], list[ActiveGroup]]:
    records: list[PageRecord] = []
    groups: list[ActiveGroup] = []

    for pdf_path in pdfs_in_lecture_order(input_dir):
        for page_number, raw_image in render_pdf_pages(pdf_path, dpi=config.dpi):
            if config.limit_pages is not None and len(records) >= config.limit_pages:
                return records, finalize_groups(groups, config)

            display, analysis = analyze_page(raw_image)
            order_index = len(records)
            record = PageRecord(
                id=f"{order_index + 1:05d}",
                pdf_name=pdf_path.name,
                page_number=page_number,
                order_index=order_index,
                detail_score=analysis.detail_score,
                is_dark_background=analysis.is_dark_background,
                group_id=-1,
            )

            group = best_recent_group_match(
                analysis=analysis,
                groups=groups,
                order_index=order_index,
                window_pages=max(1, config.window_pages),
                duplicate_threshold=config.duplicate_threshold,
            )
            if group is None:
                group = ActiveGroup(
                    group_id=len(groups) + 1,
                    first_order_index=order_index,
                    last_order_index=order_index,
                    best_record=record,
                    best_analysis=analysis,
                )
                groups.append(group)
                record.group_id = group.group_id
                save_best_page(display, record, page_store)
            else:
                group.size += 1
                group.last_order_index = order_index
                record.group_id = group.group_id
                record.decision = "skipped"
                if is_better_candidate(record, group.best_record):
                    group.best_record.decision = "skipped"
                    save_best_page(display, record, page_store)
                    group.best_record = record
                    group.best_analysis = analysis

            records.append(record)

    return records, finalize_groups(groups, config)


def finalize_groups(
    groups: list[ActiveGroup],
    config: CompilerConfig,
) -> list[ActiveGroup]:
    for group in groups:
        best = group.best_record
        annotated_enough = best.detail_score >= config.annotation_threshold
        if annotated_enough or config.keep_unannotated_unique:
            best.decision = "selected"
        else:
            best.decision = "skipped"
    return groups


def best_recent_group_match(
    analysis: PageAnalysis,
    groups: list[ActiveGroup],
    order_index: int,
    window_pages: int,
    duplicate_threshold: float,
) -> ActiveGroup | None:
    best_score = 0.0
    best_group: ActiveGroup | None = None
    min_order = max(0, order_index - window_pages)
    for group in reversed(groups):
        if group.last_order_index < min_order:
            break
        score = similarity(analysis, group.best_analysis)
        if score > best_score:
            best_score = score
            best_group = group
    if best_score >= duplicate_threshold:
        return best_group
    return None


def is_better_candidate(candidate: PageRecord, current: PageRecord) -> bool:
    detail_delta = candidate.detail_score - current.detail_score
    if detail_delta > 0.004:
        return True
    if abs(detail_delta) <= 0.004:
        return candidate.order_index > current.order_index
    return False


def save_best_page(image: Image.Image, record: PageRecord, page_store: Path) -> None:
    page_store.mkdir(parents=True, exist_ok=True)
    path = page_store / f"{record.id}_{Path(record.pdf_name).stem}_p{record.page_number}.jpg"
    image.save(path, quality=86, optimize=True)
    record.image_path = path


def write_reports(
    run_dir: Path,
    review_dir: Path,
    records: list[PageRecord],
    groups: list[ActiveGroup],
    config: CompilerConfig,
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = review_dir / "page_decisions.csv"
    group_sizes = {group.group_id: group.size for group in groups}
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
        for record in records:
            writer.writerow([
                record.decision,
                record.id,
                record.pdf_name,
                record.page_number,
                f"{record.detail_score:.6f}",
                record.is_dark_background,
                record.group_id,
                group_sizes.get(record.group_id, 1),
            ])

    summary = {
        "input_dir": str(config.input_dir),
        "output_dir": str(config.output_dir),
        "dry_run": config.dry_run,
        "dpi": config.dpi,
        "max_size_mb": config.max_size_mb,
        "annotation_threshold": config.annotation_threshold,
        "duplicate_threshold": config.duplicate_threshold,
        "window_pages": config.window_pages,
        "limit_pages": config.limit_pages,
        "keep_unannotated_unique": config.keep_unannotated_unique,
        "total_pages": len(records),
        "duplicate_groups": len(groups),
        "selected_pages": sum(1 for record in records if record.decision == "selected"),
        "skipped_pages": sum(1 for record in records if record.decision == "skipped"),
        "reports": {
            "page_decisions_csv": str(csv_path),
        },
    }
    summary_path = review_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary_path


def write_review_thumbs(review_dir: Path, records: list[PageRecord]) -> None:
    for record in records:
        if record.image_path is None:
            continue
        image = Image.open(record.image_path)
        try:
            save_thumbnail(
                image,
                review_dir / record.decision / f"{record.id}_{Path(record.pdf_name).stem}_p{record.page_number}.jpg",
            )
        finally:
            image.close()
