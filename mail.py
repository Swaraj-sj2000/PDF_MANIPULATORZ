import os
import smtplib
import time
from email.message import EmailMessage

# ================== USER SETTINGS ==================
pdf_folder = "/home/swaraj/sj_code/miscellaneous/pdf_manipulatorz/OUTPUT"

smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "swarajsj8102000@gmail.com"
app_password = "viom couw vyvs vbbj"

recipient_email = "printz.bi@gmail.com"

delay_between_emails = 1
subject_prefix = "PDF Document"
# ====================================================

def get_sorted_pdfs(folder):
    pdfs = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".pdf")
    ]
    pdfs.sort(key=lambda f: os.path.getmtime(f))
    return pdfs


def send_all_pdfs():
    pdf_files = get_sorted_pdfs(pdf_folder)
    if not pdf_files:
        print("No PDFs found.")
        return

    print(f"Found {len(pdf_files)} PDFs. Starting…\n")

    # ---------- REUSE ONE SMTP SESSION ----------
    with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        smtp.starttls()
        smtp.login(sender_email, app_password)

        for i, pdf in enumerate(pdf_files, start=1):
            pdf_name = os.path.basename(pdf)
            print(f"[{i}/{len(pdf_files)}] Sending: {pdf_name}")

            try:
                msg = EmailMessage()
                msg["From"] = sender_email
                msg["To"] = recipient_email
                msg["Subject"] = f"{subject_prefix}: {pdf_name}"
                msg.set_content(f"Attached: {pdf_name}")

                with open(pdf, "rb") as f:
                    data = f.read()

                msg.add_attachment(
                    data,
                    maintype="application",
                    subtype="pdf",
                    filename=pdf_name
                )

                smtp.send_message(msg)
                print("   ✔ Sent")

            except Exception as e:
                print(f"   ❌ Failed: {e}")

            time.sleep(delay_between_emails)

    print("\nAll emails sent!")

if __name__=="__main__":
    send_all_pdfs()