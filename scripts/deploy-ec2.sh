#!/bin/bash
# EC2 Deployment Helper Script
# This script helps you deploy the Study Planning app to an EC2 instance

set -e

echo "=========================================="
echo "Study Planning App - EC2 Deployment"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create .env file with your configuration."
    echo "See .env.example for reference."
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker installed! Please log out and log back in, then run this script again."
    exit 0
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo "Error: docker compose is not available!"
    echo "Please install Docker Compose v2"
    exit 1
fi

echo "Step 1: Pulling latest code..."
git pull origin main

echo ""
echo "Step 2: Building Docker images..."
docker compose -f docker-compose.prod.yml build

echo ""
echo "Step 3: Starting services..."
docker compose -f docker-compose.prod.yml up -d

echo ""
echo "Step 4: Waiting for services to start..."
sleep 10

echo ""
echo "Step 5: Pulling Ollama model (this may take 5-10 minutes)..."
docker exec study-planning-ollama ollama pull llama2:latest || echo "Ollama model pull failed, will retry later"

echo ""
echo "Step 6: Checking service status..."
docker compose -f docker-compose.prod.yml ps

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Your app is now running at:"
echo "  Frontend: http://$(curl -s ifconfig.me):3000"
echo "  API:      http://$(curl -s ifconfig.me):8000"
echo "  API Docs: http://$(curl -s ifconfig.me):8000/docs"
echo ""
echo "To view logs:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "To stop services:"
echo "  docker compose -f docker-compose.prod.yml down"
echo ""
echo "IMPORTANT: Update your Auth0 callback URLs to include:"
echo "  http://$(curl -s ifconfig.me):3000"
echo ""
