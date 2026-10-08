from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import CompilerConfig, compile_notes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compile screenshot/blackboard lecture PDFs into annotated, "
            "deduplicated, inverted, 4-up printable notes."
        )
    )
    parser.add_argument("input_dir", type=Path, help="Folder containing lecture PDFs.")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("compiled"),
        help="Output folder for compiled PDFs and reports.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Base name for output PDFs. Defaults to the input folder name.",
    )
    parser.add_argument(
        "--max-size-mb",
        type=float,
        default=20.0,
        help="Maximum size for each final PDF part.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=160,
        help="Render DPI used for page images.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only analyze and write review reports; do not write final PDFs.",
    )
    parser.add_argument(
        "--keep-unannotated-unique",
        action="store_true",
        help=(
            "Keep unique pages even when they look lightly annotated. "
            "By default, lightly marked unique pages are skipped."
        ),
    )
    parser.add_argument(
        "--annotation-threshold",
        type=float,
        default=0.022,
        help="Minimum detail score for a page to be treated as annotated/useful.",
    )
    parser.add_argument(
        "--duplicate-threshold",
        type=float,
        default=0.82,
        help="Similarity threshold used to group repeated slides.",
    )
    parser.add_argument(
        "--review-thumbnails",
        action="store_true",
        help="Write small chosen/skipped thumbnails for manual audit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = CompilerConfig(
        input_dir=args.input_dir,
        output_dir=args.out,
        output_name=args.name,
        max_size_mb=args.max_size_mb,
        dpi=args.dpi,
        dry_run=args.dry_run,
        keep_unannotated_unique=args.keep_unannotated_unique,
        annotation_threshold=args.annotation_threshold,
        duplicate_threshold=args.duplicate_threshold,
        write_review_thumbnails=args.review_thumbnails,
    )
    try:
        result = compile_notes(config)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Analyzed pages: {result.total_pages}")
    print(f"Selected pages: {result.selected_pages}")
    print(f"Skipped pages: {result.skipped_pages}")
    print(f"Review report: {result.report_path}")
    if result.output_parts:
        print("Output PDFs:")
        for part in result.output_parts:
            print(f"  - {part}")
    return 0
