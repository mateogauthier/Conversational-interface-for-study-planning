#!/bin/bash
set -e

# ============================================
# Simple AWS EC2 Deployment Script
# ============================================
# This script deploys with a SINGLE ngrok tunnel
# (frontend proxies API requests via nginx)

echo "=========================================="
echo "Study Planning App - Simple Deployment"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
fi

# Load environment variables
source .env

echo "🛑 Step 1: Stopping existing containers and ngrok..."
sudo docker compose -f docker-compose.prod.yml down || true
pkill ngrok || true
sleep 2

echo ""
echo "🏗️  Step 2: Building and starting containers..."
sudo docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "⏳ Step 3: Waiting for services to start..."
sleep 15

# Check container status
echo ""
echo "📊 Container Status:"
sudo docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "study-planning|NAMES"

echo ""
echo "🌐 Step 4: Starting ngrok tunnel..."

# Install ngrok if needed
if ! command -v ngrok &> /dev/null; then
    echo "Installing ngrok..."
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt update && sudo apt install ngrok -y
fi

# Configure ngrok
if [ -z "$NGROK_AUTHTOKEN" ]; then
    echo "❌ NGROK_AUTHTOKEN not set in .env"
    exit 1
fi

ngrok config add-authtoken $NGROK_AUTHTOKEN

if [ -z "$NGROK_DOMAIN" ]; then
    echo "❌ NGROK_DOMAIN not set in .env"
    exit 1
fi

# Start ngrok tunnel in background
echo "Starting ngrok: https://$NGROK_DOMAIN → port 3000"
nohup ngrok http --domain=$NGROK_DOMAIN 3000 > /tmp/ngrok.log 2>&1 &
sleep 3

# Check if tunnel is running
if pgrep -f "ngrok.*3000" > /dev/null; then
    echo "✅ Ngrok tunnel started successfully"
else
    echo "❌ Failed to start ngrok tunnel"
    cat /tmp/ngrok.log
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "🌐 Access your application:"
echo "   https://$NGROK_DOMAIN"
echo ""
echo "📋 IMPORTANT - Configure Auth0:"
echo "   Go to: https://manage.auth0.com/dashboard"
echo "   Update your application with:"
echo "   - Allowed Callback URLs: https://$NGROK_DOMAIN"
echo "   - Allowed Logout URLs: https://$NGROK_DOMAIN"
echo "   - Allowed Web Origins: https://$NGROK_DOMAIN"
echo "   - Allowed Origins (CORS): https://$NGROK_DOMAIN"
echo ""
echo "📊 Useful Commands:"
echo "   View logs:     sudo docker compose -f docker-compose.prod.yml logs -f"
echo "   Redeploy:      ./deploy-simple.sh"
echo "   Stop all:      sudo docker compose -f docker-compose.prod.yml down && pkill ngrok"
echo "   Ngrok status:  curl -s http://localhost:4040/api/tunnels | python3 -m json.tool"
echo ""
