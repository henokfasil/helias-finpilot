# Helias FinPilot — Claude Code Documentation

**AI-assisted financial reporting and transaction intelligence system with Natural Language Chatbot.**

---

## Project Overview

**FinPilot** is a multi-tenant financial management system that:
- 📊 Captures transactions via Telegram bot or file upload
- 🤖 Uses AI (OpenAI/Gemini) to extract and classify transactions
- 💬 Provides natural language chatbot for querying financial data
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
| **Deployment** | Streamlit Cloud | Auto-deploys from GitHub |

---

## Key Features

### ✅ Transaction Management
- Text: "Paid 3,500 ETB to Ethio Telecom for internet"
- File uploads: Receipts/PDFs auto-extracted with vision AI
- Duplicate detection, category auto-classification
- Confirmation workflow with edit capability

### ✅ Chatbot (NEW)
- **Natural Language Queries**: "Show me all expenses from last month"
- **Aggregate Analysis**: "What are my total expenses by category?"
- **Spending Patterns**: "Which counterparty did I spend the most on?"
- **Real-time Responses**: Powered by Gemini + PostgreSQL
- **Multi-format Results**: Tables, summaries, insights

### ✅ Financial Reports
- Monthly/Annual P&L, Balance Sheet, Cash Flow
- Tax calculations (VAT, withholding tax)
- Multi-currency support (ETB, USD, etc.)
- Audit logging (immutable transaction history)

### ✅ Multi-Tenant Ready
- Single company (configurable)
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
│   │   ├── 0_Chat.py           ← Chatbot interface (NEW)
│   │   ├── 1_Transactions.py   ← Transaction ledger
│   │   ├── 2_Reports.py        ← Report viewer
│   │   ├── 3_Receipts.py       ← File uploads
│   │   ├── 4_Settings.py       ← Config management
│   │   ├── 5_Tax.py            ← Tax calculations
│   │   ├── 6_Income_Statement.py
│   │   ├── 7_Balance_Sheet.py
│   │   ├── 8_Cash_Flow.py
│   │   └── 99_Debug.py         ← Debug/diagnostics
│   └── components.py           ← Reusable UI components
│
├── scripts/
│   └── seed_data.py            ← Initialize database
│
├── .env                        ← Configuration (git-ignored)
├── .env.example                ← Template
├── requirements.txt            ← Dependencies
├── docker-compose.yml          ← Docker setup
└── README.md / CHATBOT_SETUP.md/ etc.
```

---

## Chatbot Implementation

### How It Works
```
User Question
    ↓
Gemini API: "Generate SQL from this question"
    ↓
SQL Query generated
    ↓
Execute against PostgreSQL (Supabase)
    ↓
Get results (17 transactions, totals, etc.)
    ↓
Gemini API: "Summarize these results naturally"
    ↓
Display formatted response in chat
```

### Key Files
- **`app/agents/chatbot.py`**: Core chatbot logic
  - `generate_sql_query()`: NL→SQL using Gemini
  - `execute_query()`: Execute SQL, return results
  - `format_response()`: Make results human-readable
  - `chat()`: Main entry point

- **`dashboard/pages/0_Chat.py`**: Streamlit UI
  - Chat message history
  - Example queries sidebar
  - Real-time response display
  - Error handling with diagnostics

### SQL Generation
Gemini is given:
1. Database schema (tables, columns, relationships)
2. Specific examples (simple SELECT, GROUP BY aggregates, JOINs)
3. Rules (always filter by company_id and status='confirmed')
4. Instructions (return ONLY valid SQL, no markdown)

### Critical Fixes Applied
- ✅ Model format: Use `models/gemini-2.5-flash` (not just `gemini-2.5-flash`)
- ✅ Connection pooling: Use `pool_pre_ping=True` for Supabase
- ✅ SQL truncation bug: Don't cut off at first newline (multi-line SQL support)
- ✅ Aggregate queries: Proper GROUP BY with all required columns
- ✅ Error handling: Graceful fallback to simple table formatting

---

## Configuration

### Environment Variables (`.env`)
```bash
# Database (Supabase PostgreSQL - pooler connection)
DATABASE_URL = "postgresql://postgres.cjsasjycoeagccwsnvmb:PASSWORD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"

# Gemini API (for chatbot)
GEMINI_API_KEY = "AIza..."
GEMINI_VISION_MODEL = "gemini-2.0-flash"

# OpenAI (for extraction)
OPENAI_API_KEY = "sk-proj-..."
OPENAI_MODEL = "gpt-4o-mini"

# App config
APP_ENV = "production"
DATABASE_URL = "postgresql://..." # Production DB
```

### Streamlit Secrets (`streamlit/secrets.toml`)
```toml
DATABASE_URL = "postgresql://postgres.cjsasjycoeagccwsnvmb:PASSWORD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"
GEMINI_API_KEY = "AIza..."
GEMINI_VISION_MODEL = "gemini-2.0-flash"
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

# Run dashboard
streamlit run dashboard/app.py
```

### Testing the Chatbot
```bash
# Local testing (in Python shell)
from app.agents.chatbot import chat
response = chat("Show me all transactions", company_id=1, db_url="postgresql://...")
print(response)
```

### Deploying Changes
```bash
git add .
git commit -m "description"
git push origin main
# Streamlit Cloud auto-deploys ~30 seconds after push
```

---

## Database Schema

### Core Tables
```sql
-- Transactions (main financial records)
transactions:
  id, transaction_date, transaction_type (income/expense/transfer)
  amount, currency, description
  payment_method, reference_number, status (confirmed/draft/needs_clarification)
  category_id, counterparty_id, company_id
  vat_amount, withholding_tax, activity_type
  ai_confidence, raw_text, created_at

-- Categories (customizable per company)
categories: id, name, type (income/expense/transfer), company_id, is_active

-- Counterparties (auto-managed client/vendor list)
counterparties: id, name, contact_info, company_id

-- Companies (multi-tenant support)
companies: id, name, base_currency, created_at

-- Audit Log (immutable transaction history)
audit_logs: id, action, entity_type, entity_id, old_value, new_value, created_at

-- Reports (saved generated reports)
reports: id, report_type, period_year, period_month, content, created_at
```

---

## Deployment

### Streamlit Cloud (Production)
- **URL**: https://helias-finpilot.streamlit.app/
- **Repo**: GitHub (henokfasil/helias-finpilot)
- **Auto-deploy**: On `main` branch push
- **Secrets**: Set via Streamlit admin panel
  - DATABASE_URL (Supabase pooler)
  - GEMINI_API_KEY
  - GEMINI_VISION_MODEL

### VPS Deployment (Optional)
```bash
# Docker setup
docker-compose up -d

# Or manual:
# 1. Install Python 3.11+
# 2. pip install -r requirements.txt
# 3. Set environment variables
# 4. streamlit run dashboard/app.py --server.port 80
```

---

## Known Issues & Limitations

### Chatbot
- ✅ Works for: simple SELECT, aggregates (SUM, COUNT), GROUP BY, filtering
- ⚠️ Limitations: No JOIN to multiple tables (only categories + counterparties)
- ⚠️ No write operations (read-only)
- ⚠️ Results limited to 1000 rows per query

### Free Tier
- Gemini: 60 requests/minute (usually ~2 per question)
- Supabase: Row-level security, pooler connection required

---

## Common Tasks

### Add a New Chat Example Question
Edit `dashboard/pages/0_Chat.py`:
```python
examples = [
    "Show me all transactions",  # existing
    "Your new question here",    # add this
]
```

### Improve SQL Generation
Edit the prompt in `app/agents/chatbot.py` `generate_sql_query()`:
```python
prompt = f"""..your improved prompt..."""
```

### Change LLM Model
Update `app/config.py`:
```python
gemini_vision_model: str = Field("models/gemini-2.5-flash", env="GEMINI_VISION_MODEL")
```

### Debug Database Issues
1. Go to dashboard → 🔧 Debug page
2. Click "Test Database Connection"
3. Shows exact error or success

---

## Next Steps / Roadmap

### Phase 2 (Future)
- [ ] Multi-step reasoning ("What was my trend over Q1?")
- [ ] Chart generation from query results
- [ ] Saved query templates
- [ ] Natural language report generation
- [ ] Telegram bot integration with chatbot

### Phase 3
- [ ] Multi-company SaaS onboarding
- [ ] Subscription/billing (Chapa)
- [ ] Mobile app
- [ ] Bank statement import (PDF)
- [ ] Ethiopian tax compliance

---

## Support & Resources

- **Documentation**: See README.md, CHATBOT_SETUP.md, DEPLOYMENT_GUIDE.md
- **Debug**: Use 🔧 Debug page in dashboard
- **Issues**: Check Streamlit Cloud logs via admin panel
- **Contact**: hft4866@gmail.com

---

**Last Updated**: 2026-06-27  
**Status**: ✅ Fully Operational  
**Chatbot Status**: ✅ Live and Working
