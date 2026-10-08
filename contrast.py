from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageOps
import os
import shutil

# ==== USER SETTINGS ====
input_dir = "/home/swaraj/sj_code/miscellaneous/pdf_manipulatorz/OUTPUT"
output_dir = os.path.join(input_dir, "ENHANCED")
temp_folder = os.path.join(input_dir, "temp_pages")
dpi_value = 200
# =======================

os.makedirs(output_dir, exist_ok=True)
os.makedirs(temp_folder, exist_ok=True)

pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]

if not pdf_files:
    print("⚠️ No PDF files found in the directory.")
    exit()

for pdf_file in pdf_files:
    input_pdf = os.path.join(input_dir, pdf_file)
    output_pdf = os.path.join(output_dir, pdf_file)

    print(f"\n🧾 Processing: {pdf_file}")

    # Convert each page to image
    pages = convert_from_path(input_pdf, dpi=dpi_value, output_folder=temp_folder)

    enhanced_images = []

    for i, page in enumerate(pages, start=1):
        print(f"   🛠️ Enhancing page {i}")

        # Convert to grayscale
        gray = page.convert("L")

        # Boost contrast
        contrast = ImageEnhance.Contrast(gray).enhance(2.0)   # try 1.5–3.0 for tuning

        # Optional: Slight brightness increase (to reveal faded marks)
        bright = ImageEnhance.Brightness(contrast).enhance(1.2)

        # Binarize for crisp black-white output
        bw = bright.point(lambda x: 0 if x < 128 else 255, "1")

        enhanced_images.append(bw.convert("RGB"))

    # Save all enhanced pages to a single PDF
    enhanced_images[0].save(output_pdf, save_all=True, append_images=enhanced_images[1:])
    print(f"✅ Saved enhanced PDF → {output_pdf}")

    # Clean up temp folder for next file
    shutil.rmtree(temp_folder)
    os.makedirs(temp_folder, exist_ok=True)

print("\n🎉 All PDFs processed and enhanced successfully!")
