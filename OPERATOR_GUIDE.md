# Helias FinPilot — Operator & Onboarding Guide

**For: Helias AI and Analytics — Internal Use & Client Deployment**
**Version: 1.0 | Phase 1 MVP**
**Last Updated: 2026-03-25**

---

## What Is Helias FinPilot?

Helias FinPilot is a Telegram-based AI financial assistant that helps small and medium businesses (SMEs) in Ethiopia and Africa:

- Record daily transactions by simply sending a message or photo
- Extract structured data from receipts, invoices, and screenshots automatically
- Generate monthly and annual financial reports
- Maintain a full audit trail without manual bookkeeping

**No accounting knowledge required. No app to install. Works entirely through Telegram.**

---

## Part 1 — How the Bot Works (For Clients)

### 1.1 Sending a Transaction

The client simply types a message in plain language:

| What They Type | What the Bot Does |
|---|---|
| `Paid 3,500 ETB to Ethio Telecom for internet` | Extracts: expense, 3500 ETB, Ethio Telecom, Internet/Telecom |
| `Received $400 from Addis Tech for consulting` | Extracts: income, 400 USD, Addis Tech, Consulting |
| `Bought 2 chairs for office, 4,800 birr cash` | Extracts: expense, 4800 ETB, Equipment, cash |
| *(send a photo of a receipt)* | Reads the receipt using AI vision, extracts all fields |

### 1.2 Confirmation Flow

After every transaction, the bot shows a preview:

```
💸 Extracted Transaction

Type:         expense
Amount:       3500 ETB
Date:         2026-03-25
Counterparty: Ethio Telecom
Description:  internet service
Category:     Internet & Telecom
Confidence:   100%

Is this correct? Reply:
  ✅ yes — save it
  ❌ no — discard it
  ✏️ edit — correct a field
```

The client replies:
- **yes** → saved and confirmed
- **no** → discarded (nothing is saved)
- **edit** → bot asks which field to change, then re-shows preview

### 1.3 Supported File Types

Clients can send:
- 📸 Photos (receipts, invoices, handwritten notes)
- 📄 PDF documents (bank statements, invoices)
- Any file with a caption like "office rent invoice March"

### 1.4 Commands Available to Clients

| Command | What It Does |
|---|---|
| `/start` | Register with the system |
| `/help` | Show all commands |
| `/transactions` | List recent 15 transactions |
| `/pending` | Show unconfirmed entries |
| `/summary` | Quick income/expense snapshot for this month |
| `/monthly_report` | Full report for current month |
| `/report 2026-03` | Report for a specific month |
| `/annual_report` | Full year report with AI narrative |
| `/search Ethio Telecom` | Find transactions by keyword |
| `/export` | Download all confirmed transactions as CSV |
| `/delete 42` | Remove a wrong transaction by its ID |

### 1.5 Editing a Wrong Entry

If a client saved wrong data:
1. Send `/transactions` → find the ID number (e.g. `#12`)
2. Send `/delete 12`
3. Re-enter the correct transaction as a new message

---

## Part 2 — Onboarding a New SME Client

### Step 1 — Create a Telegram Bot for the Client

1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Enter bot display name: e.g. `Acme Finance Bot`
4. Enter bot username: e.g. `acme_finance_bot` (must end in `bot`)
5. Copy the token: `7XXXXXXXXX:AAF...`

> **Important:** Each client company gets their own dedicated bot. Do NOT share one bot between multiple companies.

### Step 2 — Deploy the System for This Client

**Option A — Run on the client's own machine (Phase 1 approach):**

```bash
# 1. Copy the project to their machine or a server
# 2. Create their .env file
cp .env.example .env
```

Edit `.env` with their details:
```
TELEGRAM_BOT_TOKEN=<their bot token>
OPENAI_API_KEY=<your shared or their own OpenAI key>
DATABASE_URL=sqlite:///./finpilot_acme.db
DEFAULT_COMPANY_NAME=Acme Trading PLC
DEFAULT_COMPANY_CURRENCY=ETB
DEFAULT_ADMIN_TELEGRAM_ID=<client's Telegram user ID>
```

```bash
# 3. Set up and run
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/seed_data.py
nohup python -m app.main > finpilot.log 2>&1 &
```

**Option B — Run on a central server (recommended for selling to multiple clients):**

Deploy on a Linux VPS (e.g. the server at `72.60.133.179`). Each client gets:
- Their own `.env` file
- Their own database file
- Their own bot token
- Run as a separate process or Docker container

### Step 3 — Configure Categories for the Client

Default categories are seeded automatically. To customise for a specific business type, edit `scripts/seed_data.py` before first run, or add categories directly to the database.

**Example: For a restaurant client, replace:**
- Cloud & API Costs → Food & Ingredients
- Contractors → Kitchen Staff
- Software Subscriptions → Equipment Maintenance

### Step 4 — Register the Client as Admin User

The client sends `/start` to their bot from their Telegram account. The system automatically registers them as admin of their company.

### Step 5 — Test Before Handover

Send these test messages and verify responses:

```
1. "Paid 500 ETB for coffee and supplies" → should extract expense
2. Send any receipt photo → should extract from image
3. /summary → should show 0 income, 500 ETB expense
4. /monthly_report → should generate a report
5. /delete 1 → should delete the test transaction
```

---

## Part 3 — What to Tell Clients

### 3.1 What the bot CAN do

- ✅ Record income and expenses from text or photos
- ✅ Categorise transactions automatically
- ✅ Generate monthly and annual financial summaries
- ✅ Export data as CSV for their accountant
- ✅ Track who paid what and when
- ✅ Never lose a receipt (all files are stored)
- ✅ Ask clarifying questions if something is unclear

### 3.2 What the bot CANNOT do (Phase 1)

- ❌ Connect directly to a bank account
- ❌ File taxes automatically
- ❌ Handle payroll calculations
- ❌ Support multiple users at the same time (Phase 2)
- ❌ Work offline (requires internet)
- ❌ Replace a certified accountant for audit purposes

### 3.3 Data & Privacy

- All transaction data is stored locally on the server running the bot
- Raw text and files are preserved for audit purposes
- Nothing is shared with third parties except OpenAI (for AI extraction only)
- Clients should be informed that message content is sent to OpenAI for processing

---

## Part 4 — Pricing Guidance (For Helias Sales Team)

> Suggested pricing model for selling to Ethiopian SMEs (Phase 2 SaaS):

| Tier | Target | Suggested Price | Includes |
|---|---|---|---|
| Starter | Solo traders, freelancers | 500 ETB/month | 1 user, 100 transactions/month, monthly report |
| Business | SMEs (5–20 employees) | 1,500 ETB/month | 3 users, unlimited transactions, annual report |
| Professional | Growing companies | 3,500 ETB/month | 10 users, multi-currency, custom categories, export |
| Enterprise | Large SMEs | Custom | Dedicated server, custom integrations, training |

**Setup fee (one-time):** 2,000–5,000 ETB depending on customisation needed.

---

## Part 5 — Common Client Questions & Answers

**Q: What if I send the wrong amount?**
> Use `/transactions` to find the ID, then `/delete [ID]`. Re-send the correct message.

**Q: What if the bot misunderstands my message?**
> Reply `no` when it shows the preview. Then try sending the message more clearly, e.g. include the amount, currency, and who you paid.

**Q: Can I use it in Amharic?**
> The AI understands some Amharic context, but English works more reliably in Phase 1. Amharic support is planned for Phase 2.

**Q: What currencies does it support?**
> ETB (Birr), USD, and EUR. Always include the currency in your message if it's not ETB.

**Q: Can my accountant access the reports?**
> Use `/export` to get a CSV file. Share it directly with your accountant. Web access is planned for Phase 2.

**Q: What happens if the internet goes down?**
> The bot is unavailable during outages. Transactions sent during that time are queued by Telegram and processed when the connection returns.

**Q: Is my financial data safe?**
> Yes. Data is stored on a private server. Only the transaction text is sent to OpenAI for extraction — your full financial history stays on your server.

---

## Part 6 — Operator Maintenance

### Checking if the Bot is Running

```bash
ps aux | grep "app.main" | grep -v grep
```

### Restarting the Bot

```bash
pkill -f "app.main"
cd /path/to/Financial_Reporting_AI
nohup venv/bin/python3 -m app.main > finpilot.log 2>&1 &
```

### Viewing Logs

```bash
tail -f finpilot.log          # live log stream
tail -100 finpilot.log        # last 100 lines
grep "ERROR" finpilot.log     # errors only
```

### Backing Up Client Data

```bash
# Back up the database daily
cp finpilot.db backups/finpilot_$(date +%Y-%m-%d).db
```

### Auto-Restart on Crash (macOS)

Create `/Library/LaunchAgents/com.helias.finpilot.plist` — contact Helias tech team for the configuration file.

---

## Part 7 — Upgrade Path to SaaS (Phase 2)

When Helias FinPilot grows into a full SaaS product, this is the planned evolution:

1. **Central server** — All clients run on one server, fully isolated by `company_id`
2. **Web dashboard** — Clients log in at `finpilot.helias.ai` to view reports
3. **Billing** — Chapa integration for monthly subscription payments
4. **Multi-user** — Multiple staff per company with role-based access
5. **Bank integration** — Import statements from Ethiopian banks
6. **Amharic support** — Full language support for local users

The current database schema already supports all of the above — the `companies` table acts as the tenant separator. No data migration required to upgrade.

---

## Contact & Support

**Helias AI and Analytics**
For technical issues, contact the Helias tech team before escalating to clients.

---

*This document is internal to Helias AI and Analytics. Do not share with clients directly.*
