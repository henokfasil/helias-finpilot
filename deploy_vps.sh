#!/bin/bash
set -e

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║       FinPilot VPS Deployment Script v2.1                      ║"
echo "║       Deploy latest changes with WHT rate fixes                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

PROJECT_DIR="/home/finpilot"

# Step 1: Navigate to project
echo "📂 [1/7] Navigating to project directory..."
cd "$PROJECT_DIR"
echo "✅ In $PROJECT_DIR"
echo ""

# Step 2: Pull latest code
echo "📥 [2/7] Pulling latest code from GitHub..."
git fetch origin
git pull origin main
echo "✅ Code updated"
git log --oneline -2
echo ""

# Step 3: Activate venv
echo "🐍 [3/7] Activating virtual environment..."
source venv/bin/activate
python3 --version
echo "✅ Virtual environment activated"
echo ""

# Step 4: Install dependencies
echo "📦 [4/7] Installing/updating dependencies..."
pip install --upgrade pip > /dev/null
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Step 5: Run migrations
echo "🗄️ [5/7] Running database migrations..."
python3 scripts/migrate_add_counterparty_category.py
echo ""
python3 scripts/categorize_existing_transactions.py
echo "✅ Migrations complete"
echo ""

# Step 6: Restart Streamlit
echo "🔄 [6/7] Restarting Streamlit service..."
pkill -f "streamlit run" || true
sleep 2
nohup streamlit run dashboard/app.py \
  --server.port 8501 \
  --logger.level=error \
  > /var/log/finpilot.log 2>&1 &
sleep 5
echo "✅ Streamlit restarted"
echo ""

# Step 7: Verify
echo "✔️  [7/7] Verifying deployment..."
if curl -s http://localhost:8501 > /dev/null 2>&1; then
    echo "✅ Streamlit is responding on port 8501"
else
    echo "⚠️  Streamlit not responding yet (may still be starting)"
    echo "    Check logs: tail -f /var/log/finpilot.log"
fi
echo ""

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    DEPLOYMENT COMPLETE ✅                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 Dashboard: http://your-vps-ip:8501"
echo "🧾 Tax Page: http://your-vps-ip:8501/Tax"
echo "➕ Quick Add: http://your-vps-ip:8501/Quick_Add"
echo ""
echo "📋 Recent changes deployed:"
echo "   • CRITICAL FIX: WHT rate 2% → 3% across entire system"
echo "   • Refactored Quick Add page for better UX"
echo ""
echo "📝 Logs: tail -f /var/log/finpilot.log"
echo ""
