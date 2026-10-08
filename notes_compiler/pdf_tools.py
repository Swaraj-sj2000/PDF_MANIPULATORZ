from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Iterable

import fitz
from PIL import Image


EXCLUDED_DIR_NAMES = {
    "__temp__",
    "temp_pages",
    "TEMP_OUTPUT",
    "op",
    "OUTPUT",
    "COMPRESSED",
    "ENHANCED",
    "compiled",
    "review",
}


def pdfs_in_lecture_order(input_dir: Path) -> list[Path]:
    pdfs: list[Path] = []
    for path in input_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() != ".pdf":
            continue
        if any(part in EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        pdfs.append(path)
    return sorted(pdfs, key=lambda path: (path.stat().st_mtime, natural_key(path.name)))


def natural_key(value: str) -> list[object]:
    parts: list[object] = []
    current = ""
    is_digit = False
    for char in value:
        if char.isdigit() == is_digit:
            current += char
            continue
        if current:
            parts.append(int(current) if is_digit else current.lower())
        current = char
        is_digit = char.isdigit()
    if current:
        parts.append(int(current) if is_digit else current.lower())
    return parts


def render_pdf_pages(pdf_path: Path, dpi: int) -> Iterable[tuple[int, Image.Image]]:
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(pdf_path) as document:
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            yield index, image


def write_four_up_pdf(images: list[Image.Image], output_path: Path, dpi: int = 160) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not images:
        raise ValueError("Cannot write a PDF with no pages.")

    page_width, page_height = images[0].size
    pages: list[Image.Image] = []
    for offset in range(0, len(images), 4):
        canvas = Image.new("RGB", (page_width, page_height), "white")
        for slot, image in enumerate(images[offset:offset + 4]):
            quadrant = fit_image_inside(image, page_width // 2, page_height // 2)
            x = (slot % 2) * (page_width // 2) + ((page_width // 2) - quadrant.width) // 2
            y = (slot // 2) * (page_height // 2) + ((page_height // 2) - quadrant.height) // 2
            canvas.paste(quadrant, (x, y))
        pages.append(canvas)

    first, rest = pages[0], pages[1:]
    first.save(output_path, save_all=True, append_images=rest, resolution=dpi, quality=82)


def fit_image_inside(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    fitted = image.copy()
    fitted.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    return fitted


def split_pdf_by_size(input_pdf: Path, output_prefix: Path, max_size_bytes: int) -> list[Path]:
    with fitz.open(input_pdf) as source:
        if input_pdf.stat().st_size <= max_size_bytes:
            final_path = output_prefix.with_name(f"{output_prefix.name}_part_01.pdf")
            if final_path != input_pdf:
                input_pdf.replace(final_path)
            return [final_path]

        parts: list[Path] = []
        current = fitz.open()
        part_number = 1

        for page_index in range(source.page_count):
            probe = fitz.open()
            probe.insert_pdf(current)
            probe.insert_pdf(source, from_page=page_index, to_page=page_index)
            probe_bytes = probe.tobytes(garbage=4, deflate=True)

            if len(probe_bytes) > max_size_bytes and current.page_count:
                part_path = output_prefix.with_name(f"{output_prefix.name}_part_{part_number:02d}.pdf")
                current.save(part_path, garbage=4, deflate=True)
                parts.append(part_path)
                current.close()
                current = fitz.open()
                part_number += 1

            current.insert_pdf(source, from_page=page_index, to_page=page_index)

        if current.page_count:
            part_path = output_prefix.with_name(f"{output_prefix.name}_part_{part_number:02d}.pdf")
            current.save(part_path, garbage=4, deflate=True)
            parts.append(part_path)
        current.close()

    try:
        os.remove(input_pdf)
    except FileNotFoundError:
        pass
    return parts


def max_size_bytes(max_size_mb: float) -> int:
    return math.floor(max_size_mb * 1024 * 1024)
