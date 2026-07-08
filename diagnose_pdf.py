# python diagnose_pdf.py
# Shows exactly what pdfplumber sees in your statement
# Delete after use

import pdfplumber
import sys

PDF_PATH = "OpTransactionHistory07-07-2026.pdf"  # ← change to your actual filename

with pdfplumber.open(PDF_PATH) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    print("=" * 60)

    for page_num, page in enumerate(pdf.pages):
        print(f"\n── PAGE {page_num + 1} ──────────────────────────────")

        # Show raw text
        text = page.extract_text()
        if text:
            print("RAW TEXT (first 500 chars):")
            print(text[:500])
        else:
            print("No raw text found on this page")

        print()

        # Show tables
        tables = page.extract_tables()
        print(f"Tables found: {len(tables)}")
        for t_idx, table in enumerate(tables):
            print(f"\n  Table {t_idx + 1} — {len(table)} rows:")
            for r_idx, row in enumerate(table[:8]):  # first 8 rows only
                print(f"    Row {r_idx}: {row}")