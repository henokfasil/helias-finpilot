#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HELIAS AI AND ANALYTICS PLC
Annual Financial Report — Ethiopian Budget Year 2018 E.C. (08 Jul 2025 - 07 Jul 2026)
Generates a multi-sheet Excel workbook for the Ministry of Revenue filing.

All figures reconciled across: CBE bank statement <-> working papers (WHT/VAT/Rent)
<-> receipts <-> FinPilot bot export.  Currency = ETB.  Basis = Accrual.
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OUT = "Helias_FY2018_Financial_Report_ETB.xlsx"

# ------------------------------------------------------------------ styling
NAVY   = "1F3864"
BLUE   = "2E5496"
LTBLUE = "D9E1F2"
GOLD   = "FFF2CC"
GREY   = "F2F2F2"
GREEN  = "E2EFDA"
RED    = "FCE4D6"
WHITE  = "FFFFFF"

CURR = '#,##0.00'
INT  = '#,##0'

thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
TOPB   = Border(top=Side(style="thin", color="808080"))
DBL    = Border(top=Side(style="double", color="000000"))

def F(size=10, bold=False, color="000000", italic=False):
    return Font(name="Calibri", size=size, bold=bold, color=color, italic=italic)

def fill(c): return PatternFill("solid", fgColor=c)

def cell(ws, r, c, v=None, *, font=None, fillc=None, num=None, align=None,
         wrap=False, border=False, valign="center"):
    x = ws.cell(row=r, column=c, value=v)
    if font: x.font = font
    if fillc: x.fill = fill(fillc)
    if num: x.number_format = num
    x.alignment = Alignment(horizontal=align, vertical=valign, wrap_text=wrap)
    if border: x.border = BORDER
    return x

def title_block(ws, title, subtitle, ncols):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    cell(ws, 1, 1, "HELIAS AI AND ANALYTICS PLC", font=F(15, True, WHITE),
         fillc=NAVY, align="left")
    ws.row_dimensions[1].height = 24
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=ncols)
    cell(ws, 2, 1, title, font=F(12, True, WHITE), fillc=BLUE, align="left")
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=ncols)
    cell(ws, 3, 1, subtitle, font=F(9, False, "444444"), fillc=LTBLUE, align="left")
    ws.row_dimensions[2].height = 18

def section(ws, r, text, ncols, c0=1):
    ws.merge_cells(start_row=r, start_column=c0, end_row=r, end_column=ncols)
    cell(ws, r, c0, text, font=F(10, True, NAVY), fillc=LTBLUE, align="left")

PERIOD = "Ethiopian Budget Year 2018 E.C.  |  Hamle 1, 2017 E.C. – Sene 30, 2018 E.C.  |  08 July 2025 – 07 July 2026"

wb = Workbook()

# ============================================================== 0. COVER
ws = wb.active; ws.title = "Cover"
ws.sheet_view.showGridLines = False
for i,w in enumerate([3,26,40,22,10], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "ANNUAL FINANCIAL REPORT", PERIOD, 5)
r = 5
info = [
    ("Company name", "HELIAS AI AND ANALYTICS PLC"),
    ("Legal form", "Private Limited Company (PLC)"),
    ("General Manager", "Dr. Henok Fasil Telila"),
    ("TIN", "0098960114"),
    ("Commercial Registration No.", "AACATB/2/0242251/2018"),
    ("Business License No.", "AACATB/14/707/44611365/2018"),
    ("Registered address", "Addis Ababa, Lemi Kura Sub-City, Woreda 05"),
    ("Sector / activities", "AI, software, data processing & business services (ISIC 8)"),
    ("Paid-up capital", "ETB 50,000.00"),
    ("Reporting period", "08 July 2025 – 07 July 2026 (FY 2018 E.C.)"),
    ("Reporting currency", "Ethiopian Birr (ETB)"),
    ("Accounting basis", "Accrual"),
    ("VAT status", "Registered (15%)"),
    ("First operating year", "Yes – company registered Hidar 2018 E.C. (opening balances nil)"),
]
for k,v in info:
    cell(ws, r, 2, k, font=F(10, True));
    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=5)
    cell(ws, r, 3, v, font=F(10)); r += 1

r += 1
section(ws, r, "CONTENTS OF THIS WORKBOOK", 5); r += 1
contents = [
    ("1. Reconciliation", "Bank statement vs FinPilot bot vs working papers; corrections applied"),
    ("2. Transaction Ledger", "All reconciled transactions in the period, by source & treatment"),
    ("3. Revenue Summary", "Sales/service income, output VAT, WHT withheld by clients"),
    ("4. Expense Summary", "Operating expenses by category (accrual)"),
    ("5. Payroll Summary", "Employees, gross salary, income tax, pension, net pay"),
    ("6. Pension Summary", "Employee 7% + Employer 11% contributions"),
    ("7. Income Statement", "Profit & Loss for the year"),
    ("8. Balance Sheet", "Financial position as at 07 July 2026"),
    ("9. Cash Flow Statement", "CBE operating account, direct method (ties to bank)"),
    ("10. Tax Summary", "VAT, WHT and business profit-tax computation"),
    ("11. Notes & Open Items", "Assumptions and items to confirm with the accountant"),
]
for k,v in contents:
    cell(ws, r, 2, k, font=F(10, True, BLUE))
    ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=5)
    cell(ws, r, 3, v, font=F(9, italic=True, color="555555")); r += 1

r += 1
cell(ws, r, 2, "Prepared", font=F(9, True))
ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=5)
cell(ws, r, 3, "Draft prepared from company source documents for review by the "
     "external accountant (Fantanesh) before submission to the Ministry of Revenue.",
     font=F(9, italic=True, color="555555"), wrap=True)
ws.row_dimensions[r].height = 30

# ============================================================== 1. RECONCILIATION
ws = wb.create_sheet("1. Reconciliation")
ws.sheet_view.showGridLines = False
widths = [4, 12, 34, 15, 15, 15, 30]
for i,w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "RECONCILIATION — Bank ↔ FinPilot ↔ Working papers", PERIOD, 7)
r = 5
cell(ws, r, 1, "A) CBE local account 1000723346235 — every bank line traced to source",
     font=F(10, True, NAVY)); r += 1
hdr = ["#","Value date","Narration (bank)","Debit","Credit","Bank balance","Treatment / source"]
for c,h in enumerate(hdr, start=1):
    cell(ws, r, c, h, font=F(9, True, WHITE), fillc=NAVY, align="center", border=True, wrap=True)
r += 1
bank = [
    ("15 Oct 25","Mobile Credit — 'ghg done via Mob'", 0, 50000.00, 50000.00, "Financing: owner/related-party injection"),
    ("26 Jan 26","Internet Debit — 'TEST'", 10.75, 0, 49989.25, "Bank charge / test"),
    ("09 Apr 26","Mobile Money — 'DD95QMQNKX'", 0, 300000.00, 349989.25, "Financing: owner/related-party injection"),
    ("09 Apr 26","Mobile Credit — 'hdhddh'", 0, 50000.00, 399989.25, "Financing: owner/related-party injection"),
    ("10 Apr 26","Internet Debit — Flight ticket", 303006.00, 0, 96983.25, "Expense: Travel (air ticket)"),
    ("20 Jun 26","Internet Debit — 'For Income tax'", 6871.45, 0, 90111.80, "Payroll income-tax / profit-tax prepayment"),
    ("20 Jun 26","Internet Debit — 'Pension related'", 4711.20, 0, 85400.60, "Pension / payroll remittance"),
    ("26 Jun 26","Transfer — Ethiopian Economic Assoc.", 0, 939826.09, 1025226.69, "REVENUE: EEA (ref FT261773ZVX5)"),
    ("26 Jun 26","Inward Telex — National Bank of Ethiopia", 0, 1392608.10, 2417834.79, "REVENUE: NBE project (ref FT26177H6WV9)"),
    ("01 Jul 26","Internet Debit — car rent", 155206.00, 0, 2262628.79, "Expense: Vehicle rent (net of 3% WHT)"),
    ("01 Jul 26","Internet Debit — GM Salary Annual", 80006.00, 0, 2182622.79, "Payroll: General Manager salary"),
    ("01 Jul 26","Internet Debit — house rent annual", 21346.00, 0, 2161276.79, "Expense: Office/house rent (net of 3% WHT)"),
    ("01 Jul 26","Internet Debit — Accountant Salary", 15006.00, 0, 2146270.79, "Payroll: Accountant salary"),
    ("02 Jul 26","Internet Debit — Consulting service (Corridor)", 718169.00, 0, 1428101.79, "Expense: Professional/software (net of VAT+WHT)"),
    ("02 Jul 26","Internet Debit — laptop devices (SkyBlue)", 547929.00, 0, 880172.79, "CAPEX: Equipment (net of VAT+WHT)"),
]
n = 1
first = r
for vd, nar, deb, cre, bal, tr in bank:
    cell(ws, r, 1, n, align="center", border=True)
    cell(ws, r, 2, vd, border=True, font=F(9))
    cell(ws, r, 3, nar, border=True, font=F(9), wrap=True)
    cell(ws, r, 4, deb or None, num=CURR, border=True)
    cell(ws, r, 5, cre or None, num=CURR, border=True)
    cell(ws, r, 6, bal, num=CURR, border=True)
    cell(ws, r, 7, tr, border=True, font=F(9), wrap=True)
    n += 1; r += 1
cell(ws, r, 3, "TOTALS", font=F(9, True), fillc=GOLD, align="right", border=True)
cell(ws, r, 4, f"=SUM(D{first}:D{r-1})", num=CURR, font=F(9, True), fillc=GOLD, border=True)
cell(ws, r, 5, f"=SUM(E{first}:E{r-1})", num=CURR, font=F(9, True), fillc=GOLD, border=True)
cell(ws, r, 6, "Ending 880,172.79", font=F(9, True), fillc=GOLD, align="center", border=True)
cell(ws, r, 7, "Starting 0.00 → Ending 880,172.79 ✓", font=F(9, True), fillc=GOLD, border=True)
r += 2
cell(ws, r, 1, "B) Corrections applied to FinPilot bot figures (bot had data-entry errors)",
     font=F(10, True, NAVY)); r += 1
hdr2 = ["","Item","Bot (FinPilot) value","Correct value (source)","Source of truth"]
cell(ws, r, 2, "Item", font=F(9, True, WHITE), fillc=NAVY, border=True)
cell(ws, r, 3, "Bot (FinPilot) value", font=F(9, True, WHITE), fillc=NAVY, border=True, align="center")
cell(ws, r, 4, "Correct value", font=F(9, True, WHITE), fillc=NAVY, border=True, align="center")
cell(ws, r, 5, "Source of truth", font=F(9, True, WHITE), fillc=NAVY, border=True)
ws.merge_cells(start_row=r, start_column=5, end_row=r, end_column=7)
r += 1
corr = [
    ("Corridor Trading (consulting) — cash paid", 718613.00, 718169.00, "Bank + Corridor receipt FT2618383G9L"),
    ("SkyBlue Trading (equipment) — cash paid", 547923.00, 547929.00, "Bank + SkyBlue receipt FT2618363HQ1"),
    ("VAT paid to Ministry (June 2026)", 143104.48, 142814.48, "e-Tax receipt ref 2106569599999"),
    ("WHT paid to Ministry (June 2026)", 34203.02, 33913.02, "e-Tax receipt ref 2104995749999"),
    ("Pension paid to Ministry (June 2026)", 2706.00, 2700.00, "e-Tax receipt ref 2104558149999"),
    ("Revenue counterparty for ETB 1,392,608.10", 0, 0, "Payer = National Bank of Ethiopia (not internal transfer) → genuine revenue"),
]
for it, bv, cv, src in corr:
    cell(ws, r, 2, it, border=True, font=F(9), wrap=True)
    cell(ws, r, 3, bv or ("—" if bv==0 else bv), num=CURR if bv else None, border=True, align="right")
    cell(ws, r, 4, cv or "—", num=CURR if cv else None, border=True, align="right")
    ws.merge_cells(start_row=r, start_column=5, end_row=r, end_column=7)
    cell(ws, r, 5, src, border=True, font=F(9), wrap=True)
    r += 1
r += 1
cell(ws, r, 1, "C) Items in the bank but NOT captured in the bot (now included):", font=F(9, True, "833C00")); r+=1
for t in ["• Car rent 155,206 (net) • GM salary 80,006 • House rent 21,346 (net) • Accountant salary 15,006",
          "• Owner/related-party injections 50,000 + 300,000 + 50,000 = 400,000 (financing)"]:
    cell(ws, r, 1, t, font=F(9)); ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=7); r+=1
cell(ws, r, 1, "D) Items in the bot paid OUTSIDE this bank account (TeleBirr/cash, funded by director) — included on accrual basis:", font=F(9, True, "833C00")); r+=1
for t in ["• DARS document/registration fees 15,734 • Ethio Telecom 5,224 • Romina training/meals 5,430.02",
          "• Berhanena Selam printing 4,500.06 • Circular stamp 2,800 • July VAT/WHT/pension remittances • loan repayment 300,000 (20 Aug 26, after year-end)"]:
    cell(ws, r, 1, t, font=F(9)); ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=7); r+=1

# ============================================================== 2. LEDGER
ws = wb.create_sheet("2. Transaction Ledger")
ws.sheet_view.showGridLines = False
widths = [4, 11, 30, 26, 13, 11, 11, 14, 16]
for i,w in enumerate(widths, start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "TRANSACTION LEDGER (reconciled)", PERIOD, 9)
r = 5
hdr = ["#","Date","Counterparty","Description","Amount (ETB)","VAT","WHT","Channel","Classification"]
for c,h in enumerate(hdr, start=1):
    cell(ws, r, c, h, font=F(9, True, WHITE), fillc=NAVY, align="center", border=True, wrap=True)
r += 1
# (date, counterparty, description, amount, vat, wht, channel, class)
led = [
 ("2025-08-30","DARS","Document authentication fee",340.00,None,None,"TeleBirr","Expense-Legal/Reg"),
 ("2025-09-01","DARS","Document authentication fee",1210.00,None,None,"CBE","Expense-Legal/Reg"),
 ("2025-10-15","Owner/Related party","Injection 'ghg'",50000.00,None,None,"CBE","Financing-in"),
 ("2026-01-05","DARS","Document authentication fee",1302.00,None,None,"TeleBirr","Expense-Legal/Reg"),
 ("2026-02-12","Romina PLC","Marketing team training / lunch",5430.02,708.27,None,"Cash","Expense-Training/Meals"),
 ("2026-02-16","Berhanena Selam Printing","VAT/WHT receipts printing",4500.06,586.96,None,"Cash","Expense-Printing"),
 ("2026-03-26","DARS","Document authentication fee",140.00,None,None,"TeleBirr","Expense-Legal/Reg"),
 ("2026-03-26","DARS","Document authentication fee",340.00,None,None,"TeleBirr","Expense-Legal/Reg"),
 ("2026-03-26","DARS","Document authentication fee",10900.00,None,None,"TeleBirr","Expense-Legal/Reg"),
 ("2026-03-26","DARS","Receipt for services",702.00,None,None,"TeleBirr","Expense-Legal/Reg"),
 ("2026-03-28","Ethio Telecom","LTE SIM / MSISDN fee",4500.00,586.30,None,"CBE","Expense-Telecom"),
 ("2026-04-09","Notary (TIN 0098960114)","Circular stamp / CEO & Deputy titles",2800.00,365.22,None,"Cash","Expense-Legal/Reg"),
 ("2026-04-09","Owner/Related party","Injection (Mobile Money)",300000.00,None,None,"CBE","Financing-in"),
 ("2026-04-09","Owner/Related party","Injection 'hdhddh'",50000.00,None,None,"CBE","Financing-in"),
 ("2026-04-10","Fly Better Tour & Travel","Air ticket (travel)",303006.00,None,6060.12,"CBE","Expense-Travel"),
 ("2026-04-15","Ethio Telecom","Stamps",724.00,None,None,"TeleBirr","Expense-Telecom"),
 ("2026-06-14","DARS","Document authentication fee",800.00,None,None,"TeleBirr","Expense-Legal/Reg"),
 ("2026-06-20","Ministry of Revenue","Payroll income-tax remittance",6871.45,None,None,"CBE","Tax remittance"),
 ("2026-06-20","Ministry of Revenue","Pension remittance",4711.20,None,None,"CBE","Tax remittance"),
 ("2026-06-26","Ethiopian Economic Association","AI/ML services (net 839,130.43 + VAT)",939826.09,125869.57,25173.91,"CBE","REVENUE"),
 ("2026-06-26","National Bank of Ethiopia","AI/data services (net 1,243,400.09 + VAT)",1392608.10,186510.01,37302.00,"CBE","REVENUE"),
 ("2026-07-01","Fasil Telila (lessor)","Vehicle rent — 4 months (net of WHT)",155206.00,None,4800.00,"CBE","Expense-Rent"),
 ("2026-07-01","General Manager","GM salary (annual settlement)",80006.00,None,None,"CBE","Payroll"),
 ("2026-07-01","Fasil Telila (lessor)","Office/house rent (net of WHT)",21346.00,None,660.00,"CBE","Expense-Rent"),
 ("2026-07-01","Accountant (Beti)","Accountant salary",15006.00,None,None,"CBE","Payroll"),
 ("2026-07-02","Corridor Trading PLC","Consulting/software (net of VAT+WHT)",718169.00,96182.61,19236.52,"CBE","Expense-Professional"),
 ("2026-07-02","SkyBlue Trading PLC","Laptops/furniture (net of VAT+WHT)",547929.00,73382.61,14676.52,"CBE","CAPEX-Equipment"),
]
n = 1
for d,cp,desc,amt,vat,wht,ch,cl in led:
    fc = GREEN if cl=="REVENUE" else (RED if cl.startswith("Financing") else (LTBLUE if cl.startswith("CAPEX") else None))
    cell(ws, r, 1, n, align="center", border=True)
    cell(ws, r, 2, d, border=True, font=F(9))
    cell(ws, r, 3, cp, border=True, font=F(9), wrap=True)
    cell(ws, r, 4, desc, border=True, font=F(9), wrap=True)
    cell(ws, r, 5, amt, num=CURR, border=True, fillc=fc)
    cell(ws, r, 6, vat, num=CURR, border=True)
    cell(ws, r, 7, wht, num=CURR, border=True)
    cell(ws, r, 8, ch, border=True, font=F(9), align="center")
    cell(ws, r, 9, cl, border=True, font=F(9))
    n += 1; r += 1
cell(ws, r, 4, "Note: excludes 1 rejected duplicate (EEA appeared twice in bot). Loan repayment 300,000 (2026-08-20) is post year-end.",
     font=F(8, italic=True, color="808080")); ws.merge_cells(start_row=r,start_column=4,end_row=r,end_column=9)

# ============================================================== 3. REVENUE
ws = wb.create_sheet("3. Revenue Summary")
ws.sheet_view.showGridLines = False
for i,w in enumerate([4,34,18,16,16,16,16], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "REVENUE SUMMARY (net of VAT)", PERIOD, 7)
r = 5
hdr = ["#","Client / source","Gross incl. VAT","Net revenue","Output VAT (15%)","WHT withheld by client","Cash received"]
for c,h in enumerate(hdr, start=1):
    cell(ws, r, c, h, font=F(9, True, WHITE), fillc=NAVY, align="center", border=True, wrap=True)
r += 1
rev = [
    ("National Bank of Ethiopia — AI/data services project", 1429910.10, 1243400.09, 186510.01, 37302.00, 1392608.10),
    ("Ethiopian Economic Association — ML/AI services", 965000.00, 839130.43, 125869.57, 25173.91, 939826.09),
]
first = r
n=1
for name,g,net,vat,wht,cash in rev:
    cell(ws, r, 1, n, align="center", border=True)
    cell(ws, r, 2, name, border=True, font=F(10), wrap=True)
    cell(ws, r, 3, g, num=CURR, border=True)
    cell(ws, r, 4, net, num=CURR, border=True, fillc=GREEN)
    cell(ws, r, 5, vat, num=CURR, border=True)
    cell(ws, r, 6, wht, num=CURR, border=True)
    cell(ws, r, 7, cash, num=CURR, border=True)
    n+=1; r+=1
cell(ws, r, 2, "TOTAL REVENUE", font=F(11, True), fillc=GOLD, border=True)
for c in range(3,8):
    L = get_column_letter(c)
    cell(ws, r, c, f"=SUM({L}{first}:{L}{r-1})", num=CURR, font=F(11, True), fillc=GOLD, border=True)
r += 2
cell(ws, r, 2, "Total net revenue for the year (Income Statement line):", font=F(10, True))
cell(ws, r, 4, "=D"+str(r-2), num=CURR, font=F(11, True, BLUE)); r+=1
cell(ws, r, 2, "Output VAT collected (Tax Summary):", font=F(9))
cell(ws, r, 5, "=E"+str(r-3), num=CURR, font=F(10, True)); r+=1
cell(ws, r, 2, "WHT credit receivable (creditable vs profit tax):", font=F(9))
cell(ws, r, 6, "=F"+str(r-4), num=CURR, font=F(10, True))

# ============================================================== 4. EXPENSES
ws = wb.create_sheet("4. Expense Summary")
ws.sheet_view.showGridLines = False
for i,w in enumerate([4,38,18,42], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "EXPENSE SUMMARY (operating, accrual)", PERIOD, 4)
r = 5
hdr = ["#","Expense category","Amount (ETB)","Basis / note"]
for c,h in enumerate(hdr, start=1):
    cell(ws, r, c, h, font=F(9, True, WHITE), fillc=NAVY, align="center", border=True)
r += 1
exp = [
    ("Professional, consulting & software (Corridor)", 641217.39, "Net of 15% VAT; WHT 19,236.52 withheld"),
    ("Salaries & wages (GM 80,000 + Accountant 15,000)", 95000.00, "Gross basic salaries — see Payroll"),
    ("Staff pension — employer 11%", 10450.00, "GM 8,800 + Accountant 1,650"),
    ("Rent — vehicle (4 months @ 40,000)", 160000.00, "Gross; WHT 4,800 (3%) withheld"),
    ("Rent — office/house (11 months @ 2,000)", 22000.00, "Gross; WHT 660 (3%) withheld"),
    ("Travel — air ticket", 303006.00, "Business travel; WHT 6,060.12"),
    ("Telecommunication & internet (Ethio Telecom)", 5224.00, "SIM/MSISDN + stamps"),
    ("Printing & stationery (Berhanena Selam)", 4500.06, "VAT/WHT receipt printing"),
    ("Staff training & meals (Romina PLC)", 5430.02, "Marketing team training"),
    ("Government fees, licensing & registration (DARS + notary)", 18534.00, "Document authentication + circular stamp"),
    ("Bank service charges", 45.31, "CBE transaction charges"),
    ("Depreciation — equipment (20% pool)", 97843.48, "Ethiopian pool method: 20% of 489,217 (computer portion may qualify for 25%)"),
]
first = r
n=1
for name,amt,note in exp:
    cell(ws, r, 1, n, align="center", border=True)
    cell(ws, r, 2, name, border=True, font=F(10), wrap=True)
    cell(ws, r, 3, amt, num=CURR, border=True)
    cell(ws, r, 4, note, border=True, font=F(9), wrap=True)
    n+=1; r+=1
cell(ws, r, 2, "TOTAL OPERATING EXPENSES", font=F(11, True), fillc=GOLD, border=True)
cell(ws, r, 3, f"=SUM(C{first}:C{r-1})", num=CURR, font=F(11, True), fillc=GOLD, border=True)
cell(ws, r, 4, "", border=True)

# ============================================================== 5. PAYROLL
ws = wb.create_sheet("5. Payroll Summary")
ws.sheet_view.showGridLines = False
for i,w in enumerate([4,26,10,13,13,13,13,13,13], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "PAYROLL SUMMARY", PERIOD, 9)
r = 5
hdr = ["#","Employee / position","Months","Monthly gross","Annual gross","Income tax","Pension EE 7%","Pension ER 11%","Net pay"]
for c,h in enumerate(hdr, start=1):
    cell(ws, r, c, h, font=F(9, True, WHITE), fillc=NAVY, align="center", border=True, wrap=True)
r += 1
# income tax per Ethiopian monthly schedule (Proc 1395/2017): computed on gross basic
pay = [
    ("Dr. Henok Fasil Telila — General Manager", 8, 10000.00, 2045.00, 700.00, 1100.00),
    ("Bethlehem (Beti) — Accountant", 3, 5000.00, 607.50, 350.00, 550.00),
]
first = r
n=1
for name,months,mg,itax_m,ee_m,er_m in pay:
    ag = mg*months; itax=itax_m*months; ee=ee_m*months; er=er_m*months
    net = ag - itax - ee
    cell(ws, r, 1, n, align="center", border=True)
    cell(ws, r, 2, name, border=True, font=F(10), wrap=True)
    cell(ws, r, 3, months, align="center", border=True)
    cell(ws, r, 4, mg, num=CURR, border=True)
    cell(ws, r, 5, ag, num=CURR, border=True)
    cell(ws, r, 6, itax, num=CURR, border=True)
    cell(ws, r, 7, ee, num=CURR, border=True)
    cell(ws, r, 8, er, num=CURR, border=True)
    cell(ws, r, 9, net, num=CURR, border=True)
    n+=1; r+=1
cell(ws, r, 2, "TOTAL", font=F(10, True), fillc=GOLD, border=True)
cell(ws, r, 3, "", fillc=GOLD, border=True)
cell(ws, r, 4, "", fillc=GOLD, border=True)
for c in [5,6,7,8,9]:
    L=get_column_letter(c)
    cell(ws, r, c, f"=SUM({L}{first}:{L}{r-1})", num=CURR, font=F(10, True), fillc=GOLD, border=True)
r += 2
cell(ws, r, 2, "Employment cost in Income Statement = Gross salaries 95,000 + Employer pension 10,450 = 105,450",
     font=F(9, True, BLUE)); ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=9); r+=1
cell(ws, r, 2, "Income tax shown is the standard monthly schedule on gross basic. Actual remittances (with late-filing "
     "interest/penalty for some months) are itemised in sheet 10 – Tax Summary.",
     font=F(8, italic=True, color="808080"), wrap=True)
ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=9); ws.row_dimensions[r].height=26

# ============================================================== 6. PENSION
ws = wb.create_sheet("6. Pension Summary")
ws.sheet_view.showGridLines = False
for i,w in enumerate([4,26,16,14,16,16,16], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "PENSION SUMMARY (Private Org. Employees Pension)", PERIOD, 7)
r = 5
hdr = ["#","Employee","Pensionable base","Employee 7%","Employer 11%","Total 18%","Note"]
for c,h in enumerate(hdr, start=1):
    cell(ws, r, c, h, font=F(9, True, WHITE), fillc=NAVY, align="center", border=True, wrap=True)
r += 1
pen = [
    ("Dr. Henok Fasil Telila (GM)", 80000.00, "8 months @ 10,000"),
    ("Bethlehem (Accountant)", 15000.00, "3 months @ 5,000"),
]
first=r; n=1
for name,base,note in pen:
    ee=base*0.07; er=base*0.11; tot=ee+er
    cell(ws, r, 1, n, align="center", border=True)
    cell(ws, r, 2, name, border=True, font=F(10))
    cell(ws, r, 3, base, num=CURR, border=True)
    cell(ws, r, 4, ee, num=CURR, border=True)
    cell(ws, r, 5, er, num=CURR, border=True)
    cell(ws, r, 6, tot, num=CURR, border=True)
    cell(ws, r, 7, note, border=True, font=F(9))
    n+=1; r+=1
cell(ws, r, 2, "TOTAL", font=F(10, True), fillc=GOLD, border=True)
for c in [3,4,5,6]:
    L=get_column_letter(c)
    cell(ws, r, c, f"=SUM({L}{first}:{L}{r-1})", num=CURR, font=F(10, True), fillc=GOLD, border=True)
cell(ws, r, 7, "", fillc=GOLD, border=True)
r+=2
cell(ws, r, 2, "Employee 7% is withheld from salary; Employer 11% is a company cost (in Expense Summary).",
     font=F(9, italic=True, color="555555")); ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=7)

# ============================================================== 7. INCOME STATEMENT
ws = wb.create_sheet("7. Income Statement")
ws.sheet_view.showGridLines = False
for i,w in enumerate([4,46,20,30], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "INCOME STATEMENT (Profit & Loss)", PERIOD, 4)
r = 5
def line(label, val=None, *, bold=False, fillc=None, num=CURR, note=None, indent=False):
    global r
    used = r
    cell(ws, r, 2, ("   " if indent else "")+label, font=F(11 if bold else 10, bold), fillc=fillc)
    if val is not None:
        cell(ws, r, 3, val, num=num, font=F(11 if bold else 10, bold), fillc=fillc, align="right")
    if note:
        cell(ws, r, 4, note, font=F(9, italic=True, color="808080"), wrap=True)
    r += 1
    return used

section(ws, r, "REVENUE", 4); r+=1
rv1=line("Service revenue — NBE project", 1243400.09, indent=True)
rv2=line("Service revenue — Ethiopian Economic Association", 839130.43, indent=True)
IS_REV=line("Total Revenue", f"=C{rv1}+C{rv2}", bold=True, fillc=LTBLUE)
r += 1
section(ws, r, "OPERATING EXPENSES", 4); r+=1
opex = [
    ("Professional, consulting & software", 641217.39),
    ("Salaries & wages", 95000.00),
    ("Staff pension — employer 11%", 10450.00),
    ("Rent — vehicle & office", 182000.00),
    ("Travel", 303006.00),
    ("Telecommunication & internet", 5224.00),
    ("Printing & stationery", 4500.06),
    ("Staff training & meals", 5430.02),
    ("Government fees, licensing & registration", 18534.00),
    ("Bank charges", 45.31),
    ("Depreciation — equipment (20% pool)", 97843.48),
]
erows=[line(name, val, indent=True) for name,val in opex]
IS_EXP=line("Total Operating Expenses", f"=SUM(C{erows[0]}:C{erows[-1]})", bold=True, fillc=LTBLUE)
r += 1
IS_PBT=line("NET PROFIT BEFORE TAX", f"=C{IS_REV}-C{IS_EXP}", bold=True, fillc=GOLD,
     note="= Total Revenue − Total Operating Expenses")
IS_TAX=line("Business profit tax @ 30%", f"=-C{IS_PBT}*0.3", note="30% of profit before tax (see Tax Summary)")
IS_NPAT=line("NET PROFIT AFTER TAX", f"=C{IS_PBT}+C{IS_TAX}", bold=True, fillc=GREEN)
IS_SHEET="'7. Income Statement'"
r += 1
cell(ws, r, 2, "Note: Equipment (SkyBlue, 489,217.39 net of VAT) is capitalised and depreciated at the 20% pool rate "
     "(computer portion may qualify for 25%). Corridor is expensed as services/subscriptions — the tax-favourable "
     "treatment. The 10% dividend tax is avoided by retaining rather than distributing profit.",
     font=F(8, italic=True, color="808080"), wrap=True)
ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=4); ws.row_dimensions[r].height=42

# ============================================================== 8. BALANCE SHEET
ws = wb.create_sheet("8. Balance Sheet")
ws.sheet_view.showGridLines = False
for i,w in enumerate([4,46,20,30], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "BALANCE SHEET — as at 07 July 2026 (Sene 30, 2018 E.C.)", PERIOD, 4)
r = 5
section(ws, r, "ASSETS", 4); r+=1
line("Non-current assets", None, bold=True)
bs_cost=line("Equipment — laptops, devices & furniture (at cost)", 489217.39, indent=True)
bs_dep=line("Less: accumulated depreciation (20% pool)", f"=-C{bs_cost}*0.2", indent=True, note="= 489,217 × 20%")
bs_nbv=line("Equipment — net book value", f"=C{bs_cost}+C{bs_dep}", indent=True)
line("Current assets", None, bold=True)
bs_cash=line("Cash at bank — CBE local a/c 1000723346235", 880172.79, indent=True)
bs_oc=line("Cash — CBE USD a/c / TeleBirr / cash on hand", 0.00, indent=True, note="⚠ To be confirmed by accountant")
bs_whtr=line("WHT receivable (creditable vs profit tax)", 62475.91, indent=True, note="Withheld by NBE 37,302 + EEA 25,173.91")
BS_TA=line("TOTAL ASSETS", f"=C{bs_nbv}+C{bs_cash}+C{bs_oc}+C{bs_whtr}", bold=True, fillc=GOLD)
r += 1
section(ws, r, "LIABILITIES", 4); r+=1
l_vat=line("VAT payable", 142814.48, indent=True, note="Settled 17 Jul 2026")
l_wht=line("Withholding tax payable (suppliers)", 33913.02, indent=True, note="Settled 13 Jul 2026")
l_pen=line("Pension payable", 2700.00, indent=True, note="Year-end accrual")
l_ptax=line("Business profit tax payable (gross)", f"=-{IS_SHEET}!C{IS_TAX}", indent=True, note="From Income Statement; net of WHT credit 62,476 → 153,308 to pay")
l_loan=line("Director's loan — Dr. Henok Fasil Telila", 300000.00, indent=True, note="Drawn FY2018; repaid 20 Aug 2026 (FY2019)")
l_adv=line("Director's advances (company costs paid personally)", 33688.08, indent=True, note="DARS, telecom, printing, meals, stamps")
l_oth=line("Other related-party financing", 50000.00, indent=True, note="09 Apr 2026 injection — confirm source")
# residual is a balancing figure (formula) so the statement always ties
BS_RES=r  # capture before writing (needs TE below); write placeholder now, fix formula after equity
l_res=line("Other payable / rounding (balancing figure)", 0, indent=True, note="⚠ = Assets − Equity − other liabilities; confirm with opening records")
BS_TL=line("TOTAL LIABILITIES", f"=SUM(C{l_vat}:C{l_res})", bold=True, fillc=LTBLUE)
r += 1
section(ws, r, "EQUITY", 4); r+=1
e_cap=line("Paid-up share capital", 50000.00, indent=True, note="First CBE credit, 15 Oct 2025")
e_re=line("Retained earnings (net profit after tax)", f"={IS_SHEET}!C{IS_NPAT}", indent=True,
     note="From Income Statement. ETB 700,000 cash earmarked for FY2019 cloud investment (directors' resolution)")
BS_TE=line("TOTAL EQUITY", f"=C{e_cap}+C{e_re}", bold=True, fillc=LTBLUE)
r += 1
# now set the residual formula = Total Assets − Total Equity − (other liabilities excl. residual)
cell(ws, l_res, 3, f"=C{BS_TA}-C{BS_TE}-SUM(C{l_vat}:C{l_oth})", num=CURR,
     font=F(10), align="right")
line("TOTAL LIABILITIES & EQUITY", f"=C{BS_TL}+C{BS_TE}", bold=True, fillc=GOLD)
r += 1
cell(ws, r, 2, "First-year balance sheet (opening balances nil). Director's total exposure = 333,688 "
     "(loan 300,000 + advances 33,688), repaid/repayable in FY2019. To confirm: USD-account / TeleBirr / "
     "cash balances and the source of the 09 Apr 2026 related-party injection.",
     font=F(9, italic=True, color="C00000"), wrap=True)
ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=4); ws.row_dimensions[r].height=40

# ============================================================== 9. CASH FLOW
ws = wb.create_sheet("9. Cash Flow")
ws.sheet_view.showGridLines = False
for i,w in enumerate([4,46,20,30], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "CASH FLOW STATEMENT — CBE operating account (direct method)", PERIOD, 4)
r = 5
cf_open=line("Opening cash (account opened during the year)", 0.00, bold=True)
r += 1
section(ws, r, "OPERATING ACTIVITIES", 4); r+=1
o1=line("Cash received from customers", 2332434.19, indent=True, note="EEA 939,826.09 + NBE 1,392,608.10")
o2=line("Paid to suppliers & services (Corridor + flight)", -1021175.00, indent=True)
o3=line("Paid to employees (salaries)", -95012.00, indent=True)
o4=line("Rent paid (vehicle + office)", -176552.00, indent=True)
o5=line("Taxes / pension remitted via bank", -11582.65, indent=True)
o6=line("Bank charges", -10.75, indent=True)
cf_op=line("Net cash from operating activities", f"=SUM(C{o1}:C{o6})", bold=True, fillc=LTBLUE)
r += 1
section(ws, r, "INVESTING ACTIVITIES", 4); r+=1
i1=line("Purchase of equipment (SkyBlue)", -547929.00, indent=True)
cf_inv=line("Net cash used in investing", f"=C{i1}", bold=True, fillc=LTBLUE)
r += 1
section(ws, r, "FINANCING ACTIVITIES", 4); r+=1
f1=line("Owner / related-party injections", 400000.00, indent=True, note="50,000 + 300,000 + 50,000")
cf_fin=line("Net cash from financing", f"=C{f1}", bold=True, fillc=LTBLUE)
r += 1
cf_net=line("NET INCREASE IN CASH", f"=C{cf_op}+C{cf_inv}+C{cf_fin}", bold=True, fillc=GOLD)
line("CLOSING CASH (CBE local a/c) ✓ ties to bank", f"=C{cf_open}+C{cf_net}", bold=True, fillc=GREEN)
r += 1
cell(ws, r, 2, "Covers the CBE local operating account (the account for which a statement exists). Expenses settled via "
     "TeleBirr/cash (DARS, Ethio Telecom, small items and the July VAT/WHT/pension remittances), funded by the "
     "director, are reflected on the accrual Income Statement, not in this account's cash flow.",
     font=F(9, italic=True, color="808080"), wrap=True)
ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=4); ws.row_dimensions[r].height=46

# ============================================================== 10. TAX SUMMARY
ws = wb.create_sheet("10. Tax Summary")
ws.sheet_view.showGridLines = False
for i,w in enumerate([4,44,20,30], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "TAX SUMMARY — VAT · WHT · Profit tax", PERIOD, 4)
r = 5
section(ws, r, "A) VALUE ADDED TAX (15%)", 4); r+=1
t_ov=line("Output VAT on sales (NBE 186,510.01 + EEA 125,869.57)", 312379.58, indent=True)
t_iv=line("Input VAT on purchases (SkyBlue 73,382.61 + Corridor 96,182.61)", -169565.22, indent=True)
line("Net VAT payable  (paid 17 Jul 2026, ref 2106569599999)", f"=C{t_ov}+C{t_iv}", bold=True, fillc=GOLD,
     note="e-Tax receipt 142,814.48")
r += 1
section(ws, r, "B) WITHHOLDING TAX (WHT) withheld & remitted by Helias", 4); r+=1
b1=line("On SkyBlue purchase (3%)", 14676.52, indent=True)
b2=line("On Corridor purchase (3%)", 19236.52, indent=True)
t_wsub=line("Sub-total supplier WHT (paid 13 Jul 2026, ref 2104995749999)", f"=C{b1}+C{b2}", bold=True, fillc=LTBLUE,
     note="e-Tax receipt 33,913.02")
b3=line("On vehicle rent (3%)", 4800.00, indent=True)
b4=line("On office/house rent (3%)", 660.00, indent=True)
line("Total WHT withheld", f"=C{t_wsub}+C{b3}+C{b4}", bold=True, fillc=GOLD)
r += 1
section(ws, r, "C) WHT credit — withheld from Helias by clients (creditable)", 4); r+=1
c1=line("By National Bank of Ethiopia", 37302.00, indent=True)
c2=line("By Ethiopian Economic Association", 25173.91, indent=True)
t_crd=line("Total creditable WHT", f"=C{c1}+C{c2}", bold=True, fillc=LTBLUE)
r += 1
section(ws, r, "D) BUSINESS PROFIT TAX (Schedule C)", 4); r+=1
d_pbd=line("Net profit before depreciation", 817123.74, indent=True)
d_dep=line("Less: capital depreciation allowance (20% pool)", -97843.48, indent=True,
     note="Computer portion may qualify for 25% → up to 122,304")
d_ti=line("Taxable business profit", f"=C{d_pbd}+C{d_dep}", indent=True)
d_pt=line("Profit tax @ 30%", f"=C{d_ti}*0.3", indent=True)
d_cr=line("Less: creditable WHT (section C)", f"=-C{t_crd}", indent=True)
line("Net profit tax payable", f"=C{d_pt}+C{d_cr}", bold=True, fillc=GOLD,
     note="Depreciation saves ~29,353 vs 182,661 before")
r += 1
section(ws, r, "E) EMPLOYMENT INCOME TAX & PENSION remitted (per e-Tax schedule)", 4); r+=1
etax = [
    ("Income tax — YE 12/2025", 10000.00),
    ("Income tax — YE 11/2025", 10000.00),
    ("Income tax — YE 04/2026", 10000.00),
    ("Income tax — YE 01/2026 (incl. penalty)", 3563.38),
    ("Income tax — YE 02/2026 (incl. penalty)", 3529.84),
    ("Income tax — YE 03/2026 (incl. penalty)", 3496.30),
    ("Pension — YE 03/2026 (incl. penalty)", 2005.20),
    ("Pension — YE 04/2026", 1800.00),
    ("Pension — YE 05/2026", 2700.00),
    ("Pension — YE 06/2026 (ref 2104558149999)", 2700.00),
]
et_rows=[line(name, val, indent=True) for name,val in etax]
line("Total employment tax & pension remitted", f"=SUM(C{et_rows[0]}:C{et_rows[-1]})", bold=True, fillc=LTBLUE)
r += 1
cell(ws, r, 2, "Note: several months were filed late and include interest & penalty; amounts above are as actually "
     "remitted (source: company e-Tax payment schedule).", font=F(8, italic=True, color="808080"), wrap=True)
ws.merge_cells(start_row=r,start_column=2,end_row=r,end_column=4); ws.row_dimensions[r].height=28

# ============================================================== 11. NOTES
ws = wb.create_sheet("11. Notes & Open Items")
ws.sheet_view.showGridLines = False
for i,w in enumerate([4,4,100], start=1):
    ws.column_dimensions[get_column_letter(i)].width = w
title_block(ws, "NOTES, ASSUMPTIONS & OPEN ITEMS FOR THE ACCOUNTANT", PERIOD, 3)
r = 5
notes = [
 ("H","Basis of preparation"),
 ("",  "Accrual basis; ETB; Ethiopian Budget Year 2018 E.C. (08 Jul 2025 – 07 Jul 2026). First operating year, so opening balances are nil. Figures reconciled across the CBE bank statement, the company WHT/VAT/Rent working papers, official receipts, and the FinPilot bot export."),
 ("H","Reconciliation & corrections"),
 ("",  "The FinPilot bot contained data-entry errors that have been corrected to the source documents: Corridor 718,613→718,169; SkyBlue 547,923→547,929; VAT 143,104.48→142,814.48; WHT 34,203.02→33,913.02; pension 2,706→2,700. Four bank transactions missing from the bot (car rent, GM salary, house rent, accountant salary) and three owner injections (400,000) were added. One duplicated EEA revenue line in the bot was excluded."),
 ("H","Revenue"),
 ("",  "The ETB 1,392,608.10 credit (bot counterparty 'HELIAS…PLC') is confirmed by the CBE receipt to be an inbound RTGS from the National Bank of Ethiopia to Helias's account — genuine service revenue, not an internal transfer."),
 ("H","Key judgements"),
 ("",  "1. Equipment (SkyBlue, 489,217.39 net of VAT) capitalised, not expensed; acquired ~5 days before year-end so nil depreciation this year (depreciation begins FY2019 — confirm rate: computers 20-25%, furniture 20%)."),
 ("",  "2. Corridor (641,217.39) expensed as consulting/software/subscriptions. If the 'product development / software' portion is capital, it should be capitalised & amortised — this would INCREASE current-year profit and profit tax."),
 ("",  "3. Export/foreign-sourced services may qualify for VAT zero-rating. The company charged 15% VAT on the NBE project; if it is an export of services, output VAT (186,510.01) may be recoverable — confirm with the Ministry."),
 ("",  "4. Salaries shown as gross basic; employment income tax on GM (10,000) taken at the standard monthly schedule. Confirm whether 10,000/5,000 are gross or net, and allowances (transport, etc.)."),
 ("H","Legitimate tax-reduction levers (applied / recommended)"),
 ("",  "1. APPLIED — Capital depreciation allowance: 20% pool on equipment = 97,843 deduction, cutting profit tax by ~29,353. Ethiopian pool method gives the full-year rate even though the asset was bought near year-end (no pro-rating). If the SkyBlue invoice itemises the laptop/computer portion, that portion qualifies for 25% (up to 122,304 deduction → ~36,691 saving)."),
 ("",  "2. Capture every remaining deductible: cloud/website hosting, bank charges (done), any interest on the director's loan, forex loss on the NBE inbound wire, and accrued year-end costs (audit/accountant/rent)."),
 ("",  "3. Corridor (641,217) fully expensed as consulting/software/subscriptions — the tax-favourable treatment — retained."),
 ("",  "4. The ETB 700,000 cloud investment reduces FY2019 tax when actually incurred (subscriptions fully deductible; hardware depreciated). It cannot be deducted retroactively in FY2018."),
 ("",  "5. FUTURE — register the cloud/data business with the Ethiopian Investment Commission for a possible income-tax holiday (2–6 years) + duty-free capital imports: the lawful route to materially cut future tax."),
 ("",  "6. Retaining rather than distributing the profit avoids the 10% dividend withholding tax."),
 ("",  "NOT permissible (would trigger reassessment + penalty + interest): deducting a cash 'reserve' from profit, under-declaring revenue, or backdating FY2019 spend into FY2018."),
 ("H","OPEN ITEMS — must be confirmed before submission"),
 ("O","Paid-up share capital confirmed at ETB 50,000 (per registration) — confirm fully paid."),
 ("O","USD account (1000755516612), TeleBirr (HELIAS0070) and cash-on-hand balances at 07 Jul 2026 — needed to complete the Balance Sheet (currently assumed nil)."),
 ("O","Director's / related-party loan: opening/closing balance and movements. Working papers list injections & 'got it back' repayments to Elsa Abebe, Eleni Abebe, Andualem Yaregal, Fasil Telila and Henok — reconcile to a single director-loan schedule. The Balance Sheet uses a balancing figure of 384,019.62 pending this."),
 ("O","Loan from Henok Fasil Telila: snapshot shows 1,000,000; repayment of 300,000 on 20 Aug 2026 (after year-end)."),
 ("O","Rent WHT (car 4,800 + house 660 = 5,460): confirm remittance to the Ministry."),
 ("O","Business travel (air ticket 303,006): keep boarding pass/itinerary & business purpose for deductibility."),
 ("O","Related-party pricing (vehicle & office rent from Fasil Telila): ensure market-rate documentation."),
 ("H","Documents on file (audit trail)"),
 ("",  "CBE bank statement; NBE & EEA revenue receipts; Corridor, SkyBlue & flight expense receipts; VAT/WHT/pension e-Tax receipts; pension & income declarations (Nov 2025, Dec 2025, Mar 2026, May 2026); commercial registration, business license & TIN certificate."),
]
for tag,text in notes:
    if tag=="H":
        cell(ws, r, 1, text, font=F(11, True, NAVY))
        ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=3)
    elif tag=="O":
        cell(ws, r, 2, "☐", font=F(11, True, "C00000"))
        cell(ws, r, 3, text, font=F(10), wrap=True)
    else:
        cell(ws, r, 3, text, font=F(10), wrap=True)
    # rough height
    ws.row_dimensions[r].height = max(16, 15*(1+len(text)//95))
    r += 1

# ------------------------------------------------------------------ save
wb.save(OUT)
print("WROTE", OUT, "with sheets:", wb.sheetnames)
