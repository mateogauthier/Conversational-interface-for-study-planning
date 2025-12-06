#!/bin/bash
# SSL Setup Script for EC2 Deployment
# Sets up Nginx reverse proxy with Let's Encrypt SSL

set -e

echo "=========================================="
echo "SSL Setup with Let's Encrypt"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please do not run this script as root (without sudo)."
    exit 1
fi

# Get domain names from user
read -p "Enter your frontend domain (e.g., app.yourdomain.com): " FRONTEND_DOMAIN
read -p "Enter your API domain (e.g., api.yourdomain.com): " API_DOMAIN
read -p "Enter your email for Let's Encrypt notifications: " EMAIL

echo ""
echo "Configuration:"
echo "  Frontend: $FRONTEND_DOMAIN"
echo "  API: $API_DOMAIN"
echo "  Email: $EMAIL"
echo ""
read -p "Is this correct? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# Install Nginx
echo ""
echo "Installing Nginx..."
sudo apt update
sudo apt install -y nginx

# Install Certbot
echo ""
echo "Installing Certbot..."
sudo apt install -y certbot python3-certbot-nginx

# Create Nginx configuration
echo ""
echo "Creating Nginx configuration..."
sudo tee /etc/nginx/sites-available/study-planning > /dev/null <<EOF
# Frontend
server {
    listen 80;
    server_name $FRONTEND_DOMAIN;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}

# API
server {
    listen 80;
    server_name $API_DOMAIN;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable site
echo ""
echo "Enabling site..."
sudo ln -sf /etc/nginx/sites-available/study-planning /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificates
echo ""
echo "Obtaining SSL certificates from Let's Encrypt..."
sudo certbot --nginx -d $FRONTEND_DOMAIN -d $API_DOMAIN --non-interactive --agree-tos --email $EMAIL

# Test auto-renewal
echo ""
echo "Testing certificate auto-renewal..."
sudo certbot renew --dry-run

echo ""
echo "=========================================="
echo "SSL Setup Complete!"
echo "=========================================="
echo ""
echo "Your app is now accessible via HTTPS:"
echo "  Frontend: https://$FRONTEND_DOMAIN"
echo "  API:      https://$API_DOMAIN"
echo ""
echo "IMPORTANT: Update your .env file with these URLs:"
echo "  VITE_AUTH0_REDIRECT_URI=https://$FRONTEND_DOMAIN"
echo "  CORS_ORIGINS=https://$FRONTEND_DOMAIN,https://$API_DOMAIN"
echo ""
echo "Then restart your containers:"
echo "  cd /path/to/repo"
echo "  docker compose -f docker-compose.prod.yml down"
echo "  docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "Also update Auth0 callback URLs to include:"
echo "  https://$FRONTEND_DOMAIN"
echo ""
