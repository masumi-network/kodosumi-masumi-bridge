# Quick Deployment Guide

## 🚀 One-Command DigitalOcean Deployment

### Step 1: Create DigitalOcean Droplet
1. Go to [DigitalOcean](https://cloud.digitalocean.com)
2. Create Ubuntu 22.04 droplet (minimum 2GB RAM)
3. Note your droplet IP address

### Step 2: Run Setup Script
```bash
# Connect to your droplet
ssh root@YOUR_DROPLET_IP

# Download and run setup script
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/masumi_kodosuni_connector/main/digitalocean-setup.sh | bash
```

### Step 3: Configure and Deploy
```bash
# Edit configuration
nano /opt/masumi-connector/.env

# Deploy application
cd /opt/masumi-connector
./deploy-docker.sh
```

### Step 4: Setup SSL (Optional)
```bash
# If you have a domain
certbot --nginx -d yourdomain.com
```

## ✅ That's it! 

Your Masumi Kodosuni Connector is now running at:
- **Direct Access**: `http://YOUR_DROPLET_IP:8000`
- **Through Nginx**: `http://YOUR_DROPLET_IP` or `https://yourdomain.com`

## 🔧 Management Commands
```bash
masumi-connector start    # Start services
masumi-connector stop     # Stop services  
masumi-connector logs     # View logs
masumi-connector status   # Check status
masumi-connector backup   # Create backup
masumi-connector update   # Update application
```

## 📚 Documentation
- **Full Guide**: `DIGITALOCEAN_SETUP.md`
- **Docker Details**: `DEPLOYMENT.md`
- **Application Docs**: `README.md`