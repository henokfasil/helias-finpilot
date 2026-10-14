# Helias FinPilot — Claude Code Documentation

**AI-assisted financial reporting and transaction intelligence system for Helias AI and Analytics PLC.
Ethiopian-tax-aware, CBE-reconciled, Ministry-of-Revenue-ready.**

---

## Company & Legal Context

| Field | Value |
|-------|-------|
| **Company** | Helias AI and Analytics PLC |
| **TIN** | 0098960114 |
| **Commercial Registration** | AACATB/2/0242251/2018 |
| **Business Licence** | AACATB/14/707/44611365/2018 |
| **General Manager** | Dr. Henok Fasil Telila |
| **Address** | Addis Ababa, Lemi Kura Sub-City, Woreda 05 |
| **Paid-up capital** | ETB 50,000 |
| **First operating year** | FY2018 E.C. (08 Jul 2025 – 07 Jul 2026) |
| **VAT registered** | Yes (15%) |
| **CBE local account** | 1000723346235 |
| **CBE USD account** | 1000755516612 |
| **Supabase project** | `cjsasjycoeagccwsnvmb` ← HENOK'S — do NOT touch `xqxqvbgbycczaqkspvyz` (engineer's) |

---

## Project Overview

**FinPilot** is the single source of truth for Helias's finances:
- 📱 Captures transactions via Telegram bot, file upload, or Quick Add form
- 🤖 Uses AI (OpenAI/Gemini) to extract and classify transactions
- 💬 Natural language chatbot for querying financial data
- 💰 Ethiopian tax compliance: VAT 15%, WHT 3%, profit tax 30% (Proc. 1341/2016, 979/2008, 1395/2017)
- 📊 Live dashboard: Income Statement, Balance Sheet, Cash Flow, Tax — all Ethiopian FY aware
- 📁 Annual reports: 12-sheet Excel (all formulas) + filled Schedule C (Ministry of Revenue)
- 🏦 CBE bank-statement importer: one command per year reconciles the DB to the bank

---

## Tech Stack

| Component | Technology | Details |
|-----------|-----------|---------|
| **Backend** | Python 3.11+ | FastAPI, SQLAlchemy ORM |
| **Dashboard** | Streamlit | https://helias-finpilot.streamlit.app/ |
| **Database** | PostgreSQL (Supabase) | Cloud-hosted, project `cjsasjycoeagccwsnvmb` |
| **LLM — Chatbot** | Google Gemini | `gemini-2.5-flash` |
| **LLM — Extraction** | OpenAI | `gpt-4o-mini` |
| **Bot** | python-telegram-bot | Telegram |
| **Report generation** | openpyxl, reportlab | Excel (12 sheets) + PDF |
| **Deployment** | Streamlit Cloud + VPS | Auto-deploys on `main` push |

---

## Repository Structure

```
helias-finpilot/
├── app/
│   ├── agents/
│   │   ├── chatbot.py          ← NL→SQL + response formatting (Gemini)
│   │   ├── extraction.py       ← Transaction extraction (OpenAI vision)
│   │   ├── classification.py   ← Category matching
│   │   ├── validation.py       ← Completeness checks
│   │   └── reporting.py        ← AI narrative generation
│   ├── models/                 ← SQLAlchemy ORM models
│   │   └── transaction.py      ← includes activity_type, counterparty_category,
│   │                              vat_amount, withholding_tax, is_vat_inclusive
│   ├── services/               ← Business logic (CRUD, reports)
│   ├── bot/                    ← Telegram bot handlers
│   ├── database.py             ← SQLAlchemy engine setup
│   ├── config.py               ← Environment config
│   └── main.py                 ← Bot entry point
│
├── dashboard/
│   ├── app.py                  ← Streamlit main app
│   ├── db.py                   ← Read-only DB queries (load_financial_data, load_tax_data, etc.)
│   └── pages/
│       ├── 0_Chat.py           ← Chatbot interface
│       ├── 1_Transactions.py   ← Transaction ledger
│       ├── 1a_Quick_Add.py     ← Fast transaction entry with WHT category dropdown
│       ├── 2_Reports.py        ← Report viewer
│       ├── 3_Receipts.py       ← File uploads
│       ├── 4_Settings.py       ← Config management
│       ├── 5_Tax.py            ← VAT/WHT compliance (exemption detection, MoR summary)
│       ├── 6_Income_Statement.py ← Ethiopian FY selector, depreciation, download button
│       ├── 7_Balance_Sheet.py  ← Ethiopian FY end-date selector, download button
│       ├── 8_Cash_Flow.py      ← Ethiopian FY selector, activity_type grouping
│       └── 99_Debug.py         ← DB diagnostics
│
├── scripts/
│   ├── import_cbe_statement.py          ← CBE CSV importer (see Annual Workflow)
│   ├── seed_data.py                     ← Initialize DB
│   ├── migrate_add_counterparty_category.py
│   └── categorize_existing_transactions.py
│
├── reports/
│   └── fy2018/                          ← FY2018 E.C. complete record
│       ├── build_report.py              ← Regenerates Excel from scratch
│       ├── Helias_FY2018_Financial_Report_ETB.xlsx  ← 12-sheet report (all formulas)
│       ├── Helias_ScheduleC_FY2018_FILLED.xlsx      ← Ministry Schedule C (filled)
│       ├── Helias_FY2018_Comparison_Note.pdf        ← Accountant diff note
│       └── README.md
│
├── FINANCIAL_REPORTING.md      ← Year-by-year workflow (start here each July)
├── CLAUDE.md                   ← This file
├── .env                        ← Secrets (git-ignored)
└── .env.example
```

---

## FY2018 E.C. — Verified Financial Summary

**Period:** 08 July 2025 – 07 July 2026 (Hamle 1 – Sene 30, 2018 E.C.) — first operating year.
All figures reconciled across: CBE bank statement ↔ WHT/VAT working papers ↔ supplier receipts ↔ this DB. Difference = **0.00 ETB**.

### Income Statement

| Line | ETB |
|------|----:|
| Revenue — NBE/Deloitte project (net) | 1,243,400.09 |
| Revenue — Ethiopian Economic Association (net) | 839,130.43 |
| **Total net revenue** | **2,082,530.52** |
| Professional services / Corridor (opex) | 641,217.39 |
| Salaries & wages | 95,000.00 |
| Employer pension (11%) | 10,450.00 |
| Vehicle rent | 160,000.00 |
| Office/house rent | 22,000.00 |
| Travel (air ticket) | 303,006.00 |
| Telecom | 5,224.00 |
| Printing, registration, training, bank charges | 33,353.87 |
| **Depreciation (20% pool on 489,217 equipment)** | **97,843.48** |
| **Total expenses** | **1,363,250.26** |
| **Profit before tax** | **719,280.26** |
| Tax @30% | 215,784.08 |
| Less: WHT credit (clients withheld for us) | (62,475.91) |
| **Net profit tax to pay** | **153,308.17** |
| **Net profit after tax** | **503,496.18** |

### Balance Sheet (as at 07 Jul 2026)

| Assets | ETB | Liabilities & Equity | ETB |
|--------|----:|----------------------|----:|
| Equipment at cost | 489,217.39 | Net VAT payable | 142,814.35 |
| Less depreciation | (97,843.48) | Supplier WHT payable | 33,913.02 |
| Cash at bank (CBE) | 880,172.79 | Pension payable | 2,700.00 |
| Cash on hand | 4,016.47 | Profit tax payable | 215,784.08 |
| WHT receivable | 62,475.91 | Director's loan | 300,000.00 |
| | | Director's advances | 33,688.08 |
| | | Other financing | 50,000.00 |
| | | Share capital | 50,000.00 |
| | | Retained earnings | 503,496.18 |
| **Total** | **1,338,038.08** | **Total** | **1,338,038.08** ✓ |

### VAT summary
- Output VAT collected: 312,379.58
- Input VAT on purchases: 169,565.22
- **Net VAT payable: 142,814.35** (paid 17 Jul 2026, ref 2106569599999)

### Per-revenue profit
| | NBE project | EEA project |
|---|--:|--:|
| Revenue | 1,243,400 | 839,130 |
| Profit before tax | 429,455 | 289,825 |
| Net tax to pay | 91,535 | 61,774 |
| **Net profit (keep)** | **300,619** | **202,878** |

### Company vs individual tax saving
Running as a company (deductible expenses + 30% flat rate + WHT credit) saved **~ETB 517,000** compared to receiving the same income personally (no expense deductions, 35% progressive rate).

---

## Annual Reporting Workflow (repeat every July)

See `FINANCIAL_REPORTING.md` for the full checklist. Summary:

```bash
# 1. Import new CBE statement (dry-run first)
python3 scripts/import_cbe_statement.py "CBE_FY2019.csv"
python3 scripts/import_cbe_statement.py "CBE_FY2019.csv" --commit

# 2. Verify dashboard shows correct FY totals
# → https://helias-finpilot.streamlit.app/  → select FY on each page

# 3. Generate Excel report
cp -r reports/fy2018 reports/fy2019
# edit year constants in build_report.py
python3 reports/fy2019/build_report.py

# 4. Commit and push
git add reports/fy2019/
git commit -m "Add FY2019 E.C. annual financial report"
git push origin main
```

### import_cbe_statement.py — how it works
- Parses the CBE CSV (Value Date, Narration, Debit, Credit, Reference)
- Classifies each line: operating / investing / financing, income / expense / transfer
- De-duplicates against existing `transactions.reference_number` (the FT… code)
- Dry-run by default; `--commit` writes to production DB
- All 15 FY2018 bank lines produce closing cash = **880,172.79** (verified)

---

## Database — Key Tables & Fields

### transactions
```sql
id, company_id, transaction_type ('income'|'expense'|'transfer'),
transaction_date, amount, currency,
activity_type ('operating'|'investing'|'financing'),  ← drives Cash Flow
vat_amount, withholding_tax, is_vat_inclusive,        ← drives Tax page
counterparty_id, category_id, description,
payment_method, reference_number,                     ← CBE ref = FT…
status ('confirmed'|'draft'|'needs_clarification'),
source ('bank_reconciliation'|'telegram'|'cbe_import'|…),
is_duplicate, duplicate_of_id,
raw_text, ai_confidence, ai_ambiguity_flags
```

### account_snapshots
Manual Balance Sheet entries (fixed assets, loans, capital):
```sql
id, company_id, account_name, account_type ('asset'|'liability'|'equity'),
account_subtype ('director_loan'|'fixed_asset'|…),
amount, currency, entry_date, notes, is_active
```
Current entries:
- `Loan from Henok Fasil Telila` — liability/director_loan — **300,000** (drawn FY2018; repaid 20 Aug 2026, ref FT26232RGC8G → FY2019 event)

### counterparties (key ones)
| id | name |
|----|------|
| 4 | Henok Fasil Telila |
| 19 | ETHIOPIAN ECONOMIC ASSOCIATION |
| 25 | National Bank of Ethiopia (revenue payer for ETB 1,392,608.10) |
| 26 | Fasil Telila (Lessor) — vehicle & office rent |
| 27 | Owner/Related Party (financing injections) |

### Backup tables (FY2018 reconciliation)
`transactions_bak_fy2018_recon` and `counterparties_bak_fy2018_recon` — full pre-change snapshot; one SQL command reverts everything.

---

## Dashboard Pages

### 6_Income_Statement.py
- **Ethiopian FY selector** — auto-detects available FYs from DB, shows `FY2018 E.C. (2025/07/08–2026/07/07)`
- Computes 20% depreciation pool on equipment transactions
- Formal P&L table with revenue, opex by category, depreciation, income-tax line, NPAT
- Waterfall chart; monthly breakdown view
- **Download Excel report** button (if `reports/fyXXXX/` file exists)

### 7_Balance_Sheet.py
- **Ethiopian FY end-date selector** — picks the correct as-of date per FY
- Assets = cash (computed) + equipment snapshots; Liabilities from tax fields + account_snapshots; Equity = capital + retained earnings
- Asset composition pie + funding structure pie
- Download Excel report button

### 8_Cash_Flow.py
- **Ethiopian FY selector** replacing the old Gregorian year picker
- Groups by `activity_type`: operating / investing / financing
- Waterfall + inflow/outflow bars; monthly operating trend

### 5_Tax.py
- Two-tier WHT exemption: explicit `counterparty_category` → keyword fallback
- Three tables: income (VAT 15%), taxable expenses (WHT 3%), exempt transactions
- MoR filing summary: net VAT, net WHT, 30-day deadline
- WHT credit (withheld by clients from Helias) surfaced as a credit line

---

## Tax Compliance Reference

### Profit tax (Schedule C, companies)
- Rate: **30% flat** on taxable profit
- Depreciation: **20% pool** (computers may qualify for 25%)
- WHT credit: amounts withheld by clients and paid to Ministry on your behalf are **directly deductible** from the 30% figure
- MAT: 2.5% of turnover — applies only if higher than the standard 30% calculation (it never was in FY2018)

### VAT (15%) — Proc. 1341/2016
- Input VAT on purchases **nets against** output VAT — show net payable, not gross on both sides
- Export/foreign-sourced services may qualify for zero-rating — confirm with Ministry

### WHT (3%) — Proc. 979/2008, 1395/2017
- Services > 10,000 ETB; goods > 20,000 ETB
- Rent: 3% (withheld from payment to lessor)
- Counterparty_category exemptions: government, transport, healthcare, education, utilities, agriculture, fuel, residential

### Ethiopian depreciation pool
| FY | Asset cost | Opening pool | Depreciation (20%) | Closing pool |
|----|----------:|-------------:|-------------------:|-------------:|
| 2018 E.C. | 489,217.39 | 489,217.39 | 97,843.48 | 391,373.91 |
| 2019 E.C. | + additions | 391,373.91 | TBD | TBD |

---

## FY2018 Reconciliation — Bot Corrections Applied

The bot had data-entry errors corrected to source receipts (Oct 2026):

| Field | Bot had | Correct | Source |
|-------|---------|---------|--------|
| Corridor amount | 718,613 | 718,169 | CBE receipt FT2618383G9L |
| SkyBlue amount | 547,923 | 547,929 | CBE receipt FT2618363HQ1 |
| VAT paid | 143,104.48 | 142,814.48 | e-Tax ref 2106569599999 |
| WHT paid | 34,203.02 | 33,913.02 | e-Tax ref 2104995749999 |
| Pension paid | 2,706 | 2,700 | e-Tax ref 2104558149999 |
| NBE revenue counterparty | HELIAS AI… (wrong) | National Bank of Ethiopia | CBE receipt FT26177H6WV9 |

**8 bank lines added** (were missing from bot): car rent, GM salary, house rent, accountant salary, 3 owner injections, bank charge. After corrections, bot CBE cash = **880,172.79** (difference from bank = **0.00**).

---

## Configuration

### Environment Variables (`.env`)
```bash
DATABASE_URL = "postgresql+psycopg://postgres.cjsasjycoeagccwsnvmb:PASSWORD@..."
GEMINI_API_KEY  = "AIza..."
GEMINI_VISION_MODEL = "gemini-2.5-flash"
OPENAI_API_KEY  = "sk-proj-..."
OPENAI_MODEL    = "gpt-4o-mini"
APP_ENV         = "production"
```

### Streamlit Secrets (`~/.streamlit/secrets.toml`)
```toml
DATABASE_URL    = "postgresql+psycopg://..."
GEMINI_API_KEY  = "AIza..."
OPENAI_API_KEY  = "sk-proj-..."
```

---

## Development Workflow

```bash
# Setup
git clone https://github.com/henokfasil/helias-finpilot.git
cd helias-finpilot
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in credentials

# Run dashboard locally
streamlit run dashboard/app.py

# Deploy (Streamlit Cloud auto-deploys on push)
git add . && git commit -m "description" && git push origin main
```

---

## Deployment

| Environment | Details |
|------------|---------|
| **Streamlit Cloud** | https://helias-finpilot.streamlit.app/ — auto-deploys on `main` push |
| **GitHub** | https://github.com/henokfasil/helias-finpilot |
| **Supabase** | `cjsasjycoeagccwsnvmb` (eu-west-1) |

---

## Roadmap

### Completed (v3.0 — Oct 2026)
- ✅ FY2018 E.C. full annual report (12-sheet Excel + Schedule C + comparison PDF)
- ✅ CBE bank-statement importer (`scripts/import_cbe_statement.py`)
- ✅ Ethiopian FY selector on Income Statement, Balance Sheet, Cash Flow
- ✅ Depreciation (20% pool) computed in Income Statement
- ✅ WHT credit surfaced as a deduction in tax computation
- ✅ Download Excel report button on financial-statement pages
- ✅ DB reconciled to CBE bank (difference 0.00 ETB)
- ✅ Backup tables for FY2018 pre-correction state
- ✅ FINANCIAL_REPORTING.md — annual checklist

### Completed (v2.1 — Jun 2026)
- ✅ Ethiopian tax compliance (VAT 15%, WHT 3%, exemption detection)
- ✅ Quick Add transaction form with WHT category dropdown
- ✅ counterparty_category field + migration + batch categorisation
- ✅ Standardised number formatting (1,234,567.89)

### Next (Phase 2)
- [ ] Telegram `/add_asset` `/add_liability` bot commands (manual Balance Sheet entries)
- [ ] Tax calendar page (filing deadlines, remittance dates)
- [ ] Auto-generate Schedule C PDF directly from the dashboard
- [ ] Bank statement upload via Telegram (triggers importer)
- [ ] FY2019 report (next July — run the Annual Workflow above)

### Phase 3 (SaaS)
- [ ] Multi-company onboarding, Chapa billing, email reminders

---

## Support & Resources

- **Live Dashboard**: https://helias-finpilot.streamlit.app/
- **GitHub**: https://github.com/henokfasil/helias-finpilot
- **Annual workflow**: `FINANCIAL_REPORTING.md`
- **FY2018 report files**: `reports/fy2018/`
- **Debug page**: Dashboard → 🔧 Debug
- **Contact**: hft4866@gmail.com

---

**Last Updated**: October 2026
**Status**: ✅ Fully Operational — FY2018 reconciled and filed
**Supabase DB**: `cjsasjycoeagccwsnvmb` (Henok's — do NOT touch `xqxqvbgbycczaqkspvyz`)
