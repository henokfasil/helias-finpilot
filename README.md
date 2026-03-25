# Helias FinPilot

**AI-assisted financial reporting and transaction intelligence system.**

Telegram-first. Built for Helias AI and Analytics. Architected to scale to multi-tenant SaaS.

---

## Phase 1 MVP Features

| Feature | Status |
|---|---|
| Telegram bot (text transactions) | ✅ |
| File upload (images, PDFs) | ✅ |
| AI extraction (OpenAI) | ✅ |
| Confirmation flow | ✅ |
| Clarification questions | ✅ |
| Duplicate detection | ✅ |
| Category classification | ✅ |
| Monthly reports | ✅ |
| Annual reports | ✅ |
| Audit logging | ✅ |
| Multi-tenant architecture | ✅ (single company, ready to scale) |
| SQLite (dev) / PostgreSQL (prod) | ✅ |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- A Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API key

### 2. Setup

```bash
# Clone / navigate to project
cd Financial_Reporting_AI

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set:
#   TELEGRAM_BOT_TOKEN=...
#   OPENAI_API_KEY=...       (already set)
#   DEFAULT_ADMIN_TELEGRAM_ID=...  (your Telegram user ID)
```

### 3. Get your Telegram user ID

Send a message to [@userinfobot](https://t.me/userinfobot) on Telegram — it will reply with your user ID.

### 4. Seed the database

```bash
python scripts/seed_data.py
```

### 5. Run the bot

```bash
python -m app.main
```

---

## Docker Deployment

```bash
# Build and run
docker-compose up --build -d

# View logs
docker-compose logs -f
```

---

## Production (PostgreSQL)

1. Update `.env`:
   ```
   DATABASE_URL=postgresql://user:password@host:5432/finpilot
   ```
2. Uncomment the `db:` service in `docker-compose.yml`
3. Run migrations (or `init_db()` will auto-create tables)

---

## Using the Bot

### Send a transaction

```
Paid 3,500 ETB to Ethio Telecom for internet
```

```
Received $400 from Addis Tech for consulting work
```

```
Bought office supplies, 1,200 ETB cash
```

The bot will:
1. Extract the transaction using AI
2. Show you a preview with all extracted fields
3. Ask you to confirm: **yes** / **no** / **edit**

### Upload a receipt

Just send a photo or PDF — the bot will extract the transaction automatically.

### Commands

| Command | Description |
|---|---|
| `/start` | Register and get started |
| `/help` | Show all commands |
| `/transactions` | List recent transactions |
| `/pending` | Show unconfirmed items |
| `/summary` | Quick financial snapshot (this month) |
| `/monthly_report` | Generate this month's report |
| `/report 2026-03` | Report for specific month |
| `/annual_report` | Full year report |
| `/annual_report 2025` | Report for specific year |
| `/search Ethio Telecom` | Search transactions |
| `/export` | Export confirmed transactions as CSV |

### Editing a transaction

After seeing the preview, reply `edit` and then:
```
amount: 3600
```
or
```
counterparty: Ethio Telecom
```

---

## Architecture

```
app/
├── config.py              — Environment settings
├── database.py            — SQLAlchemy engine + session
├── main.py                — Entry point
│
├── models/                — SQLAlchemy ORM models
│   ├── company.py         — Tenant entity
│   ├── user.py            — Telegram users
│   ├── transaction.py     — Core financial records
│   ├── attachment.py      — Uploaded files
│   ├── category.py        — Configurable categories
│   ├── counterparty.py    — Clients / vendors
│   ├── audit_log.py       — Immutable audit trail
│   ├── clarification.py   — Pending questions
│   └── report.py          — Generated reports
│
├── agents/                — AI processing components
│   ├── extraction.py      — Text → structured transaction (OpenAI)
│   ├── classification.py  — Category matching
│   ├── validation.py      — Completeness checks
│   └── reporting.py       — AI narrative generation
│
├── services/              — Business logic
│   ├── transaction_service.py  — CRUD + summaries
│   ├── file_service.py         — File storage + text extraction
│   ├── report_service.py       — Report assembly
│   └── audit_service.py        — Audit logging
│
├── bot/                   — Telegram bot
│   ├── bot.py             — Application setup
│   ├── commands.py        — Command handlers
│   ├── handlers.py        — Message + file pipeline
│   ├── state.py           — In-memory conversation state
│   └── utils.py           — Formatting helpers
│
└── prompts/               — AI prompt templates
    ├── extraction.py
    └── reporting.py

scripts/
└── seed_data.py           — Initial company + categories

uploads/                   — Stored files (gitignored)
```

---

## Database Schema

| Table | Purpose |
|---|---|
| `companies` | Tenant entity (multi-tenant ready) |
| `users` | Telegram users per company |
| `transactions` | Financial records (core table) |
| `attachments` | Uploaded files linked to transactions |
| `categories` | Configurable category tree per company |
| `counterparties` | Auto-managed client/vendor list |
| `audit_logs` | Immutable audit trail (append-only) |
| `clarification_requests` | Bot ↔ user question/answer history |
| `reports` | Generated reports (stored for reference) |

---

## Transaction Lifecycle

```
User sends text/file
       ↓
Extraction Agent (OpenAI)
       ↓
Validation Agent
       ↓
     valid?
    /      \
  No        Yes
   ↓          ↓
Ask user    Preview + ask
clarification  confirmation
       ↓          ↓
       ↓       yes/no/edit
       ↓          ↓
       └──→  Save as "confirmed"
                  ↓
             Audit log entry
```

---

## Future Roadmap

### Phase 2
- Multi-user per company (roles + permissions)
- Webhook mode (replace polling)
- Redis-backed conversation state
- Exchange rate auto-fetch (NBE API)
- Email report delivery
- Web dashboard (FastAPI + React)

### Phase 3
- Multi-company SaaS onboarding
- Subscription/billing (Chapa integration)
- Mobile OCR improvements
- Bank statement import (PDF parsing)
- Ethiopian tax calculations

### Phase 4
- Analytics dashboard
- AI-powered anomaly detection
- Multi-language support (Amharic)
- API for third-party integrations

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | — | From @BotFather |
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key |
| `OPENAI_MODEL` | | `gpt-4o-mini` | Model for text extraction |
| `OPENAI_VISION_MODEL` | | `gpt-4o` | Model for image/file processing |
| `DATABASE_URL` | | `sqlite:///./finpilot.db` | DB connection string |
| `APP_ENV` | | `development` | `development` or `production` |
| `APP_LOG_LEVEL` | | `INFO` | Log verbosity |
| `UPLOAD_DIR` | | `./uploads` | Where to store files |
| `DEFAULT_COMPANY_NAME` | | `Helias AI and Analytics` | Initial company name |
| `DEFAULT_COMPANY_CURRENCY` | | `ETB` | Base currency |
| `DEFAULT_ADMIN_TELEGRAM_ID` | | — | Your Telegram user ID |

---

*Helias FinPilot — Built for Helias AI and Analytics*
