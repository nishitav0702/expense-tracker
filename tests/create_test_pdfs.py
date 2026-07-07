# python create_test_pdfs.py
# Run once to generate test PDFs, then delete this file

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ── HDFC test PDF ─────────────────────────────────────────────────────────────
hdfc = FPDF()
hdfc.add_page()
hdfc.set_font("Helvetica", "B", 12)
hdfc.cell(0, 10, "HDFC Bank Account Statement", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
hdfc.ln(4)
hdfc.set_font("Helvetica", "", 9)

# Header row
headers = ["Date", "Narration", "Chq/Ref No", "Value Date", "Withdrawal Amt", "Deposit Amt", "Closing Balance"]
widths  = [22, 65, 25, 22, 25, 25, 25]
for h, w in zip(headers, widths):
    hdfc.cell(w, 8, h, border=1)
hdfc.ln()

# Transaction 1
row1 = ["15/06/25", "ZOMATO ORDER UPI", "123456789", "15/06/25", "340.00", "", "12,500.00"]
for val, w in zip(row1, widths):
    hdfc.cell(w, 8, val, border=1)
hdfc.ln()

# Transaction 2
row2 = ["18/06/25", "UBER RIDE UPI REF987", "987654321", "18/06/25", "180.00", "", "12,320.00"]
for val, w in zip(row2, widths):
    hdfc.cell(w, 8, val, border=1)
hdfc.ln()

hdfc.output("test_hdfc_statement.pdf")
print("Created test_hdfc_statement.pdf")


# ── SBI test PDF ──────────────────────────────────────────────────────────────
sbi = FPDF()
sbi.add_page()
sbi.set_font("Helvetica", "B", 12)
sbi.cell(0, 10, "State Bank of India - Account Statement", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
sbi.ln(4)
sbi.set_font("Helvetica", "", 9)

headers = ["Txn Date", "Value Date", "Description", "Ref No/Cheque No", "Debit", "Credit", "Balance"]
widths  = [22, 22, 60, 28, 20, 20, 25]
for h, w in zip(headers, widths):
    sbi.cell(w, 8, h, border=1)
sbi.ln()

row1 = ["10/06/2025", "10/06/2025", "SWIGGY INSTAMART UPI", "SBI123456", "520.00", "", "8,200.00"]
for val, w in zip(row1, widths):
    sbi.cell(w, 8, val, border=1)
sbi.ln()

row2 = ["14/06/2025", "14/06/2025", "BESCOM ELECTRICITY BILL", "SBI789012", "1200.00", "", "7,000.00"]
for val, w in zip(row2, widths):
    sbi.cell(w, 8, val, border=1)
sbi.ln()

sbi.output("test_sbi_statement.pdf")
print("Created test_sbi_statement.pdf")


# ── ICICI test PDF ────────────────────────────────────────────────────────────
icici = FPDF()
icici.add_page()
icici.set_font("Helvetica", "B", 12)
icici.cell(0, 10, "ICICI Bank - Statement of Account", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
icici.ln(4)
icici.set_font("Helvetica", "", 9)

headers = ["Date", "Transaction Remarks", "Amount (INR)", "Dr/Cr", "Balance"]
widths  = [25, 80, 30, 20, 30]
for h, w in zip(headers, widths):
    icici.cell(w, 8, h, border=1)
icici.ln()

row1 = ["05/06/2025", "AMAZON PURCHASE UPI", "899.00", "DR", "15,101.00"]
for val, w in zip(row1, widths):
    icici.cell(w, 8, val, border=1)
icici.ln()

row2 = ["12/06/2025", "NETFLIX SUBSCRIPTION", "199.00", "DR", "14,902.00"]
for val, w in zip(row2, widths):
    icici.cell(w, 8, val, border=1)
icici.ln()

icici.output("test_icici_statement.pdf")
print("Created test_icici_statement.pdf")