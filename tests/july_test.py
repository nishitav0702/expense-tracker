# python create_test_pdfs.py
# Run once, test, then delete

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ── HDFC test PDF ─────────────────────────────────────────────────────────────
hdfc = FPDF()
hdfc.add_page()
hdfc.set_font("Helvetica", "B", 12)
hdfc.cell(0, 10, "HDFC Bank Account Statement",
          new_x=XPos.LMARGIN, new_y=YPos.NEXT)
hdfc.ln(4)
hdfc.set_font("Helvetica", "", 9)

headers = ["Date", "Narration", "Chq/Ref No",
           "Value Date", "Withdrawal Amt", "Deposit Amt", "Closing Balance"]
widths  = [22, 65, 25, 22, 25, 25, 25]

for h, w in zip(headers, widths):
    hdfc.cell(w, 8, h, border=1)
hdfc.ln()

transactions = [
    ["01/07/26", "ZOMATO ORDER UPI REF001", "100000001", "01/07/26", "340.00",  "", "12,500.00"],
    ["03/07/26", "UBER RIDE UPI REF002",    "100000002", "03/07/26", "180.00",  "", "12,320.00"],
    ["04/07/26", "AMAZON PURCHASE UPI003",  "100000003", "04/07/26", "899.00",  "", "11,421.00"],
    ["05/07/26", "PETROL HP PUMP UPI004",   "100000004", "05/07/26", "500.00",  "", "10,921.00"],
    ["06/07/26", "NETFLIX SUBSCRIPTION005", "100000005", "06/07/26", "199.00",  "", "10,722.00"],
]

for row in transactions:
    for val, w in zip(row, widths):
        hdfc.cell(w, 8, val, border=1)
    hdfc.ln()

hdfc.output("test_hdfc_statement.pdf")
print("Created test_hdfc_statement.pdf")


# ── SBI test PDF ──────────────────────────────────────────────────────────────
sbi = FPDF()
sbi.add_page()
sbi.set_font("Helvetica", "B", 12)
sbi.cell(0, 10, "State Bank of India - Account Statement",
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
sbi.ln(4)
sbi.set_font("Helvetica", "", 9)

headers = ["Txn Date", "Value Date", "Description",
           "Ref No/Cheque No", "Debit", "Credit", "Balance"]
widths  = [22, 22, 60, 28, 20, 20, 25]

for h, w in zip(headers, widths):
    sbi.cell(w, 8, h, border=1)
sbi.ln()

transactions = [
    ["01/07/2026", "01/07/2026", "SWIGGY ORDER UPI",         "SBI100001", "420.00",  "", "9,580.00"],
    ["02/07/2026", "02/07/2026", "BESCOM ELECTRICITY BILL",  "SBI100002", "1200.00", "", "8,380.00"],
    ["03/07/2026", "03/07/2026", "BIGBASKET GROCERY UPI",    "SBI100003", "650.00",  "", "7,730.00"],
    ["04/07/2026", "04/07/2026", "OLA CAB UPI PAYMENT",      "SBI100004", "220.00",  "", "7,510.00"],
    ["05/07/2026", "05/07/2026", "APOLLO PHARMACY UPI",      "SBI100005", "380.00",  "", "7,130.00"],
]

for row in transactions:
    for val, w in zip(row, widths):
        sbi.cell(w, 8, val, border=1)
    sbi.ln()

sbi.output("test_sbi_statement.pdf")
print("Created test_sbi_statement.pdf")


# ── ICICI test PDF ────────────────────────────────────────────────────────────
icici = FPDF()
icici.add_page()
icici.set_font("Helvetica", "B", 12)
icici.cell(0, 10, "ICICI Bank - Statement of Account",
           new_x=XPos.LMARGIN, new_y=YPos.NEXT)
icici.ln(4)
icici.set_font("Helvetica", "", 9)

headers = ["Date", "Transaction Remarks", "Amount (INR)", "Dr/Cr", "Balance"]
widths  = [25, 80, 30, 20, 30]

for h, w in zip(headers, widths):
    icici.cell(w, 8, h, border=1)
icici.ln()

transactions = [
    ["01/07/2026", "MYNTRA FASHION PURCHASE UPI",   "1299.00", "DR", "18,701.00"],
    ["02/07/2026", "SPOTIFY PREMIUM SUBSCRIPTION",  "119.00",  "DR", "18,582.00"],
    ["03/07/2026", "DOMINOS PIZZA ORDER UPI",        "450.00",  "DR", "18,132.00"],
    ["04/07/2026", "RAPIDO BIKE CAB UPI",            "85.00",   "DR", "18,047.00"],
    ["05/07/2026", "CULT FIT GYM MEMBERSHIP",        "500.00",  "DR", "17,547.00"],
]

for row in transactions:
    for val, w in zip(row, widths):
        icici.cell(w, 8, val, border=1)
    icici.ln()

icici.output("test_icici_statement.pdf")
print("Created test_icici_statement.pdf")