# DigitalOcean Deployment Guide

Complete step-by-step guide to deploy Masumi Kodosuni Connector on DigitalOcean.

## Prerequisites

- DigitalOcean account
- Domain name (optional but recommended)
- GitHub account for code deployment

## Step 1: Create DigitalOcean Droplet

### 1.1 Create Droplet
1. Log into [DigitalOcean Console](https://cloud.digitalocean.com)
2. Click **"Create"** → **"Droplets"**
3. **Choose Image**: Ubuntu 22.04 LTS
4. **Choose Size**: 
   - **Minimum**: Basic plan, Regular Intel, 2 GB RAM / 1 vCPU ($12/month)
   - **Recommended**: Basic plan, Regular Intel, 4 GB RAM / 2 vCPUs ($24/month)
5. **Choose Region**: Select closest to your users
6. **Authentication**: 
   - Add SSH Key (recommended) or Password
7. **Hostname**: `masumi-connector`
8. Click **"Create Droplet"**

### 1.2 Connect to Droplet
```bash
# Replace YOUR_DROPLET_IP with actual IP
ssh root@YOUR_DROPLET_IP
```

## Step 2: Server Setup

### 2.1 Update System
```bash
apt update && apt upgrade -y
```

### 2.2 Install Docker
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### 2.3 Install Git and Other Tools
```bash
apt install -y git curl nano htop ufw
```

### 2.4 Setup Firewall
```bash
# Enable firewall
ufw enable

# Allow SSH, HTTP, HTTPS
ufw allow ssh
ufw allow 80
ufw allow 443

# Allow application port (optional, for direct access)
ufw allow 8000

# Check status
ufw status
```

## Step 3: Deploy Application

### 3.1 Clone Repository
```bash
# Create application directory
mkdir -p /opt/masumi-connector
cd /opt/masumi-connector

# Clone your repository
git clone https://github.com/YOUR_USERNAME/masumi_kodosuni_connector.git .

# Or upload files manually if no git repo
```

### 3.2 Configure Environment
```bash
# Copy environment template
cp .env.docker .env

# Edit configuration
nano .env
```

**Required Configuration:**
```bash
# Strong password for PostgreSQL
POSTGRES_PASSWORD=your_very_secure_password_here

# Kodosumi Configuration
KODOSUMI_BASE_URL=http://209.38.221.56:3370
KODOSUMI_USERNAME=admin
KODOSUMI_PASSWORD=admin

# Masumi Payment Configuration
PAYMENT_SERVICE_URL=https://payment.masumi.network/api/v1
PAYMENT_API_KEY=your_actual_masumi_api_key
NETWORK=preprod  # Change to 'mainnet' for production
SELLER_VKEY=your_actual_seller_verification_key
PAYMENT_AMOUNT=10000000
PAYMENT_UNIT=lovelace
MASUMI_TEST_MODE=false  # Set to false for production

# Agent Configuration (enable the agents you want)
AGENT_IDENTIFIER_-_127.0.0.1_8001_instagram_-_=your-instagram-agent-id
AGENT_IDENTIFIER_-_127.0.0.1_8001_linkedin_insights_-_=your-linkedin-agent-id
AGENT_IDENTIFIER_-_127.0.0.1_8001_newsagent_-_=your-news-agent-id

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Polling Configuration
POLLING_INTERVAL_SECONDS=10
```

### 3.3 Deploy with Docker
```bash
# Make deployment script executable
chmod +x deploy-docker.sh

# Deploy
./deploy-docker.sh
```

### 3.4 Verify Deployment
```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs -f masumi-connector

# Test health endpoint
curl http://localhost:8000/health
```

## Step 4: Setup Reverse Proxy (Nginx)

### 4.1 Install Nginx
```bash
apt install -y nginx
```

### 4.2 Configure Nginx
```bash
# Create site configuration
nano /etc/nginx/sites-available/masumi-connector
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN.com www.YOUR_DOMAIN.com;  # Replace with your domain
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
```

### 4.3 Enable Site
```bash
# Enable site
ln -s /etc/nginx/sites-available/masumi-connector /etc/nginx/sites-enabled/

# Remove default site
rm /etc/nginx/sites-enabled/default

# Test configuration
nginx -t

# Restart Nginx
systemctl restart nginx
systemctl enable nginx
```

## Step 5: Setup SSL with Let's Encrypt

### 5.1 Install Certbot
```bash
apt install -y certbot python3-certbot-nginx
```

### 5.2 Obtain SSL Certificate
```bash
# Replace with your domain
certbot --nginx -d YOUR_DOMAIN.com -d www.YOUR_DOMAIN.com
```

### 5.3 Setup Auto-Renewal
```bash
# Test renewal
certbot renew --dry-run

# Auto-renewal is automatically configured
systemctl status certbot.timer
```

## Step 6: Setup Monitoring and Backups

### 6.1 Create Backup Script
```bash
nano /opt/masumi-connector/backup.sh
```

**Backup Script:**
```bash
#!/bin/bash
set -e

BACKUP_DIR="/opt/masumi-connector/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup database
cd /opt/masumi-connector
docker-compose exec -T postgres pg_dump -U masumi_user masumi_connector | gzip > "$BACKUP_DIR/db_backup_${DATE}.sql.gz"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_backup_${DATE}.sql.gz"
```

```bash
# Make executable
chmod +x /opt/masumi-connector/backup.sh

# Test backup
./backup.sh
```

### 6.2 Setup Cron Jobs
```bash
crontab -e
```

**Add to crontab:**
```bash
# Daily database backup at 2 AM
0 2 * * * /opt/masumi-connector/backup.sh

# Check service health every 5 minutes
*/5 * * * * curl -f http://localhost:8000/health || systemctl restart masumi-connector
```

### 6.3 Setup Log Rotation
```bash
nano /etc/logrotate.d/masumi-connector
```

**Log Rotation Config:**
```
/opt/masumi-connector/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        docker-compose -f /opt/masumi-connector/docker-compose.yml restart masumi-connector
    endscript
}
```

## Step 7: Configure Domain (Optional)

### 7.1 DNS Configuration
In your domain registrar, create these DNS records:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | @ | YOUR_DROPLET_IP | 3600 |
| A | www | YOUR_DROPLET_IP | 3600 |

### 7.2 Wait for DNS Propagation
```bash
# Check DNS propagation
nslookup YOUR_DOMAIN.com
dig YOUR_DOMAIN.com
```

## Step 8: Final Verification

### 8.1 Test All Endpoints
```bash
# Health check
curl https://YOUR_DOMAIN.com/health

# Admin panel
curl https://YOUR_DOMAIN.com/admin

# API documentation
curl https://YOUR_DOMAIN.com/docs
```

### 8.2 Test Job Execution
1. Visit `https://YOUR_DOMAIN.com/docs`
2. Try the `/mip003/{flow_key}/start_job` endpoint
3. Monitor logs: `docker-compose logs -f masumi-connector`

## Management Commands

### Daily Operations
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f masumi-connector

# Restart services
docker-compose restart masumi-connector

# Update application
cd /opt/masumi-connector
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Monitoring
```bash
# System resources
htop
df -h
docker stats

# Application logs
tail -f /var/log/nginx/access.log
docker-compose logs --tail=100 masumi-connector

# Database status
docker-compose exec postgres pg_isready -U masumi_user
```

### Troubleshooting
```bash
# Check firewall
ufw status

# Check Nginx
nginx -t
systemctl status nginx

# Check Docker services
docker-compose ps
docker-compose logs masumi-connector

# Check disk space
df -h

# Check memory usage
free -h
```

## Security Best Practices

1. **Change default passwords**
2. **Keep system updated**: `apt update && apt upgrade`
3. **Monitor logs regularly**
4. **Use strong SSL configuration**
5. **Regular backups**
6. **Monitor resource usage**
7. **Setup log monitoring/alerting**

## Cost Estimation

- **Droplet**: $12-24/month (2-4GB RAM)
- **Domain**: $10-15/year (optional)
- **Backups**: ~$5/month for 100GB spaces
- **Total**: ~$15-30/month

Your Masumi Kodosuni Connector is now deployed and ready for production use on DigitalOcean! 🚀