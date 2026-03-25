---
name: Helias FinPilot Project
description: Phase 1 MVP of AI-assisted financial reporting system for Helias AI and Analytics
type: project
---

Helias FinPilot is a Telegram-first financial transaction management system built for Helias AI and Analytics (Ethiopia). Phase 1 MVP was fully implemented and verified working.

**Why:** Replace manual financial tracking with an AI-assisted Telegram bot that extracts transactions from natural language and files, stores them in a structured DB, and generates monthly/annual reports.

**Stack:** Python 3.9, python-telegram-bot v20+, SQLAlchemy 2.0, SQLite (dev)/PostgreSQL (prod), OpenAI gpt-4o-mini (text) + gpt-4o (vision)

**Project root:** `/Users/henok/Library/CloudStorage/OneDrive-Universita'degliStudidiRomaTorVergata/1_aaaamyBusiness/Helias/Financial_Reporting_AI/`

**Key architecture decisions:**
- Multi-tenant from day 1 (companies table as tenant entity)
- All data linked to company_id for future SaaS expansion
- Transactions are immutable once confirmed — corrections create new entries
- Audit log is append-only, never modified
- In-memory conversation state (bot/state.py) — Phase 2 will use Redis
- Categories are seeded via scripts/seed_data.py, not hardcoded

**How to apply:** When continuing work on this project, the venv is at `./venv/`, DB is `finpilot.db` (SQLite), already seeded with Helias AI company and 18 categories.

**To run:** Set `TELEGRAM_BOT_TOKEN` in `.env` then `venv/bin/python3 -m app.main`
