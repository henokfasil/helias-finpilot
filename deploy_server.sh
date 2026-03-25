#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Helias FinPilot — Server Deployment Script
# Server: 72.60.133.179
# Run this ON the server after SSH-ing in.
# ─────────────────────────────────────────────────────────────────────────────

set -e

echo "======================================"
echo " Helias FinPilot — Server Setup"
echo "======================================"

# 1. System packages
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# 2. Project directory
mkdir -p /opt/finpilot
cd /opt/finpilot

# 3. Copy files (run from your Mac first):
#    scp -r . root@72.60.133.179:/opt/finpilot/
echo "→ Files should be copied already (see instructions below)"

# 4. Virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q

# 5. Create uploads directory
mkdir -p uploads

# 6. Seed the database
python scripts/seed_data.py

# 7. Create systemd services

# ── Bot service ──────────────────────────────────────────────────────────────
cat > /etc/systemd/system/finpilot-bot.service << 'EOF'
[Unit]
Description=Helias FinPilot Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=/opt/finpilot
ExecStart=/opt/finpilot/venv/bin/python3 -m app.main
Restart=always
RestartSec=5
StandardOutput=append:/var/log/finpilot-bot.log
StandardError=append:/var/log/finpilot-bot.log

[Install]
WantedBy=multi-user.target
EOF

# ── Dashboard service ────────────────────────────────────────────────────────
cat > /etc/systemd/system/finpilot-dashboard.service << 'EOF'
[Unit]
Description=Helias FinPilot Streamlit Dashboard
After=network.target

[Service]
User=root
WorkingDirectory=/opt/finpilot
ExecStart=/opt/finpilot/venv/bin/streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=5
StandardOutput=append:/var/log/finpilot-dashboard.log
StandardError=append:/var/log/finpilot-dashboard.log

[Install]
WantedBy=multi-user.target
EOF

# 8. Enable and start both services
systemctl daemon-reload
systemctl enable finpilot-bot finpilot-dashboard
systemctl start  finpilot-bot finpilot-dashboard

echo ""
echo "✅ Services started."
echo "   Bot status:       systemctl status finpilot-bot"
echo "   Dashboard status: systemctl status finpilot-dashboard"
echo ""
echo "======================================"
echo " Now configure Nginx (see below)"
echo "======================================"
