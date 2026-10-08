from pypdf import PdfReader, PdfWriter
import os

INPUT_PDF = "/home/swaraj/sj_code/miscellaneous/pdf_manipulatorz/comp_net1.pdf"
MAX_SIZE_MB = 20
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

reader = PdfReader(INPUT_PDF)

writer = PdfWriter()
current_size = 0
part = 1

for i, page in enumerate(reader.pages):
    temp_writer = PdfWriter()
    temp_writer.add_page(page)

    temp_file = f"temp_page.pdf"
    with open(temp_file, "wb") as f:
        temp_writer.write(f)

    page_size = os.path.getsize(temp_file)
    os.remove(temp_file)

    if current_size + page_size > MAX_SIZE_BYTES:
        output_name = f"cn2_part_{part}.pdf"
        with open(output_name, "wb") as f:
            writer.write(f)

        part += 1
        writer = PdfWriter()
        current_size = 0

    writer.add_page(page)
    current_size += page_size

if len(writer.pages) > 0:
    output_name = f"output_part_{part}.pdf"
    with open(output_name, "wb") as f:
        writer.write(f)
