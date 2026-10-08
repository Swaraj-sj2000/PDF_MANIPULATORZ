import os
import subprocess

# ==== USER SETTINGS ====
input_dir = "/home/swaraj/sj_code/miscellaneous/pdf_manipulatorz/OUTPUT"
output_dir = os.path.join(input_dir, "COMPRESSED")
min_reduction = 0.50  # At least 50% compression required
# =======================

os.makedirs(output_dir, exist_ok=True)

def filesize(path):
    return os.path.getsize(path) if os.path.exists(path) else 0

def ghostscript_compress(input_path, output_path, quality):
    """
    Compress a PDF using Ghostscript.
    """
    command = [
        "gs",
        "-sDEVICE=pdfwrite",
        f"-dPDFSETTINGS=/{quality}",
        "-dCompatibilityLevel=1.4",
        "-dDownsampleColorImages=true",
        "-dColorImageResolution=72",
        "-dJPEGQ=40",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path,
    ]

    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        return False


def compress_until_good(input_pdf, output_pdf):
    temp_output = output_pdf + ".tmp.pdf"

    original_size = filesize(input_pdf)
    print(f"   → Original size: {original_size/1024/1024:.2f} MB")

    # Try progressively stronger modes
    quality_modes = ["ebook", "screen", "printer"]

    for q in quality_modes:
        print(f"   ⚙ Trying Ghostscript mode: {q}")
        if not ghostscript_compress(input_pdf, temp_output, q):
            continue

        new_size = filesize(temp_output)
        reduction = 1 - new_size / original_size

        print(f"      Size now: {new_size/1024/1024:.2f} MB ({reduction*100:.1f}% smaller)")

        if reduction >= min_reduction:
            os.rename(temp_output, output_pdf)
            print("   ✔ Achieved required compression.")
            return

    # Final fallback: accept best result if nothing reached threshold
    print("   ⚠ Could not reach desired compression, saving best attempt.")
    os.rename(temp_output, output_pdf)


def main():
    pdf_files = [
        f for f in os.listdir(input_dir)
        if f.lower().endswith(".pdf")
    ]

    if not pdf_files:
        print("⚠️ No PDFs found in the input directory.")
        return

    # Sort PDFs by last modified time
    pdf_files = sorted(
        pdf_files,
        key=lambda f: os.path.getmtime(os.path.join(input_dir, f))
    )

    print("📂 PDFs found (oldest → newest):")
    for f in pdf_files:
        print("   -", f)

    print("\n🚀 Starting compression...\n")

    for pdf in pdf_files:
        input_path = os.path.join(input_dir, pdf)
        output_path = os.path.join(output_dir, pdf)

        print(f"📄 Compressing: {pdf}")
        compress_until_good(input_path, output_path)
        print()

    print("🎉 All done! Compressed PDFs saved in COMPRESSED/")


if __name__ == "__main__":
    main()
