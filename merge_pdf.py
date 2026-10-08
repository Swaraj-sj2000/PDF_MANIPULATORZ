import os
from PyPDF2 import PdfReader, PdfWriter

# ==== USER SETTINGS ====
input_dir = "/home/swaraj/sj_code/miscellaneous/pdf_manipulatorz/INPUT/OUTPUT"
output_pdf_path = os.path.join(input_dir, "merged_output.pdf")
# =======================


def get_pdfs_sorted_by_time(directory):
    pdfs = [
        f for f in os.listdir(directory)
        if f.lower().endswith(".pdf")
    ]

    # Sort by last modified timestamp
    pdfs_sorted = sorted(
        pdfs,
        key=lambda f: os.path.getmtime(os.path.join(directory, f))
    )
    return pdfs_sorted


def merge_pdfs(pdf_list, directory, output_path):
    writer = PdfWriter()

    for pdf_file in pdf_list:
        pdf_path = os.path.join(directory, pdf_file)
        print(f"Adding → {pdf_file}")
        reader = PdfReader(pdf_path)

        for page in reader.pages:
            writer.add_page(page)

    with open(output_path, "wb") as out:
        writer.write(out)

    print(f"\n✅ Merged PDF saved at: {output_path}")


if __name__ == "__main__":
    pdf_files = get_pdfs_sorted_by_time(input_dir)

    if not pdf_files:
        print("⚠️ No PDF files found in the input directory.")
    else:
        print("📄 PDFs detected in time order:")
        for f in pdf_files:
            print("   -", f)

        merge_pdfs(pdf_files, input_dir, output_pdf_path)
