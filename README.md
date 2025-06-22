# Masumi Kodosumi Connector

A Python wrapper API for Kodosumi AI Agent jobs with Masumi payment integration.

## Overview

This system provides a wrapper around the Kodosumi API, exposing multiple AI agents through agent-specific endpoints with integrated payment processing via Masumi Node.

## Features

- **Multi-Agent Support**: Configure multiple AI agents through environment variables
- **Agent-Specific URLs**: Each agent accessible through its own base URL (`/{agent_key}/`)
- **Payment Integration**: Masumi Node integration for payment processing before job execution
- **Async Job Processing**: Background polling system to track job status and store results
- **Database Storage**: PostgreSQL storage for job runs, status, and results
- **Clean Architecture**: Modular design with clear separation of concerns

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Client App    │───▶│  Wrapper API     │───▶│  Kodosumi API   │
└─────────────────┘    │                  │    └─────────────────┘
                       │                  │
                       │                  │    ┌─────────────────┐
                       │                  │───▶│  Masumi Node    │
                       └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   PostgreSQL     │
                       │    Database      │
                       └──────────────────┘
```

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Database Setup**:
   ```bash
   # Set up your PostgreSQL database
   # Copy environment config
   cp .env.example .env
   # Edit .env with your configuration
   
   # Run database migrations
   alembic upgrade head
   ```

3. **Configuration**:
   Configure your environment variables in `.env`:
   
   ```bash
   # Database
   DATABASE_URL=postgresql+asyncpg://user:password@localhost/masumi_kodosuni
   
   # External APIs
   KODOSUMI_BASE_URL=https://api.kodosumi.example.com
   KODOSUMI_API_KEY=your_kodosumi_api_key
   MASUMI_NODE_URL=https://masumi.example.com
   MASUMI_API_KEY=your_masumi_api_key
   
   # Agents (JSON format)
   AGENTS_CONFIG={"agent1": {"name": "Agent One", "kodosumi_agent_id": "agent_1_id"}, "agent2": {"name": "Agent Two", "kodosumi_agent_id": "agent_2_id"}}
   ```

4. **Run the Application**:
   ```bash
   python -m masumi_kodosuni_connector.main
   ```

## API Usage

### Create a Job

```bash
POST /{agent_key}/jobs
Content-Type: application/json

{
  "data": {
    "prompt": "Your AI agent prompt here",
    "parameters": {...}
  },
  "payment_amount": 10.0
}
```

Response:
```json
{
  "id": 123,
  "status": "pending_payment",
  "payment_id": "payment_abc123",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Get Job Status

```bash
GET /{agent_key}/jobs/{job_id}
```

Response:
```json
{
  "id": 123,
  "status": "completed",
  "result": {
    "output": "AI agent response...",
    "metadata": {...}
  },
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:05:00Z"
}
```

### Job Status Flow

1. `pending_payment` - Waiting for payment confirmation
2. `payment_confirmed` - Payment received, starting Kodosumi job
3. `running` - Job is executing on Kodosumi
4. `completed` - Job finished successfully
5. `failed` - Job failed or error occurred

## Testing

```bash
pip install -e .[dev]
pytest
```

## Development

- **Clean Code**: Simple, readable Python code following best practices
- **Type Hints**: Full type annotation support
- **Async/Await**: Fully asynchronous for optimal performance
- **Error Handling**: Comprehensive error handling and logging
- **Database Migrations**: Alembic for database schema management