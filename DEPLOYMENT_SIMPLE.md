# Simple AWS Deployment Guide

This guide provides a streamlined deployment process using a single script.

## Prerequisites

1. **AWS EC2 Instance** (t3.small or larger, Ubuntu 24.04 LTS)
2. **Auth0 Account** (free tier works)
3. **Ngrok Account** (free tier works)

## One-Time Setup

### 1. Launch EC2 Instance

- **AMI**: Ubuntu 24.04 LTS
- **Instance Type**: t3.small (2GB RAM minimum)
- **Storage**: 60GB
- **Security Group**: Open ports 22, 80, 443, 3000, 8000
- **Key Pair**: Download and save your `.pem` file

### 2. Connect to EC2

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

### 3. Install Docker

```bash
# Update system
sudo apt update
sudo apt install -y ca-certificates curl

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### 4. Clone Repository

```bash
git clone https://github.com/yourusername/Conversational-interface-for-study-planning.git
cd Conversational-interface-for-study-planning
```

### 5. Get Ngrok Credentials

1. Sign up at https://dashboard.ngrok.com/signup
2. Get your **authtoken** from https://dashboard.ngrok.com/get-started/your-authtoken
3. Create **two permanent domains** at https://dashboard.ngrok.com/cloud-edge/domains:
   - One for frontend (e.g., `my-app-frontend.ngrok-free.dev`)
   - One for API (e.g., `my-app-api.ngrok-free.dev`)

### 6. Configure Environment

Copy the example file and fill in your values:

```bash
cp .env.example .env
nano .env
```

Update these critical values:

```bash
# Auth0 Configuration
VITE_AUTH0_DOMAIN=your-domain.auth0.com
VITE_AUTH0_CLIENT_ID=your_frontend_client_id
VITE_AUTH0_REDIRECT_URI=https://your-frontend.ngrok-free.dev
AUTH0_CLIENT_ID=your_backend_client_id
AUTH0_CLIENT_SECRET=your_backend_client_secret

# Ngrok Configuration
NGROK_AUTHTOKEN=your_ngrok_authtoken
NGROK_FRONTEND_DOMAIN=your-frontend.ngrok-free.dev
NGROK_API_DOMAIN=your-api.ngrok-free.dev

# API URL
VITE_API_URL=https://your-api.ngrok-free.dev
CORS_ORIGINS=https://your-frontend.ngrok-free.dev,https://your-api.ngrok-free.dev
```

### 7. Configure Auth0

Go to https://manage.auth0.com/dashboard and update your application:

**Allowed Callback URLs**:
```
https://your-frontend.ngrok-free.dev
```

**Allowed Logout URLs**:
```
https://your-frontend.ngrok-free.dev
```

**Allowed Web Origins**:
```
https://your-frontend.ngrok-free.dev
```

**Allowed Origins (CORS)**:
```
https://your-frontend.ngrok-free.dev
```

## Deploy!

Make the script executable and run it:

```bash
chmod +x deploy-aws.sh
./deploy-aws.sh
```

That's it! The script will:
- Pull latest code
- Build and start Docker containers
- Start ngrok tunnels
- Display access URLs

## Access Your App

After deployment completes, visit:
- **Frontend**: https://your-frontend.ngrok-free.dev
- **API**: https://your-api.ngrok-free.dev/docs

## Useful Commands

```bash
# Redeploy (after code changes or restart)
./deploy-aws.sh

# View logs
sudo docker compose -f docker-compose.prod.yml logs -f

# View specific service logs
sudo docker compose -f docker-compose.prod.yml logs -f fastapi-app

# Stop everything
sudo docker compose -f docker-compose.prod.yml down
pkill ngrok

# Check container status
sudo docker ps

# Check ngrok status
curl http://localhost:4040/api/tunnels | python3 -m json.tool
```

## Troubleshooting

### Containers not starting
```bash
# Check logs
sudo docker compose -f docker-compose.prod.yml logs

# Restart specific service
sudo docker compose -f docker-compose.prod.yml restart fastapi-app
```

### Ngrok tunnels not working
```bash
# Check ngrok logs
cat /tmp/ngrok-frontend.log
cat /tmp/ngrok-api.log

# Restart tunnels
pkill ngrok
./deploy-aws.sh
```

### Auth0 login not working
- Verify callback URLs in Auth0 dashboard match ngrok domains exactly
- Check browser console for errors (F12)
- Ensure .env has correct VITE_AUTH0_REDIRECT_URI

### Out of memory
- Upgrade to t3.medium (4GB RAM) for better stability
- Check memory usage: `free -h`

## Production Considerations

For long-term production use:

1. **Buy a domain** ($10/year) and set up proper SSL with Let's Encrypt
2. **Upgrade instance** to t3.medium for better performance
3. **Set up ngrok as systemd service** so tunnels restart automatically
4. **Enable backups** for MongoDB data
5. **Set up monitoring** and alerts

## Cost Estimate

- **EC2 t3.small**: ~$15/month
- **60GB EBS storage**: ~$6/month
- **Ngrok free tier**: $0 (limitations: 1 user, 40 connections/min)
- **Total**: ~$21/month

For production: Upgrade to EC2 t3.medium (~$30/month) for stability.
