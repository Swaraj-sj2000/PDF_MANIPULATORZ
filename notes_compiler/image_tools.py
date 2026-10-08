from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageOps, ImageStat


@dataclass(frozen=True)
class PageAnalysis:
    is_dark_background: bool
    detail_score: float
    dhash: int
    ahash: int
    compare_image: Image.Image


def is_dark_background(image: Image.Image) -> bool:
    gray = image.convert("L").resize((64, 64))
    stat = ImageStat.Stat(gray)
    mean = stat.mean[0]
    dark_pixels = sum(1 for value in gray.getdata() if value < 90)
    return mean < 115 or dark_pixels / (64 * 64) > 0.55


def normalize_display(image: Image.Image) -> tuple[Image.Image, bool]:
    rgb = image.convert("RGB")
    dark = is_dark_background(rgb)
    if dark:
        rgb = ImageOps.invert(rgb)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.2)
    rgb = ImageEnhance.Sharpness(rgb).enhance(1.1)
    return rgb, dark


def comparison_image(image: Image.Image, size: int = 96) -> Image.Image:
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    gray.thumbnail((size, size), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (size, size), 255)
    x = (size - gray.width) // 2
    y = (size - gray.height) // 2
    canvas.paste(gray, (x, y))
    return canvas


def dhash(image: Image.Image, hash_size: int = 16) -> int:
    gray = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    value = 0
    for row in range(hash_size):
        for col in range(hash_size):
            left = pixels[row * (hash_size + 1) + col]
            right = pixels[row * (hash_size + 1) + col + 1]
            value = (value << 1) | int(left > right)
    return value


def ahash(image: Image.Image, hash_size: int = 16) -> int:
    gray = image.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    avg = sum(pixels) / len(pixels)
    value = 0
    for pixel in pixels:
        value = (value << 1) | int(pixel < avg)
    return value


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def mse_similarity(left: Image.Image, right: Image.Image) -> float:
    diff = ImageChops.difference(left, right)
    stat = ImageStat.Stat(diff)
    mse = sum(channel ** 2 for channel in stat.rms) / len(stat.rms)
    return max(0.0, 1.0 - (mse / (255.0 * 255.0)))


def edge_density(image: Image.Image) -> float:
    gray = image.convert("L").resize((160, 160), Image.Resampling.LANCZOS)
    pixels = gray.load()
    edges = 0
    total = 0
    for y in range(1, gray.height - 1):
        for x in range(1, gray.width - 1):
            gx = abs(pixels[x + 1, y] - pixels[x - 1, y])
            gy = abs(pixels[x, y + 1] - pixels[x, y - 1])
            if gx + gy > 50:
                edges += 1
            total += 1
    return edges / total if total else 0.0


def ink_density(image: Image.Image) -> float:
    gray = image.convert("L").resize((160, 160), Image.Resampling.LANCZOS)
    darkish = sum(1 for value in gray.getdata() if value < 210)
    return darkish / (160 * 160)


def analyze_page(image: Image.Image) -> tuple[Image.Image, PageAnalysis]:
    display, dark = normalize_display(image)
    compare = comparison_image(display)
    detail = (ink_density(display) * 0.65) + (edge_density(display) * 0.35)
    return display, PageAnalysis(
        is_dark_background=dark,
        detail_score=detail,
        dhash=dhash(compare),
        ahash=ahash(compare),
        compare_image=compare,
    )


def similarity(left: PageAnalysis, right: PageAnalysis) -> float:
    hash_bits = 16 * 16
    d_score = 1.0 - (hamming(left.dhash, right.dhash) / hash_bits)
    a_score = 1.0 - (hamming(left.ahash, right.ahash) / hash_bits)
    pixel_score = mse_similarity(left.compare_image, right.compare_image)
    return (d_score * 0.35) + (a_score * 0.25) + (pixel_score * 0.40)


def save_thumbnail(image: Image.Image, path: Path, width: int = 360) -> None:
    thumb = image.copy()
    ratio = width / thumb.width
    thumb = thumb.resize((width, max(1, int(thumb.height * ratio))), Image.Resampling.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    thumb.save(path, quality=85)
