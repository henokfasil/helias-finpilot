# Helias FinPilot — Deployment Guide

## Architecture Overview

```
Telegram Bot (Mac/VPS)
        │
        ▼
Supabase PostgreSQL (cloud DB, free)
        │
        ▼
Streamlit Cloud Dashboard (free, public URL)
```

- **Bot** runs locally or on VPS, writes transactions to Supabase
- **Supabase** is the shared database both bot and dashboard use
- **Streamlit Cloud** reads from Supabase and serves the dashboard publicly

---

## 1. Supabase (Database)

### First-time setup
1. Go to supabase.com → sign up free
2. New project → set name and password
3. Wait ~2 min for provisioning
4. Click **Connect** (top of dashboard) → Connection String → **Session pooler** URI
5. Copy URI: `postgresql://postgres.[ref]:[password]@aws-1-eu-west-1.pooler.supabase.com:5432/postgres`

> ⚠️ Use **Session Pooler** URL, NOT Direct Connection — direct connection is IPv6 only and won't work on most networks.

### Run schema migration (first time only)
```bash
# From project root
venv/bin/python3 -c "from app.database import init_db; init_db()"
venv/bin/python3 scripts/seed_data.py
```

### Credentials (save securely)
- Project ref: `cjsasjycoeagccwsnvmb`
- Region: EU West 1 (Frankfurt)
- Pooler URL: `postgresql://postgres.cjsasjycoeagccwsnvmb:[password]@aws-1-eu-west-1.pooler.supabase.com:5432/postgres`

---

## 2. GitHub

### First-time setup
```bash
git init
git add -A
git commit -m "Initial commit"
git remote add origin https://[TOKEN]@github.com/henokfasil/helias-finpilot.git
git push -u origin main
```

### Every time you make changes (REQUIRED before Streamlit updates)
```bash
git add -A
git commit -m "describe your change"
git push
```

> 🔴 **IMPORTANT:** Streamlit Cloud reads directly from GitHub. If you don't push, the live dashboard will NOT update. Always push before expecting changes to appear online.

### Repo
- URL: https://github.com/henokfasil/helias-finpilot
- Visibility: Public (no secrets in code — .env is gitignored)
- Token: stored in git remote URL (no expiry)

---

## 3. Streamlit Cloud (Dashboard)

### First-time setup
1. Go to share.streamlit.io → sign in with GitHub
2. Click **Deploy now** (public app from GitHub)
3. Fill in:
   - Repository: `henokfasil/helias-finpilot`
   - Branch: `main`
   - Main file: `dashboard/app.py`
4. Click **Advanced settings → Secrets** and paste:

```toml
DATABASE_URL = "postgresql://postgres.cjsasjycoeagccwsnvmb:[password]@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"
APP_ENV = "production"
APP_LOG_LEVEL = "INFO"
UPLOAD_DIR = "./uploads"
DEFAULT_COMPANY_NAME = "Helias AI and Analytics"
DEFAULT_COMPANY_CURRENCY = "ETB"
DEFAULT_ADMIN_TELEGRAM_ID = "442192616"
```

5. Click **Deploy**

### Live URL
**https://helias-finpilot.streamlit.app**

### Auto-redeploy
Every `git push` to `main` triggers an automatic redeploy. No manual action needed.

### Update secrets
Streamlit Cloud dashboard → your app → ⋮ menu → **Settings → Secrets**

---

## 4. Telegram Bot

### Run locally (Mac)
```bash
cd "/Users/henok/Library/CloudStorage/OneDrive-.../Financial_Reporting_AI"
pkill -f "app.main" 2>/dev/null
nohup venv/bin/python3 -m app.main > finpilot.log 2>&1 &
```

### Check if running
```bash
ps aux | grep "app.main" | grep -v grep
```

### View logs
```bash
tail -f finpilot.log
```

### Bot token
`8742477185:AAG2WnfKi7hLH6cq3Syf9wZ9hhEFAnjGpRg`

---

## 5. Full workflow after any code change

```bash
# 1. Make your code changes
# 2. Push to GitHub (triggers Streamlit redeploy automatically)
git add -A && git commit -m "your message" && git push

# 3. Restart bot if bot code changed
pkill -f "app.main" 2>/dev/null
nohup venv/bin/python3 -m app.main > finpilot.log 2>&1 &
```

---

## 6. Environment variables summary

| Variable | Where set | Value |
|---|---|---|
| `DATABASE_URL` | `.env` (bot) + Streamlit secrets | Supabase pooler URL |
| `TELEGRAM_BOT_TOKEN` | `.env` only | Bot token |
| `OPENAI_API_KEY` | `.env` only | OpenAI key |
| `APP_ENV` | Both | `production` |

---

*Last updated: 2026-03-25*
