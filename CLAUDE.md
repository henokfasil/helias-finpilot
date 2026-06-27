# Helias FinPilot — Claude Code Documentation

**AI-assisted financial reporting and transaction intelligence system with Natural Language Chatbot and Ethiopian Tax Compliance.**

---

## Project Overview

**FinPilot** is a multi-tenant financial management system that:
- 📊 Captures transactions via Telegram bot, file upload, or Quick Add form
- 🤖 Uses AI (OpenAI/Gemini) to extract and classify transactions
- 💬 Provides natural language chatbot for querying financial data
- 💰 **Ethiopian Tax Compliance**: VAT (15%) and WHT (3%) calculations per Proclamations 1341/2016, 979/2008, 1395/2017
- 📈 Generates monthly/annual financial reports
- 🏗️ Built for Helias AI and Analytics, ready to scale to SaaS

---

## Tech Stack

| Component | Technology | Details |
|-----------|-----------|---------|
| **Backend** | Python 3.11+ | FastAPI, SQLAlchemy ORM |
| **Chat UI** | Streamlit | Dashboard at `https://helias-finpilot.streamlit.app/` |
| **Database** | PostgreSQL (Supabase) | Cloud-hosted, production-ready |
| **LLM - Chatbot** | Google Gemini | `gemini-2.5-flash` (free tier) |
| **LLM - Extraction** | OpenAI | `gpt-4o-mini` for transaction extraction |
| **Bot Framework** | python-telegram-bot | Telegram @bot integration |
| **Deployment** | Streamlit Cloud + VPS | Auto-deploys from GitHub |

---

## Key Features

### ✅ Transaction Management
- **Text Recording**: "Paid 3,500 ETB to Ethio Telecom for internet"
- **File Uploads**: Receipts/PDFs auto-extracted with vision AI
- **Quick Add Form**: New page (1a_Quick_Add) for fast transaction entry with category classification
- **Duplicate Detection**: Auto-detect and merge duplicates
- **Category Classification**: Auto-classify transactions
- **Confirmation Workflow**: Edit and validate before confirmation

### ✅ Natural Language Chatbot
- **Natural Language Queries**: "Show me all expenses from last month"
- **Aggregate Analysis**: "What are my total expenses by category?"
- **Spending Patterns**: "Which counterparty did I spend the most on?"
- **Real-time Responses**: Powered by Gemini + PostgreSQL
- **Multi-format Results**: Tables, summaries, insights

### ✅ **Ethiopian Tax Compliance** (NEW)
- **VAT (15%)**: 
  - Applied to all income/sales
  - Registration thresholds: Mandatory 2M ETB, Voluntary 1M ETB
  - Remittance: Within 30 days of month-end

- **WHT (3%)**: 
  - Goods: 3% if transaction > 20,000 ETB
  - Services: 3% if transaction > 10,000 ETB
  - Non-compliant: 30% (if no TIN + valid license)

- **Exemptions** (per Proclamation 979/2008):
  - 🏛️ Government services (DARS, ministries, etc.)
  - ✈️ Transport (flights, trains, tours, tickets)
  - 🏥 Healthcare (hospitals, doctors, medicines)
  - 🎓 Education (schools, universities, training)
  - 💡 Utilities (electricity, telecom, water)
  - 🌾 Agriculture (farm products, livestock)
  - ⛽ Fuel (petrol, diesel, gas)
  - 🏠 Residential (house sales, rentals)

### ✅ Financial Reports
- Monthly/Annual P&L, Balance Sheet, Cash Flow
- Tax calculations with exemption detection
- Multi-currency support (ETB, USD, etc.)
- Audit logging (immutable transaction history)

### ✅ Multi-Tenant Ready
- Single/multiple company support
- Tenant isolation via `company_id`
- Supabase PostgreSQL backend

---

## Architecture

```
FinPilot/
├── app/
│   ├── agents/
│   │   ├── chatbot.py          ← NL→SQL conversion + response formatting
│   │   ├── extraction.py       ← Transaction extraction (OpenAI)
│   │   ├── classification.py   ← Category matching
│   │   ├── validation.py       ← Completeness checks
│   │   └── reporting.py        ← Report generation
│   ├── models/                 ← SQLAlchemy ORM models
│   │   └── transaction.py      ← NOW includes counterparty_category field
│   ├── services/               ← Business logic (CRUD, reports)
│   ├── bot/                    ← Telegram bot handlers
│   ├── database.py             ← SQLAlchemy engine setup
│   ├── config.py               ← Environment configuration
│   └── main.py                 ← Bot entry point
│
├── dashboard/
│   ├── app.py                  ← Streamlit main app
│   ├── db.py                   ← Read-only database queries
│   ├── pages/
│   │   ├── 0_Chat.py           ← Chatbot interface
│   │   ├── 1_Transactions.py   ← Transaction ledger
│   │   ├── 1a_Quick_Add.py     ← Quick add with category classification (NEW)
│   │   ├── 2_Reports.py        ← Report viewer
│   │   ├── 3_Receipts.py       ← File uploads
│   │   ├── 4_Settings.py       ← Config management
│   │   ├── 5_Tax.py            ← Tax compliance (UPDATED - comprehensive WHT handling)
│   │   ├── 6_Income_Statement.py
│   │   ├── 7_Balance_Sheet.py
│   │   ├── 8_Cash_Flow.py
│   │   └── 99_Debug.py         ← Debug/diagnostics
│   └── components.py           ← Reusable UI components
│
├── scripts/
│   ├── seed_data.py            ← Initialize database
│   ├── migrate_add_counterparty_category.py  ← Add category column (NEW)
│   └── categorize_existing_transactions.py   ← Batch categorize (NEW)
│
├── .env                        ← Configuration (git-ignored)
├── .env.example                ← Template
├── requirements.txt            ← Dependencies
├── CLAUDE.md                   ← This file
└── README.md / DEPLOYMENT_GUIDE.md / etc.
```

---

## Tax Compliance Implementation

### Database Schema Update (June 28, 2026)
```sql
-- NEW COLUMN added to transactions table:
ALTER TABLE transactions ADD COLUMN counterparty_category VARCHAR(30) NULL;

-- Valid values:
-- "government"   → Exempt (DARS, ministries, etc.)
-- "transport"    → Exempt (flights, trains, tours)
-- "healthcare"   → Exempt (hospitals, doctors, medicines)
-- "education"    → Exempt (schools, universities)
-- "utilities"    → Exempt (electricity, telecom, water)
-- "agriculture"  → Exempt (farm products, livestock)
-- "fuel"         → Exempt (petrol, diesel, gas)
-- "residential"  → Exempt (house sales/rentals)
-- "business"     → Taxable (3% WHT if > 10k)
-- NULL           → Use keyword matching as fallback
```

### Tax Page (5_Tax.py) Features
1. **Two-tier exemption detection**:
   - Primary: Check explicit `counterparty_category` field
   - Fallback: Keyword matching in description/counterparty name

2. **Government Institution Keywords** (auto-exempts):
   - dars, dire, addis, government, federal, regional, ministry, authority
   - revenue, customs, immigration, police, defense, parliament, senate, council

3. **Three separate tables**:
   - Income Transactions → VAT (15%)
   - Taxable Expenses → WHT (3%)
   - **Exempt Transactions** → NO WHT (new in v2.1)

4. **Number Formatting** (Standardized 2026-06-28):
   - All amounts: `1,234,567.89` (commas, 2 decimals)
   - Consistent across all tables and KPI cards

5. **MoR Filing Summary**:
   - Total VAT obligation
   - Total WHT obligation
   - 30-day remittance deadline
   - Filing checklist

### Quick Add Transaction (1a_Quick_Add.py)
New dashboard page for rapid transaction entry:

**Features**:
- Transaction type selector (income/expense)
- Amount, date, currency fields
- Counterparty & description
- **WHT Category dropdown** with visual indicators:
  - 🏛️ Government Service
  - ✈️ Transport (Flights, Trains, Tours)
  - 🏥 Healthcare (Hospital, Doctor, Medicine)
  - 🎓 Education (School, University, Training)
  - 💡 Utilities (Electricity, Telecom, Water)
  - 🌾 Agriculture (Farm, Crops, Livestock)
  - ⛽ Fuel (Petrol, Diesel, Gas)
  - 🏠 Residential Property
  - 💼 Business (Regular Business Transaction)

- Real-time WHT calculation display
- Automatic counterparty creation
- Transaction saved with category classification

### Migration Scripts

**1. Add counterparty_category column**:
```bash
python3 scripts/migrate_add_counterparty_category.py
```
- Checks if column exists
- Adds column if missing
- Works for both SQLite and PostgreSQL

**2. Categorize existing transactions**:
```bash
python3 scripts/categorize_existing_transactions.py
```
- Scans all transactions without categories
- Matches against keyword lists
- Assigns proper counterparty_category
- Updates database automatically

---

## Configuration

### Environment Variables (`.env`)
```bash
# Database (Supabase PostgreSQL - pooler connection)
DATABASE_URL = "postgresql://postgres.XXXXX:PASSWORD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"

# Gemini API (for chatbot)
GEMINI_API_KEY = "AIza..."
GEMINI_VISION_MODEL = "gemini-2.5-flash"

# OpenAI (for extraction)
OPENAI_API_KEY = "sk-proj-..."
OPENAI_MODEL = "gpt-4o-mini"

# App config
APP_ENV = "production"
```

### Streamlit Secrets (`streamlit/secrets.toml`)
```toml
DATABASE_URL = "postgresql://postgres.XXXXX:PASSWORD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"
GEMINI_API_KEY = "AIza..."
GEMINI_VISION_MODEL = "gemini-2.5-flash"
```

---

## Development Workflow

### Local Setup
```bash
# Clone and setup
git clone https://github.com/henokfasil/helias-finpilot.git
cd helias-finpilot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env from .env.example
cp .env.example .env
# Edit .env with your credentials

# Initialize database
python3 << 'EOF'
from app.database import init_db
init_db()
EOF

# Run dashboard
streamlit run dashboard/app.py

# Categorize existing transactions (optional)
python3 scripts/categorize_existing_transactions.py
```

### Testing Tax Features
```bash
# View Tax page
# 1. Go to http://localhost:8501
# 2. Click "Tax (🧾)" in sidebar
# 3. Check Exempt Transactions section (DARS, etc. should appear there)

# Test Quick Add
# 1. Click "Quick Add (➕)" in sidebar
# 2. Record transaction with "Government" category
# 3. Go back to Tax page - transaction should be exempt
```

### Deploying Changes
```bash
git add .
git commit -m "description"
git push origin main
# Streamlit Cloud auto-deploys ~30 seconds after push
# Changes also sync to VPS via deployment script
```

---

## Deployment

### Streamlit Cloud (Production)
- **URL**: https://helias-finpilot.streamlit.app/
- **Repo**: GitHub (henokfasil/helias-finpilot)
- **Auto-deploy**: On `main` branch push
- **Secrets**: Set via Streamlit admin panel

### VPS Deployment
```bash
# 1. SSH into VPS
ssh root@88.164.54.132  # (or your VPS IP)

# 2. Navigate to project directory
cd /home/finpilot

# 3. Pull latest changes
git pull origin main

# 4. Activate venv and install deps
source venv/bin/activate
pip install -r requirements.txt

# 5. Run migrations on production database
python3 scripts/migrate_add_counterparty_category.py
python3 scripts/categorize_existing_transactions.py

# 6. Restart Streamlit service
systemctl restart finpilot-streamlit
# OR manually:
pkill -f "streamlit run"
nohup streamlit run dashboard/app.py --server.port 8501 > /var/log/finpilot.log 2>&1 &
```

### Docker (Optional)
```bash
docker-compose up -d
# Services: Streamlit (port 8501), API (port 8000)
```

---

## Database Schema

### Transactions Table (with Tax Fields)
```sql
transactions:
  id INT PRIMARY KEY
  company_id INT → companies.id
  transaction_type VARCHAR(20) → 'income', 'expense', 'transfer'
  transaction_date DATE
  amount DECIMAL(18,2)
  currency VARCHAR(3) → 'ETB', 'USD', etc.
  description TEXT
  counterparty_id INT → counterparties.id
  category_id INT → categories.id
  
  -- Ethiopian Tax Fields
  vat_amount DECIMAL(18,2) → VAT amount (15%)
  withholding_tax DECIMAL(18,2) → WHT amount (3%, 30%, etc.)
  is_vat_inclusive BOOLEAN → Is VAT included in amount?
  counterparty_category VARCHAR(30) → NEW: for exemption classification
    Values: 'government', 'transport', 'healthcare', 'education',
            'utilities', 'agriculture', 'fuel', 'residential', 'business'
  
  status VARCHAR(30) → 'confirmed', 'draft', 'needs_clarification'
  created_at TIMESTAMP
  updated_at TIMESTAMP
```

### Related Tables
```sql
categories: id, name, type, company_id, is_active
counterparties: id, name, type, company_id
companies: id, name, base_currency
audit_logs: id, action, entity_type, entity_id, old_value, new_value
reports: id, report_type, period_year, period_month, content
```

---

## Tax Compliance Reference

### VAT (15%) — Proclamation 1341/2016
- **Applies to**: All income/sales (15% of amount)
- **Registration**: Mandatory if > 2,000,000 ETB/year; Voluntary if > 1,000,000 ETB
- **Filing**: Last day of following month electronically
- **Remittance**: 30 days after month-end to Ministry of Revenues
- **Exemptions**: Food, utilities (≤200 kWh), healthcare, education, housing, government

### WHT (Withholding Tax) — Proclamations 979/2008, 1395/2017
- **Goods**: 3% if single transaction > 20,000 ETB
- **Services**: 3% if single transaction > 10,000 ETB
- **Non-compliant supplier**: 30% (if no TIN + valid license)
- **Import**: 3% advance tax on CIF value
- **Remittance**: Within 30 days of month-end
- **Penalties**: 10% non-compliance, 5% late filing (max 25%)

### Exemptions (NO WHT)
✅ Government offices and services  
✅ Transport (flights, trains, buses, tours)  
✅ Healthcare (hospitals, doctors, medicines)  
✅ Education (schools, universities)  
✅ Utilities (electricity, telecom, water)  
✅ Agriculture (unprocessed farm products)  
✅ Fuel (petrol, diesel, gas)  
✅ Residential property (sales and rentals)  

---

## Common Tasks

### Add a New Tax Category
1. Update `WHT_EXEMPT_KEYWORDS` in `dashboard/pages/5_Tax.py`
2. Add keyword to appropriate category
3. Update `CATEGORY_KEYWORDS` in `scripts/categorize_existing_transactions.py`
4. Run categorization script on production

### Fix Misclassified Transactions
```bash
# Option 1: Update via Quick Add form (for new transactions)
# Dashboard → Quick Add → Select correct category

# Option 2: Direct database update (for existing)
# UPDATE transactions SET counterparty_category = 'government' 
# WHERE counterparty ILIKE '%DARS%';

# Option 3: Batch re-categorize
python3 scripts/categorize_existing_transactions.py
```

### Debug Tax Calculations
1. Go to dashboard → 🧾 Tax page
2. Check "Exempt Transactions" section for proper classification
3. Verify counterparty_category field in Debug page
4. Run: `python3 scripts/categorize_existing_transactions.py`

### Change WHT Rate (if new proclamation)
Edit `dashboard/pages/5_Tax.py`:
```python
WHT_RATE = 0.03  # Change to new rate (e.g., 0.04 for 4%)
```

### Add New Exemption Category
1. Update database enum/validation in models
2. Add keywords to exemption lists
3. Update category dropdown in `1a_Quick_Add.py`
4. Test with new transactions

---

## Roadmap

### Completed (v2.1 — 2026-06-28)
- ✅ Ethiopian tax compliance (VAT 15%, WHT 3%)
- ✅ Exemption system with keyword matching
- ✅ Quick Add transaction form with category selection
- ✅ counterparty_category database field
- ✅ Migration scripts for production
- ✅ Standardized number formatting (1,234.56)
- ✅ Government institution detection (DARS, etc.)

### Phase 2 (Q3 2026)
- [ ] Telegram bot integration with category selection
- [ ] Transaction edit form with category update
- [ ] Export tax reports to PDF (MoR format)
- [ ] Tax calendar (filing deadlines)
- [ ] Compliance checklist

### Phase 3 (Q4 2026)
- [ ] Multi-company SaaS onboarding
- [ ] Subscription/billing (Chapa integration)
- [ ] Bank statement import with auto-categorization
- [ ] Tax dashboard with year-to-date metrics
- [ ] Email reminders for tax deadlines

---

## Support & Resources

- **Live Dashboard**: https://helias-finpilot.streamlit.app/
- **GitHub Repo**: https://github.com/henokfasil/helias-finpilot
- **Documentation**: See README.md, DEPLOYMENT_GUIDE.md in repo
- **Debug Page**: Dashboard → 🔧 Debug (database connection tester)
- **Issues**: Check Streamlit Cloud logs via admin panel
- **Contact**: hft4866@gmail.com

---

**Last Updated**: 2026-06-28  
**Status**: ✅ Fully Operational  
**Tax Compliance**: ✅ Live with Exemption Detection  
**Quick Add Form**: ✅ Ready for Production  
**Deployment**: ✅ Automated (GitHub → Streamlit Cloud + VPS)
