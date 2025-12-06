#!/bin/bash
set -e

# ============================================
# Setup Ngrok as Systemd Service
# ============================================
# This makes ngrok restart automatically if it crashes

echo "Setting up ngrok as a system service..."

# Load environment
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

source .env

if [ -z "$NGROK_DOMAIN" ]; then
    echo "❌ NGROK_DOMAIN not set in .env"
    exit 1
fi

# Create systemd service file
sudo tee /etc/systemd/system/ngrok.service > /dev/null <<EOF
[Unit]
Description=Ngrok Tunnel Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=/usr/bin/ngrok http --domain=$NGROK_DOMAIN 3000
Restart=always
RestartSec=10
StandardOutput=append:/tmp/ngrok.log
StandardError=append:/tmp/ngrok.log

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable ngrok
sudo systemctl restart ngrok

echo "✅ Ngrok service installed and started"
echo ""
echo "Useful commands:"
echo "  Check status:  sudo systemctl status ngrok"
echo "  View logs:     sudo journalctl -u ngrok -f"
echo "  Restart:       sudo systemctl restart ngrok"
echo "  Stop:          sudo systemctl stop ngrok"
echo ""
