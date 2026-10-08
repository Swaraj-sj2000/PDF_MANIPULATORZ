import fitz
import os

PDF_DIR = "/home/swaraj/sj_code/miscellaneous/pdf_manipulatorz/INPUT"
OUTPUT_PDF = "combined.pdf"

pdf_paths = sorted(
    (
        os.path.join(PDF_DIR, f)
        for f in os.listdir(PDF_DIR)
        if f.lower().endswith(".pdf")
    ),
    key=os.path.getmtime
)

merged = fitz.open()

for path in pdf_paths:
    mtime = os.path.getmtime(path)
    print(f"Merging: {os.path.basename(path)} | mtime={mtime}")

    with fitz.open(path) as doc:
        merged.insert_pdf(doc)

merged.save(OUTPUT_PDF)
merged.close()

print("\n✅ Combined PDF created in strict modification-time order")
