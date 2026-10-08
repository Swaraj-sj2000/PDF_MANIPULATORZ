import os
import shutil
import re
from PyPDF2 import PdfReader, PdfWriter
from pdf2image import convert_from_path
from PIL import ImageOps

def parse_pages(spec, total_pages):
    if not spec:
        return []
    spec = spec.replace(" ", "")
    tokens = re.findall(r"\(\d+,\d+\)|\d+", spec)
    pages = set()
    for tok in tokens:
        if tok.startswith("("):
            a, b = map(int, tok[1:-1].split(","))
            pages.update(range(max(1, min(a, b)), min(total_pages, max(a, b)) + 1))
        else:
            p = int(tok)
            if 1 <= p <= total_pages:
                pages.add(p)
    return sorted(pages)

input_dir = "/home/swaraj/sj_code/miscellaneous/pdf_manipulatorz/datawarehousing"
output_dir = os.path.join(input_dir, "op")
temp_dir = os.path.join(input_dir, "__temp__")

os.makedirs(output_dir, exist_ok=True)
os.makedirs(temp_dir, exist_ok=True)

pdfs = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
pdfs.sort(key=lambda f: os.path.getmtime(os.path.join(input_dir, f)))

for pdf in pdfs:
    in_path = os.path.join(input_dir, pdf)
    out_path = os.path.join(output_dir, pdf)

    print(f"\nPDF: {pdf}")
    if input("Process this PDF? [y/n]: ").strip().lower() != "y":
        continue

    reader = PdfReader(in_path)
    total = len(reader.pages)

    mode = input("Keep or exclude pages? [k/e]: ").strip().lower()
    spec = input("Enter pages like 1,2,(23,44) or leave empty for all: ").strip()

    selected = parse_pages(spec, total)

    if mode == "k":
        pages_to_keep = selected if selected else list(range(1, total + 1))
    else:
        pages_to_keep = [p for p in range(1, total + 1) if p not in selected]

    if not pages_to_keep:
        print("No pages left after filtering. Skipping save.")
        continue

    invert = input("Invert colors? [y/n]: ").strip().lower() == "y"

    if not invert:
        writer = PdfWriter()
        for p in pages_to_keep:
            writer.add_page(reader.pages[p - 1])
        with open(out_path, "wb") as f:
            writer.write(f)
    else:
        images = convert_from_path(in_path, dpi=200, output_folder=temp_dir)
        processed = []
        for i in pages_to_keep:
            img = ImageOps.invert(images[i - 1].convert("RGB"))
            processed.append(img)
        processed[0].save(out_path, save_all=True, append_images=processed[1:])

    print(f"Saved -> {out_path}")

shutil.rmtree(temp_dir, ignore_errors=True)
print("Done")