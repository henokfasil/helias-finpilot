# Helias AI — FY2018 E.C. Annual Financial Report

**Period:** 08 July 2025 – 07 July 2026 (Hamle 1 – Sene 30, 2018 E.C.)
**First operating year.** All opening balances are nil.

## Files in this folder

| File | Description |
|------|-------------|
| `Helias_FY2018_Financial_Report_ETB.xlsx` | 12-sheet reconciled annual report (all formulas live) |
| `Helias_ScheduleC_FY2018_FILLED.xlsx` | Official Ministry of Revenue Schedule C — filled |
| `Helias_FY2018_Comparison_Note.pdf` | Comparison note for the external accountant |
| `build_report.py` | Re-runnable generator — rebuilds both Excel files from scratch |

## Key figures (ETB, accrual)

| Line | Amount |
|------|-------:|
| Net revenue | 2,082,530.52 |
| Total expenses (incl. depreciation) | 1,363,250.26 |
| Net profit before tax | 719,280.26 |
| Profit tax @30% | 215,784.08 |
| Less: WHT credit | (62,475.91) |
| **Net tax to pay** | **153,308.17** |
| Net profit after tax | 503,496.18 |
| Cash at bank (closing, ties to CBE statement) | 880,172.79 |

## How to regenerate

```bash
cd reports/fy2018
pip install openpyxl
python3 build_report.py
# Writes Helias_FY2018_Financial_Report_ETB.xlsx
```

## FY2019+ workflow

1. Download the new CBE statement CSV
2. Run the importer (dry-run first):
   ```bash
   python3 scripts/import_cbe_statement.py "statement_fy2019.csv"
   python3 scripts/import_cbe_statement.py "statement_fy2019.csv" --commit
   ```
3. The dashboard auto-updates.
4. Copy `build_report.py` to `reports/fy2019/`, update the year constants, regenerate.
