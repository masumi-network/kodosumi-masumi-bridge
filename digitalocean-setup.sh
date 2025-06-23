#!/bin/bash

# DigitalOcean Server Setup Script for Masumi Kodosuni Connector
set -e

echo "🌊 DigitalOcean Server Setup for Masumi Kodosuni Connector"
echo "============================================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root: sudo ./digitalocean-setup.sh"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install essential packages
echo "🔧 Installing essential packages..."
apt install -y curl wget git nano htop ufw fail2ban

# Install Docker
echo "🐳 Installing Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
rm get-docker.sh

# Install Docker Compose
echo "🔧 Installing Docker Compose..."
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Nginx
echo "🌐 Installing Nginx..."
apt install -y nginx

# Install Certbot for SSL
echo "🔒 Installing Certbot..."
apt install -y certbot python3-certbot-nginx

# Setup firewall
echo "🛡️ Configuring firewall..."
ufw --force enable
ufw allow ssh
ufw allow 80
ufw allow 443
ufw allow 8000  # For direct access during setup

# Create application directory
echo "📁 Creating application directory..."
mkdir -p /opt/masumi-connector
cd /opt/masumi-connector

# Download application files (if GitHub repo is available)
read -p "📥 Enter your GitHub repository URL (or press Enter to skip): " REPO_URL
if [ ! -z "$REPO_URL" ]; then
    echo "⬇️ Cloning repository..."
    git clone "$REPO_URL" .
else
    echo "ℹ️ Skipped repository clone. You'll need to upload files manually."
fi

# Create .env from template if it doesn't exist
if [ -f ".env.docker" ] && [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.docker .env
    echo "⚠️ Please edit /opt/masumi-connector/.env with your configuration"
fi

# Create systemd service for easier management
echo "⚙️ Creating systemd service..."
cat > /etc/systemd/system/masumi-connector.service << EOF
[Unit]
Description=Masumi Kodosuni Connector
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/masumi-connector
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable masumi-connector

# Create backup script
echo "💾 Creating backup script..."
cat > /opt/masumi-connector/backup.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/opt/masumi-connector/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

cd /opt/masumi-connector
docker-compose exec -T postgres pg_dump -U masumi_user masumi_connector | gzip > "$BACKUP_DIR/db_backup_${DATE}.sql.gz"

find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: db_backup_${DATE}.sql.gz"
EOF

chmod +x /opt/masumi-connector/backup.sh

# Setup log rotation
echo "📋 Setting up log rotation..."
cat > /etc/logrotate.d/masumi-connector << EOF
/opt/masumi-connector/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        /usr/local/bin/docker-compose -f /opt/masumi-connector/docker-compose.yml restart masumi-connector > /dev/null 2>&1 || true
    endscript
}
EOF

# Create basic Nginx configuration
echo "🌐 Creating Nginx configuration..."
read -p "🌍 Enter your domain name (or press Enter for IP-only setup): " DOMAIN_NAME

if [ ! -z "$DOMAIN_NAME" ]; then
    SERVER_NAME="$DOMAIN_NAME www.$DOMAIN_NAME"
else
    SERVER_NAME="_"
fi

cat > /etc/nginx/sites-available/masumi-connector << EOF
server {
    listen 80;
    server_name $SERVER_NAME;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
EOF

# Enable Nginx site
ln -sf /etc/nginx/sites-available/masumi-connector /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and restart Nginx
nginx -t
systemctl restart nginx
systemctl enable nginx

# Create management script
echo "🔧 Creating management script..."
cat > /opt/masumi-connector/manage.sh << 'EOF'
#!/bin/bash

case "$1" in
    start)
        echo "🚀 Starting Masumi Connector..."
        cd /opt/masumi-connector
        docker-compose up -d
        ;;
    stop)
        echo "🛑 Stopping Masumi Connector..."
        cd /opt/masumi-connector
        docker-compose down
        ;;
    restart)
        echo "🔄 Restarting Masumi Connector..."
        cd /opt/masumi-connector
        docker-compose restart
        ;;
    logs)
        echo "📋 Showing logs..."
        cd /opt/masumi-connector
        docker-compose logs -f masumi-connector
        ;;
    status)
        echo "📊 Service status..."
        cd /opt/masumi-connector
        docker-compose ps
        ;;
    backup)
        echo "💾 Creating backup..."
        /opt/masumi-connector/backup.sh
        ;;
    update)
        echo "⬆️ Updating application..."
        cd /opt/masumi-connector
        git pull
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|logs|status|backup|update}"
        exit 1
        ;;
esac
EOF

chmod +x /opt/masumi-connector/manage.sh

# Create symbolic link for easy access
ln -sf /opt/masumi-connector/manage.sh /usr/local/bin/masumi-connector

echo ""
echo "✅ Server setup completed!"
echo ""
echo "📋 Next Steps:"
echo "1. Edit configuration: nano /opt/masumi-connector/.env"
echo "2. Deploy application: cd /opt/masumi-connector && ./deploy-docker.sh"
if [ ! -z "$DOMAIN_NAME" ]; then
echo "3. Setup SSL: certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME"
fi
echo ""
echo "🔧 Management Commands:"
echo "  masumi-connector start   - Start services"
echo "  masumi-connector stop    - Stop services"
echo "  masumi-connector logs    - View logs"
echo "  masumi-connector status  - Check status"
echo "  masumi-connector backup  - Create backup"
echo "  masumi-connector update  - Update application"
echo ""
echo "🌐 Access URLs:"
echo "  Application: http://$(curl -s ifconfig.me):8000"
if [ ! -z "$DOMAIN_NAME" ]; then
echo "  Domain: http://$DOMAIN_NAME"
fi
echo "  Health: http://$(curl -s ifconfig.me):8000/health"
echo "  Admin: http://$(curl -s ifconfig.me):8000/admin"
echo ""
echo "📚 Full documentation: /opt/masumi-connector/DIGITALOCEAN_SETUP.md"