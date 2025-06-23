# Docker Deployment Guide

This guide covers deploying the Masumi Kodosuni Connector using Docker with PostgreSQL.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 2GB RAM
- 10GB disk space

## Quick Start

### 1. Configure Environment

```bash
# Copy the Docker environment template
cp .env.docker .env

# Edit the configuration
nano .env
```

**Required Configuration:**
- `POSTGRES_PASSWORD`: Strong password for PostgreSQL
- `PAYMENT_API_KEY`: Your Masumi API key
- `SELLER_VKEY`: Your seller verification key
- `AGENT_IDENTIFIER_*`: Agent identifiers for enabled flows
- `MASUMI_TEST_MODE`: Set to `false` for production

### 2. Deploy

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f masumi-connector
```

### 3. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Check available flows
curl http://localhost:8000/admin

# API documentation
open http://localhost:8000/docs
```

## Service Management

### Start/Stop Services
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart a specific service
docker-compose restart masumi-connector
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f masumi-connector
docker-compose logs -f postgres
```

### Database Management
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U masumi_user -d masumi_connector

# Backup database
docker-compose exec postgres pg_dump -U masumi_user masumi_connector > backup.sql

# Restore database
docker-compose exec -T postgres psql -U masumi_user masumi_connector < backup.sql
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL password | `masumi_secure_password_123` |
| `KODOSUMI_BASE_URL` | Kodosumi server URL | Required |
| `PAYMENT_API_KEY` | Masumi API key | Required |
| `NETWORK` | Blockchain network | `preprod` |
| `MASUMI_TEST_MODE` | Enable test mode | `true` |
| `POLLING_INTERVAL_SECONDS` | Job polling interval | `10` |

### Agent Configuration

Enable agents by setting their identifiers:
```bash
AGENT_IDENTIFIER_-_127.0.0.1_8001_instagram_-_=your-instagram-agent-id
AGENT_IDENTIFIER_-_127.0.0.1_8001_linkedin_insights_-_=your-linkedin-agent-id
```

## Production Deployment

### 1. Security Hardening

```bash
# Generate strong passwords
openssl rand -base64 32  # For POSTGRES_PASSWORD

# Update .env with production values
MASUMI_TEST_MODE=false
NETWORK=mainnet
POSTGRES_PASSWORD=your_secure_password
```

### 2. Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/masumi-connector
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. SSL with Certbot

```bash
sudo certbot --nginx -d your-domain.com
```

### 4. Monitoring

```bash
# Health check endpoint
curl https://your-domain.com/health

# Service metrics
docker stats

# Disk usage
docker system df
```

## Troubleshooting

### Common Issues

**Service won't start:**
```bash
# Check logs
docker-compose logs masumi-connector

# Check database connectivity
docker-compose exec masumi-connector python -c "
import asyncio
from src.masumi_kodosuni_connector.database.database import get_database_engine
asyncio.run(get_database_engine().connect())
"
```

**Database connection errors:**
```bash
# Check PostgreSQL status
docker-compose logs postgres

# Test database connection
docker-compose exec postgres pg_isready -U masumi_user
```

**Port conflicts:**
```bash
# Change ports in docker-compose.yml
ports:
  - "8001:8000"  # App
  - "5433:5432"  # PostgreSQL
```

### Scaling

For high-traffic deployments:

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  masumi-connector:
    deploy:
      replicas: 3
    environment:
      - WORKERS=4
```

## Backup Strategy

### Automated Backups

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U masumi_user masumi_connector | gzip > "backup_${DATE}.sql.gz"
find . -name "backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# Add to crontab for daily backups
echo "0 2 * * * /path/to/backup.sh" | crontab -
```

## Updates

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Check migration logs
docker-compose logs masumi-connector | grep -i migration
```