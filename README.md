# Masumi Kodosuni Connector

A lightweight Docker-based connector that integrates Kodosumi AI agents with Masumi payment processing. Features a modern web-based admin interface for managing agents and monitoring jobs.

## Features

- 🚀 **Docker Compose Setup** - One-command deployment
- 🎛️ **Modern Admin Interface** - Clean table-based UI for agent management
- 🔐 **API Security** - Optional API key protection
- ⚡ **Real-time Monitoring** - Live job status and timeout tracking
- 🔄 **Agent Management** - Enable/disable agents via web interface
- 📊 **Job Timeout System** - Automatic timeout handling with visual warnings
- 🗄️ **PostgreSQL Database** - Persistent data storage

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- `.env` file configured (see Configuration section)

### 2. Setup

```bash
# Clone the repository
git clone <repository-url>
cd masumi_kodosuni_connector

# Run the startup script (recommended)
./start.sh

# OR manually:
# cp .env.example .env
# nano .env  # Configure your settings
# docker compose up -d
```

### 3. Access

- **Admin Interface**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Configuration

### Required Environment Variables

Edit your `.env` file with the following required settings:

```env
# Database (automatically configured for Docker)
DATABASE_URL=postgresql+asyncpg://masumi_user:your_password@postgres:5432/masumi_connector

# Kodosumi API
KODOSUMI_BASE_URL=http://your-kodosumi-instance.com
KODOSUMI_USERNAME=your_username
KODOSUMI_PASSWORD=your_password

# Masumi Payment Service
PAYMENT_SERVICE_URL=https://payment.masumi.network/api/v1
PAYMENT_API_KEY=your_payment_api_key
NETWORK=preprod  # or mainnet
SELLER_VKEY=your_seller_verification_key

# Security (optional - enables admin interface protection)
# API_KEY=your-secure-api-key-here

# Agent Configuration
AGENT_IDENTIFIER_<flow_key>=<agent_identifier>
```

### Agent Configuration

To enable agents, add their identifiers to your `.env` file:

```env
# Example agent configurations
AGENT_IDENTIFIER_-_localhost_8001_seo-agent_-_=seo-analysis-masumi-agent
AGENT_IDENTIFIER_-_localhost_8001_news-agent_-_=news-research-masumi-agent
```

## Usage

### Starting the Services

```bash
# Start in background
docker compose up -d

# View logs
docker compose logs -f masumi-connector

# Check status
docker compose ps
```

### Managing Agents

1. Open the admin interface at http://localhost:8000/admin
2. Use the checkboxes to enable/disable agents
3. View real-time job status and timeouts
4. Monitor system health and statistics

### API Security

To secure the admin interface:

1. Uncomment and set `API_KEY` in your `.env` file
2. Restart the services: `docker compose restart`
3. Access admin endpoints with header: `Authorization: Bearer your-api-key`

### Stopping the Services

```bash
# Stop services
docker compose down

# Stop and remove all data
docker compose down --volumes
```

## Docker Commands

```bash
# View logs
docker compose logs -f masumi-connector
docker compose logs -f postgres

# Restart a service
docker compose restart masumi-connector

# Rebuild after code changes
docker compose down
docker compose build --no-cache
docker compose up -d

# Access container shell
docker compose exec masumi-connector bash

# Database operations
docker compose exec postgres psql -U masumi_user -d masumi_connector
```

## Project Structure

```
masumi_kodosuni_connector/
├── src/masumi_kodosuni_connector/    # Main application code
│   ├── api/                          # FastAPI routes and schemas
│   ├── config/                       # Settings and logging
│   ├── database/                     # Database connection and repositories
│   ├── models/                       # SQLAlchemy models
│   ├── services/                     # Business logic
│   ├── static/                       # Admin interface (HTML/CSS/JS)
│   └── utils/                        # Environment file management
├── alembic/                          # Database migrations
├── logs/                             # Application logs
├── docker-compose.yml               # Docker services configuration
├── Dockerfile                       # Container build configuration
├── requirements.txt                 # Python dependencies
└── .env                             # Environment configuration
```

## API Endpoints

### Public Endpoints
- `GET /` - Service information
- `GET /health` - Health check
- `POST /mip003/` - MIP-003 compliant job submission
- `POST /webhooks/masumi/payment` - Payment confirmation webhook

### Protected Endpoints (require API key if configured)
- `GET /admin` - Admin interface
- `GET /admin/flows` - List all agents
- `GET /admin/running-jobs` - Running jobs status
- `POST /admin/agents/toggle` - Enable/disable agents

## Troubleshooting

### Services won't start
```bash
# Check logs for errors
docker compose logs

# Verify environment configuration
docker compose config
```

### Database connection issues
```bash
# Check PostgreSQL status
docker compose logs postgres

# Verify database connectivity
docker compose exec masumi-connector python -c "from masumi_kodosuni_connector.database.connection import test_connection; test_connection()"
```

### Agent not appearing
1. Verify Kodosumi instance is accessible
2. Check agent identifier configuration in `.env`
3. Restart services after configuration changes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test with Docker Compose
4. Submit a pull request

## License

This project is licensed under the MIT License.