# Helias FinPilot — Financial Reporting System

## How it works end-to-end

```
CBE bank statement (CSV)
        │
        ▼
scripts/import_cbe_statement.py   ← classifies, de-dupes, inserts to DB
        │
        ▼
Supabase (finpilot DB)            ← single source of truth
        │
        ├──▶ Dashboard pages      ← Income Statement, Balance Sheet,
        │    (live, auto-update)       Cash Flow, Tax — Ethiopian FY aware
        │
        └──▶ reports/fyXXXX/build_report.py
                   │
                   ▼
             Excel workbook (12 sheets, all formulas)
             + Schedule C (Ministry of Revenue form, filled)
```

---

## Per-year checklist (repeat every July)

### 1. Import the bank statement
```bash
# Preview (safe — no DB writes)
python3 scripts/import_cbe_statement.py "path/to/CBE_statement.csv"

# Commit new lines to production DB
DATABASE_URL=<supabase-url> python3 scripts/import_cbe_statement.py \
    "path/to/CBE_statement.csv" --commit --company 1
```

### 2. Check the dashboard
Open https://helias-finpilot.streamlit.app/
- **Income Statement** → select the new Ethiopian FY → verify totals
- **Balance Sheet** → select FY end date → verify it balances
- **Cash Flow** → confirm closing cash ties to bank ending balance
- **Tax** → confirm VAT net and WHT credit are correct

### 3. Generate the Excel report
```bash
cd reports/fyXXXX     # copy from previous year's folder
python3 build_report.py
# → Helias_FY????_Financial_Report_ETB.xlsx  (12 sheets, all formulas)
# → Helias_ScheduleC_FY????_FILLED.xlsx      (Ministry of Revenue form)
```

### 4. Send comparison note to accountant
```bash
cd /path/to/Dropbox/helias-financial_reporting
python3 make_comparison.py
# → Helias_FY????_Comparison_Note.pdf
```

### 5. Commit to GitHub
```bash
git add reports/fyXXXX/
git commit -m "Add FY???? E.C. annual financial report"
git push origin main
```

---

## Folder structure

```
helias-finpilot/
├── scripts/
│   └── import_cbe_statement.py   ← CBE CSV importer (reusable every year)
│
├── reports/
│   ├── fy2018/
│   │   ├── build_report.py                         ← regenerate Excel
│   │   ├── Helias_FY2018_Financial_Report_ETB.xlsx ← 12-sheet report
│   │   ├── Helias_ScheduleC_FY2018_FILLED.xlsx     ← Ministry form
│   │   ├── Helias_FY2018_Comparison_Note.pdf       ← accountant note
│   │   └── README.md
│   └── fy2019/                                     ← add next year
│
└── dashboard/pages/
    ├── 6_Income_Statement.py   ← Ethiopian FY selector + download button
    ├── 7_Balance_Sheet.py      ← Ethiopian FY end date selector + download
    └── 8_Cash_Flow.py          ← Ethiopian FY selector
```

---

## FY2018 E.C. — key verified figures

| | ETB |
|---|--:|
| Net revenue | 2,082,530.52 |
| Total expenses (incl. depreciation 97,843) | 1,363,250.26 |
| Profit before tax | 719,280.26 |
| Tax @30% | 215,784.08 |
| Less WHT credit | (62,475.91) |
| **Net tax to pay** | **153,308.17** |
| Net profit after tax | 503,496.18 |
| Cash at bank (closing, verified vs CBE) | 880,172.79 |

Sources reconciled: CBE bank statement · e-Tax receipts · supplier receipts ·
WHT/VAT/rent working papers · Supabase FinPilot DB (difference = 0.00 ETB).

---

## Equipment depreciation pool (Ethiopian tax, 20%)

| FY | Cost | Opening pool | Depreciation | Closing pool |
|----|-----:|-------------:|-------------:|-------------:|
| 2018 E.C. | 489,217.39 | 489,217.39 | 97,843.48 | 391,373.91 |
| 2019 E.C. | + additions | 391,373.91 | TBD | TBD |

Computer/laptop portion may qualify for 25% — confirm with accountant when
the SkyBlue invoice is itemised.

---

## Notes

- The Supabase project is **cjsasjycoeagccwsnvmb** (Henok's — do NOT touch
  `xqxqvbgbycczaqkspvyz` which is the engineer's project).
- A full pre-change backup lives in `transactions_bak_fy2018_recon` in the DB.
- The director's loan (300,000 drawn, repaid 20 Aug 2026) is in `account_snapshots`.
