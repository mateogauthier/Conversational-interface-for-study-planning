#!/bin/bash
set -e

# ============================================
# AWS EC2 Deployment Script
# ============================================
# This script automates the entire deployment process
# Run with: ./deploy-aws.sh

echo "=========================================="
echo "Study Planning App - AWS Deployment"
echo "=========================================="
echo ""

# Check if running on EC2
if [ ! -f /sys/hypervisor/uuid ] && [ ! -d /sys/class/dmi/id ]; then
    echo "⚠️  This script should be run on the EC2 instance"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file with your configuration"
    exit 1
fi

# Load environment variables
source .env

# Check if required variables are set
if [ -z "$VITE_AUTH0_DOMAIN" ] || [ -z "$VITE_AUTH0_CLIENT_ID" ]; then
    echo "❌ Missing Auth0 configuration in .env"
    exit 1
fi

echo "📦 Step 1: Pulling latest changes from git..."
git pull origin main || echo "⚠️  No git changes to pull"

echo ""
echo "🛑 Step 2: Stopping existing containers..."
sudo docker compose -f docker-compose.prod.yml down

echo ""
echo "🏗️  Step 3: Building and starting containers..."
sudo docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "⏳ Step 4: Waiting for services to become healthy..."
sleep 10

# Check container status
echo ""
echo "📊 Container Status:"
sudo docker ps --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "🌐 Step 5: Starting ngrok tunnels..."

# Kill any existing ngrok processes
pkill ngrok || true
sleep 2

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "Installing ngrok..."
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
    sudo apt update
    sudo apt install ngrok -y
fi

# Check if NGROK_AUTHTOKEN is set
if [ -z "$NGROK_AUTHTOKEN" ]; then
    echo "❌ NGROK_AUTHTOKEN not set in .env"
    echo "Please add: NGROK_AUTHTOKEN=your_token_here"
    exit 1
fi

# Configure ngrok
ngrok config add-authtoken $NGROK_AUTHTOKEN

# Check if ngrok domains are set
if [ -z "$NGROK_FRONTEND_DOMAIN" ] || [ -z "$NGROK_API_DOMAIN" ]; then
    echo "❌ Ngrok domains not configured in .env"
    echo "Please add:"
    echo "  NGROK_FRONTEND_DOMAIN=your-frontend.ngrok-free.dev"
    echo "  NGROK_API_DOMAIN=your-api.ngrok-free.dev"
    exit 1
fi

# Start ngrok tunnels in background
echo "Starting frontend tunnel: https://$NGROK_FRONTEND_DOMAIN"
nohup ngrok http --domain=$NGROK_FRONTEND_DOMAIN 3000 > /tmp/ngrok-frontend.log 2>&1 &
sleep 2

echo "Starting API tunnel: https://$NGROK_API_DOMAIN"
nohup ngrok http --domain=$NGROK_API_DOMAIN 8000 > /tmp/ngrok-api.log 2>&1 &
sleep 2

# Check if tunnels are running
if pgrep -f "ngrok.*3000" > /dev/null && pgrep -f "ngrok.*8000" > /dev/null; then
    echo "✅ Ngrok tunnels started successfully"
else
    echo "❌ Failed to start ngrok tunnels"
    echo "Frontend log:"
    cat /tmp/ngrok-frontend.log
    echo "API log:"
    cat /tmp/ngrok-api.log
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Deployment Complete!"
echo "=========================================="
echo ""
echo "🌐 Access your application at:"
echo "   Frontend: https://$NGROK_FRONTEND_DOMAIN"
echo "   API:      https://$NGROK_API_DOMAIN"
echo ""
echo "📋 Next Steps:"
echo "1. Configure Auth0 callback URLs:"
echo "   - Go to: https://manage.auth0.com/dashboard"
echo "   - Add to Allowed Callback URLs: https://$NGROK_FRONTEND_DOMAIN"
echo "   - Add to Allowed Logout URLs: https://$NGROK_FRONTEND_DOMAIN"
echo "   - Add to Allowed Web Origins: https://$NGROK_FRONTEND_DOMAIN"
echo "   - Add to Allowed Origins (CORS): https://$NGROK_FRONTEND_DOMAIN"
echo ""
echo "2. Update your .env file with ngrok URLs:"
echo "   VITE_AUTH0_REDIRECT_URI=https://$NGROK_FRONTEND_DOMAIN"
echo "   VITE_API_URL=https://$NGROK_API_DOMAIN"
echo "   CORS_ORIGINS=https://$NGROK_FRONTEND_DOMAIN,https://$NGROK_API_DOMAIN"
echo ""
echo "3. Rebuild frontend with new URLs:"
echo "   sudo docker compose -f docker-compose.prod.yml up -d --build frontend"
echo ""
echo "📊 Useful Commands:"
echo "   View logs:        sudo docker compose -f docker-compose.prod.yml logs -f"
echo "   Restart:          ./deploy-aws.sh"
echo "   Stop:             sudo docker compose -f docker-compose.prod.yml down"
echo "   Ngrok status:     curl http://localhost:4040/api/tunnels"
echo ""
