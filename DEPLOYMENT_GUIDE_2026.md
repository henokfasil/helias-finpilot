# FinPilot Deployment Guide (Updated 2026-06-28)

Complete guide for deploying FinPilot with tax compliance features to production (Streamlit Cloud + VPS).

---

## Quick Deploy Checklist

### Local Development
- [ ] Clone repo: `git clone https://github.com/henokfasil/helias-finpilot.git`
- [ ] Create venv: `python3 -m venv venv && source venv/bin/activate`
- [ ] Install deps: `pip install -r requirements.txt`
- [ ] Copy config: `cp .env.example .env && edit .env`
- [ ] Init database: `python3 -c "from app.database import init_db; init_db()"`
- [ ] Run locally: `streamlit run dashboard/app.py`
- [ ] Test Tax page: Navigate to Tax (🧾) and verify exemptions

### Streamlit Cloud (Automatic)
- [x] Connected to GitHub repo
- [x] Auto-deploys on `git push origin main`
- [x] Secrets configured via admin panel
- [ ] Live at: https://helias-finpilot.streamlit.app/

### Production VPS
- [ ] SSH into VPS
- [ ] Pull latest code
- [ ] Run migrations
- [ ] Restart Streamlit service
- [ ] Verify at: VPS_IP:8501

---

## Detailed Deployment Steps

### 1. Streamlit Cloud Deployment (Automatic)

**Status**: ✅ Already configured  
**URL**: https://helias-finpilot.streamlit.app/  
**How**: Push to GitHub → Auto-deploys in 30-60 seconds

**Verify**:
```bash
# After pushing code, check:
# 1. GitHub Actions (if configured)
# 2. Streamlit Cloud dashboard
# 3. https://helias-finpilot.streamlit.app/Tax (check tax page updates)
```

**Troubleshooting**:
- If old version showing: Hard refresh browser (Cmd+Shift+R)
- Check Streamlit Cloud logs for errors
- Verify secrets in admin panel

---

### 2. VPS Deployment (Manual)

#### Prerequisites
- VPS IP: `88.164.54.132` (or your configured IP)
- SSH access: `ssh root@88.164.54.132`
- Python 3.11+ installed
- PostgreSQL client (psql)

#### Deployment Steps

**Step 1: SSH into VPS**
```bash
ssh root@88.164.54.132

# If key-based auth:
ssh -i ~/.ssh/vps_key root@88.164.54.132
```

**Step 2: Navigate to project directory**
```bash
cd /home/finpilot
# Or wherever your project is located
```

**Step 3: Pull latest code**
```bash
git fetch origin
git pull origin main

# Verify changes
git log --oneline -5
```

**Step 4: Activate virtual environment**
```bash
source venv/bin/activate
# Verify: should see (venv) in prompt

# If venv doesn't exist:
python3 -m venv venv
source venv/bin/activate
```

**Step 5: Install/update dependencies**
```bash
pip install --upgrade pip
pip install -r requirements.txt

# Verify key packages:
python3 -c "import streamlit; print(f'Streamlit {streamlit.__version__}')"
python3 -c "import sqlalchemy; print(f'SQLAlchemy {sqlalchemy.__version__}')"
```

**Step 6: Run database migrations**

```bash
# Migration 1: Add counterparty_category column (if not exists)
python3 scripts/migrate_add_counterparty_category.py

# Expected output:
# ✅ Added counterparty_category column to transactions table
# OR
# ℹ️  counterparty_category column already exists

# Migration 2: Categorize existing transactions
python3 scripts/categorize_existing_transactions.py

# This will show:
# 📊 Found X transactions without categories
# ✅ Updated: Y transactions
# ⏭️  Skipped (no match): Z transactions
```

**Step 7: Restart Streamlit service**

Option A (systemd service):
```bash
# If you have a systemd service configured:
sudo systemctl restart finpilot-streamlit
sudo systemctl status finpilot-streamlit

# View logs:
sudo journalctl -u finpilot-streamlit -f
```

Option B (Manual restart):
```bash
# Kill old process
pkill -f "streamlit run"
sleep 2

# Start fresh
nohup streamlit run dashboard/app.py \
  --server.port 8501 \
  --logger.level=error \
  > /var/log/finpilot.log 2>&1 &

# Verify it's running
sleep 5
curl -s http://localhost:8501 | head -c 50
```

**Step 8: Verify deployment**
```bash
# Check if service is running
ps aux | grep streamlit

# Check logs
tail -30 /var/log/finpilot.log

# Test connection
curl -s http://localhost:8501 | head -c 100
```

---

## Post-Deployment Verification

### 1. Tax Page Features
```bash
# SSH to VPS or test locally
# Navigate to: http://localhost:8501 (or http://VPS_IP:8501)
# 
# Verify:
# ✅ Tax page loads (🧾 in sidebar)
# ✅ Numbers formatted with commas (1,234.56)
# ✅ Exempt Transactions section shows government payments
# ✅ DARS classified as exempt (if exists in data)
```

### 2. Quick Add Transaction Form
```bash
# Navigate to: Quick Add (➕) in sidebar
# 
# Verify:
# ✅ Form loads
# ✅ Category dropdown has all options
# ✅ Real-time WHT calculation visible
# ✅ Can save a test transaction
```

### 3. Database Categorization
```bash
# SSH into VPS
psql $DATABASE_URL -c "
  SELECT 
    counterparty, 
    counterparty_category, 
    COUNT(*) as count
  FROM transactions
  WHERE counterparty_category IS NOT NULL
  GROUP BY counterparty_category
  ORDER BY count DESC;
"

# Should show breakdown like:
# counterparty_category | count
# government            | 15
# transport             | 8
# business              | 22
```

---

## Rollback Procedure

If something breaks after deployment:

### Option 1: Revert to previous commit
```bash
git log --oneline -10  # See recent commits
git revert HEAD  # Revert last commit
git push origin main
# Streamlit Cloud auto-redeploys within 60s

# On VPS:
git pull origin main
pkill -f "streamlit run"
nohup streamlit run dashboard/app.py --server.port 8501 > /var/log/finpilot.log 2>&1 &
```

### Option 2: Reset to specific commit
```bash
git reset --hard COMMIT_HASH
git push --force-with-lease origin main
# WARNING: Only use if you know what you're doing!
```

### Option 3: Database rollback
```bash
# Remove counterparty_category column if migration went wrong:
psql $DATABASE_URL -c "
  ALTER TABLE transactions DROP COLUMN counterparty_category;
"
# Then re-run migration script
```

---

## Environment Setup

### Required `.env` variables
```bash
# Supabase/PostgreSQL
DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Gemini API
GEMINI_API_KEY="AIza..."
GEMINI_VISION_MODEL="gemini-2.5-flash"

# OpenAI API
OPENAI_API_KEY="sk-proj-..."
OPENAI_MODEL="gpt-4o-mini"

# App config
APP_ENV="production"
DEBUG=false
```

### Streamlit secrets (`.streamlit/secrets.toml`)
```toml
DATABASE_URL = "postgresql://user:pass@host:5432/dbname"
GEMINI_API_KEY = "AIza..."
GEMINI_VISION_MODEL = "gemini-2.5-flash"
OPENAI_API_KEY = "sk-proj-..."
```

---

## Monitoring & Logs

### VPS Logs
```bash
# Streamlit logs
tail -100 /var/log/finpilot.log

# Real-time monitoring
watch -n 5 'tail -30 /var/log/finpilot.log'

# Search for errors
grep -i error /var/log/finpilot.log | tail -20
```

### Database Connection Test
```bash
# SSH to VPS
psql $DATABASE_URL -c "SELECT version();"

# Should return PostgreSQL version info
```

### Streamlit Health Check
```bash
# From any machine
curl -s http://VPS_IP:8501 | head -c 200
# Should return HTML content
```

---

## Performance Tips

### Database Optimization
```sql
-- Add indexes for faster tax queries
CREATE INDEX IF NOT EXISTS idx_transactions_counterparty_category 
  ON transactions(counterparty_category);

CREATE INDEX IF NOT EXISTS idx_transactions_type_date 
  ON transactions(transaction_type, transaction_date);

CREATE INDEX IF NOT EXISTS idx_transactions_status_company 
  ON transactions(status, company_id);
```

### Streamlit Optimization
- Cache database queries: `@st.cache_data`
- Limit data loads: Filter by date range
- Lazy load tables: Paginate large datasets
- Use `st.set_page_config(layout="wide")` for wider views

---

## Troubleshooting

### Issue: Tax page shows old numbers
**Solution**: 
1. Hard refresh browser (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)
2. Clear browser cache
3. Check if migration ran: `python3 scripts/migrate_add_counterparty_category.py`

### Issue: DARS transaction not showing as exempt
**Solution**:
1. Run categorization script: `python3 scripts/categorize_existing_transactions.py`
2. Verify keyword in exemption list: Check `WHT_EXEMPT_KEYWORDS` in `dashboard/pages/5_Tax.py`
3. Manually update: `UPDATE transactions SET counterparty_category = 'government' WHERE counterparty ILIKE '%DARS%';`

### Issue: "Database column does not exist" error
**Solution**:
1. Run migration: `python3 scripts/migrate_add_counterparty_category.py`
2. Verify column: `psql $DATABASE_URL -c "\d transactions;"` (should show counterparty_category)

### Issue: Streamlit service won't start
**Solution**:
1. Check Python version: `python3 --version` (need 3.11+)
2. Check dependencies: `pip list | grep streamlit`
3. Check port availability: `lsof -i :8501`
4. Check logs: `tail -50 /var/log/finpilot.log`

---

## Automated Deployment Script (Optional)

Create `deploy.sh` for one-command deployment:

```bash
#!/bin/bash
set -e

echo "🚀 Starting FinPilot deployment..."

# Variables
VPS_IP="88.164.54.132"
PROJECT_DIR="/home/finpilot"

# 1. SSH and pull
echo "📥 Pulling latest code..."
ssh root@$VPS_IP "cd $PROJECT_DIR && git pull origin main"

# 2. Migrations
echo "🔄 Running migrations..."
ssh root@$VPS_IP "cd $PROJECT_DIR && source venv/bin/activate && python3 scripts/migrate_add_counterparty_category.py"
ssh root@$VPS_IP "cd $PROJECT_DIR && source venv/bin/activate && python3 scripts/categorize_existing_transactions.py"

# 3. Restart
echo "🔄 Restarting Streamlit..."
ssh root@$VPS_IP "pkill -f 'streamlit run'; sleep 2; cd $PROJECT_DIR && source venv/bin/activate && nohup streamlit run dashboard/app.py --server.port 8501 > /var/log/finpilot.log 2>&1 &"

# 4. Verify
echo "✅ Waiting for service to start..."
sleep 5
curl -s http://$VPS_IP:8501 > /dev/null && echo "✅ Deployment successful!" || echo "❌ Deployment may have failed - check logs"
```

Usage:
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## Success Checklist

- [x] GitHub repo updated (all commits pushed)
- [x] Streamlit Cloud auto-deploying
- [x] VPS deployment guide documented
- [x] Database migrations tested
- [x] Tax page showing exemptions correctly
- [x] Quick Add form functional
- [x] Number formatting standardized
- [x] CLAUDE.md updated
- [x] All documentation current

---

**Last Updated**: 2026-06-28  
**Status**: Ready for production deployment  
**Contact**: hft4866@gmail.com
