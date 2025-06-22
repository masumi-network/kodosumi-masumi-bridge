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

## Quick Start Guide

### **Prerequisites**
- Python 3.13 (recommended) or Python 3.11+
- Git (for cloning/updating the code)

### **Installation Steps**

1. **Navigate to the project directory:**
   ```bash
   cd /path/to/masumi_kodosuni_connector
   ```

2. **Install required packages:**
   ```bash
   # Install the main dependencies with Python 3.13
   /Library/Frameworks/Python.framework/Versions/3.13/bin/pip3.13 install fastapi uvicorn sqlalchemy aiosqlite httpx structlog pydantic-settings python-dotenv

   # Or install specific versions for compatibility
   /Library/Frameworks/Python.framework/Versions/3.13/bin/pip3.13 install fastapi==0.104.1 uvicorn[standard]==0.24.0 sqlalchemy==2.0.23 httpx==0.25.2 structlog==23.2.0 pydantic-settings==2.0.3 python-dotenv==1.0.0 aiosqlite==0.19.0
   ```

3. **Setup Configuration**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   ```
   
   Edit `.env` to configure your database:
   ```bash
   # For SQLite (recommended for testing)
   DATABASE_URL=sqlite+aiosqlite:///./masumi_kodosuni.db
   
   # For PostgreSQL (production)
   # DATABASE_URL=postgresql+asyncpg://user:password@localhost/masumi_kodosuni
   
   # Kodosumi API Configuration
   KODOSUMI_BASE_URL=http://209.38.221.56:3370
   KODOSUMI_USERNAME=admin
   KODOSUMI_PASSWORD=admin
   
   # Masumi Node Configuration (optional for testing)
   MASUMI_NODE_URL=https://masumi.example.com
   MASUMI_API_KEY=your_masumi_api_key
   ```

4. **Start the Service**:
   ```bash
   # Option 1: Use the provided script
   ./run.sh
   
   # Option 2: Direct command
   PYTHONPATH="./src" /Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 -m masumi_kodosuni_connector.main
   
   # Option 3: If you have Python 3.13 as default python3
   PYTHONPATH="./src" python3 -m masumi_kodosuni_connector.main
   ```

### **Verify Installation**

Once started, test these endpoints:

```bash
# Health check
curl http://localhost:8000/health

# List available flows from Kodosumi
curl http://localhost:8000/flows

# MIP-003 global availability  
curl http://localhost:8000/mip003/availability

# Open API documentation in browser
open http://localhost:8000/docs
```

### **Expected Output**
When you start the service, you should see:
```
🚀 Starting Masumi Kodosuni Connector...
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
{"event": "Starting Masumi Kodosumi Connector", ...}
{"event": "Database initialized successfully", ...}
{"event": "Starting polling service", ...}
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### **Stop the Service**
Press `Ctrl+C` in the terminal where it's running.

### **What Happens When You Start**

The service automatically:
1. ✅ **Discovers Flows**: Connects to Kodosumi server and discovers available flows
2. ✅ **Creates Endpoints**: Generates API endpoints for each discovered flow
3. ✅ **Initializes Database**: Sets up SQLite database tables automatically
4. ✅ **Starts Polling**: Begins background monitoring of active jobs every 30 seconds
5. ✅ **Exposes APIs**: Makes both native and MIP-003 compliant endpoints available

Each discovered flow gets these endpoints:
- **Native API**: `/{flow_key}/runs` - Direct flow execution
- **MIP-003 API**: `/mip003/{flow_key}/start_job` - MIP-003 compliant job execution
- **Schema**: `/mip003/{flow_key}/input_schema` - Input requirements
- **Status**: `/mip003/{flow_key}/status` - Job status checking

### **Troubleshooting**

**Import Errors:**
```bash
# Test what packages are available
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 test_imports.py
```

**Service Won't Start:**
```bash
# Check if the .env file exists and has the right database URL
cat .env

# Make sure run.sh is executable
chmod +x run.sh

# Check Python path
echo $PYTHONPATH
```

**Database Issues:**
```bash
# For SQLite, make sure the directory is writable
ls -la masumi_kodosuni.db

# Reset database if needed
rm -f masumi_kodosuni.db
```

**Full Reset:**
```bash
# Clean start
rm -f masumi_kodosuni.db .env
cp .env.example .env
# Edit .env to configure your database URL
```

**Python Version Issues:**
```bash
# Check which Python versions are available
ls /Library/Frameworks/Python.framework/Versions/

# Use the specific Python version that has the packages installed
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 --version
```

## API Usage

The system exposes two API interfaces:

### 1. Native API (for direct integration)

#### Create a Flow Run
```bash
POST /{flow_key}/runs
Content-Type: application/json

{
  "inputs": {
    "prompt": "Your flow input here",
    "parameters": {...}
  },
  "payment_amount": 10.0
}
```

#### Get Flow Run Status
```bash
GET /{flow_key}/runs/{run_id}
```

### 2. MIP-003 Compliant API (for Masumi Network integration)

The system provides MIP-003 compliant endpoints for each discovered flow:

#### Start Job
```bash
POST /mip003/{flow_key}/start_job
Content-Type: application/json

{
  "identifier_from_purchaser": "my-job-123",
  "input_data": {
    "prompt": "Generate a resume for Alice",
    "style": "professional"
  }
}
```

Response:
```json
{
  "status": "success",
  "job_id": "456",
  "blockchainIdentifier": "block_789def",
  "submitResultTime": 1717171717,
  "unlockTime": 1717172717,
  "externalDisputeUnlockTime": 1717173717,
  "agentIdentifier": "resume-generator",
  "sellerVKey": "addr1qxlkjl23k4jlksdjfl234jlksdf",
  "identifierFromPurchaser": "my-job-123",
  "amounts": [{"amount": 3000000, "unit": "lovelace"}],
  "input_hash": "a87ff679a2f3e71d9181a67b7542122c"
}
```

#### Check Job Status
```bash
GET /mip003/{flow_key}/status?job_id=456
```

Response:
```json
{
  "job_id": "456",
  "status": "completed",
  "result": "Generated resume content..."
}
```

#### Get Input Schema
```bash
GET /mip003/{flow_key}/input_schema
```

Response:
```json
{
  "input_data": [
    {
      "id": "prompt",
      "type": "string",
      "name": "Prompt",
      "validations": [
        {"validation": "min", "value": "1"},
        {"validation": "format", "value": "nonempty"}
      ]
    }
  ]
}
```

#### Check Availability
```bash
GET /mip003/{flow_key}/availability
```

### MIP-003 Job Status Flow

1. `pending` - Job created, awaiting processing
2. `awaiting_payment` - Waiting for payment confirmation  
3. `awaiting_input` - Waiting for additional user input
4. `running` - Job is executing
5. `completed` - Job finished successfully
6. `failed` - Job failed or error occurred

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