# Masumi Kodosumi Connector

A FastAPI-based wrapper service that integrates Kodosumi AI agents with Masumi payment processing, providing MIP-003 compliant endpoints for secure, payment-gated AI agent execution.

## Features

- 🔐 **Secure Payment Integration**: Uses Masumi Payment Service for payment processing
- 🤖 **AI Agent Management**: Connects to multiple Kodosumi AI agents
- 📋 **MIP-003 Compliant**: Implements MIP-003 specification for job management
- 🔑 **Per-Agent Configuration**: Individual agent registration with unique identifiers
- 🛡️ **Security**: UUID-based job IDs, agent-level access control
- 📊 **Admin Panel**: Web-based management interface
- 🌐 **Network Support**: Preprod (testnet) and Mainnet support

## Requirements

**⚠️ Important: This project requires Python 3.12.11 due to the Masumi package dependency.**

### System Requirements
- Python 3.12.11 (required for masumi package)
- macOS/Linux/Windows
- 2GB+ RAM
- Internet connection

### Dependencies
All dependencies are listed in `requirements.txt` and will be installed automatically.

## 🚀 Quick Production Deployment

**Deploy to DigitalOcean in 5 commands:**
```bash
# 1. Create Ubuntu 22.04 droplet at cloud.digitalocean.com
# 2. Connect and auto-setup
ssh root@YOUR_DROPLET_IP
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/masumi_kodosuni_connector/main/digitalocean-setup.sh | bash

# 3. Upload code and configure
cd /opt/masumi-connector
git clone https://github.com/YOUR_USERNAME/masumi_kodosuni_connector.git .
cp .env.docker .env && nano .env  # Add your credentials

# 4. Deploy
./deploy-docker.sh

# 5. Access at http://YOUR_DROPLET_IP:8000
```
**Cost:** $12-24/month | **Time:** ~25 minutes | **Full Guide:** [See Production Deployment](#production-deployment)

## Quick Start (Local Development)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd masumi_kodosuni_connector
```

### 2. Create Virtual Environment (Python 3.12 Required)

```bash
# Create virtual environment with Python 3.12
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/macOS
# or
venv\Scripts\activate     # On Windows
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# Database Configuration
DATABASE_URL=sqlite+aiosqlite:///./masumi_kodosuni.db

# Kodosumi API Configuration
KODOSUMI_BASE_URL=http://209.38.221.56:3370
KODOSUMI_USERNAME=admin
KODOSUMI_PASSWORD=admin

# Masumi Payment Service Configuration
PAYMENT_SERVICE_URL=https://payment.masumi.network/api/v1
PAYMENT_API_KEY=your_masumi_api_key
NETWORK=preprod  # Options: preprod (testnet), mainnet
SELLER_VKEY=your_seller_verification_key
PAYMENT_AMOUNT=10000000
PAYMENT_UNIT=lovelace
MASUMI_TEST_MODE=false

# Agent-specific configurations (only agents with identifiers will be callable)
AGENT_IDENTIFIER_-_localhost_8001_health-fitness-agent_-_=msm_hlth_7x4n9b2vY8kL3zA1
AGENT_IDENTIFIER_-_localhost_8001_seo-agent_-_=msm_seo_p1z5v9a2c7e4h8j3
AGENT_IDENTIFIER_-_localhost_8001_meeting-agent_-_=msm_meet_m6q9s1u4x7y0b3f6

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
```

### 5. Run the Service

#### Option 1: Using the startup script (recommended)
```bash
./start.sh
```

#### Option 2: Manual startup
```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the server
PYTHONPATH=src python -m uvicorn masumi_kodosuni_connector.main:app --host 0.0.0.0 --port 8000

# For development with auto-reload
PYTHONPATH=src python -m uvicorn masumi_kodosuni_connector.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Access the Service

- **Admin Panel**: http://localhost:8000/admin
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Agent Configuration

### Enabling Agents

Only agents with configured identifiers will be accessible via the API. To enable an agent:

1. Stop the server
2. Add the agent identifier to your `.env` file:
   ```
   AGENT_IDENTIFIER_<flow_key>=<your-agent-identifier>
   ```
3. Restart the server

### Agent Flow Keys

Available agent flow keys:
- `-_localhost_8001_health-fitness-agent_-_` - AI Health & Fitness Planner
- `-_localhost_8001_seo-agent_-_` - SEO Analysis Agent  
- `-_localhost_8001_meeting-agent_-_` - Meeting Preparation Agent
- `-_localhost_8001_movie-production-agent_-_` - AI Movie Production Agent
- `-_localhost_8001_nft-agent_-_` - Content to NFT Agent
- `-_localhost_8001_llm-txt-agent_-_` - LLMs.txt Generator Agent
- `-_localhost_8001_media-trend-agent_-_` - Media Trend Analysis Agent

### Example Configuration

```bash
# Enable 3 agents
AGENT_IDENTIFIER_-_localhost_8001_health-fitness-agent_-_=msm_hlth_7x4n9b2vY8kL3zA1
AGENT_IDENTIFIER_-_localhost_8001_seo-agent_-_=msm_seo_p1z5v9a2c7e4h8j3
AGENT_IDENTIFIER_-_localhost_8001_meeting-agent_-_=msm_meet_m6q9s1u4x7y0b3f6

# Disable other agents by commenting them out
# AGENT_IDENTIFIER_-_localhost_8001_movie-production-agent_-_=msm_movie_i9l2o5r8t1w4z7c0
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

The system uses a dual polling architecture to manage job lifecycles:

```
PENDING_PAYMENT → PAYMENT_CONFIRMED → STARTING → RUNNING → FINISHED
     ↓                ↓                  ↓          ↓          ↓
Masumi polling    Payment confirmed   Kodosumi   Job runs   Complete
   (60s)           → Launch job       polling    polling    + cleanup
                                      (10s)      (10s)
```

#### Status Definitions:
1. `pending` - Job created, awaiting processing
2. `awaiting_payment` - Waiting for payment confirmation  
3. `awaiting_input` - Waiting for additional user input
4. `running` - Job is executing
5. `completed` - Job finished successfully
6. `failed` - Job failed or error occurred

#### Polling System:
- **Masumi Payment Polling**: External system monitors blockchain payments (~60 second intervals)
- **Internal Job Polling**: Our system checks Kodosumi job progress (10 second intervals)
- **Configuration**: Set `POLLING_INTERVAL_SECONDS=10` in `.env` to adjust internal polling

### Schema Conversion and Field Type Mapping

The system automatically converts Kodosumi form schemas to MIP-003 compatible input schemas. Some Kodosumi field types are not natively supported by MIP-003 and are converted to strings with specific format requirements.

#### Supported Field Types (Direct Mapping):
| Kodosumi Type | MIP-003 Type | Description |
|---------------|--------------|-------------|
| `text` | `string` | Text input field |
| `inputtext` | `string` | Text input field |
| `inputnumber` | `number` | Numeric input |
| `inputemail` | `string` | Email input (validates as string) |
| `inputpassword` | `string` | Password input |
| `textarea` | `string` | Multi-line text |
| `select` | `option` | Dropdown selection |
| `checkbox` | `boolean` | Checkbox input |
| `radio` | `option` | Radio button selection |
| `slider` | `number` | Numeric slider |
| `switch` | `boolean` | Toggle switch |
| `fileupload` | `string` | File upload (converted to string) |

#### Unsupported Field Types (Converted to String):
| Kodosumi Type | Converted To | Format Required | Example |
|---------------|--------------|-----------------|---------|
| `date` | `string` | `YYYY-MM-DD` | `2024-12-25` |
| `time` | `string` | `HH:MM` | `14:30` |
| `datetime` | `string` | `YYYY-MM-DD HH:MM` | `2024-12-25 14:30` |
| `file` | `string` | File path or URL | `/path/to/file.txt` |
| `color` | `string` | Hex color or name | `#FF0000` or `red` |

#### Example Conversion:

**Kodosumi Schema (with date field):**
```json
{
  "type": "date",
  "name": "timeframe", 
  "label": "Start Date (Max 30 days timeframe)",
  "required": true,
  "placeholder": "Select start date"
}
```

**Converted MIP-003 Schema:**
```json
{
  "id": "timeframe",
  "type": "string",
  "name": "Start Date (Max 30 days timeframe)",
  "data": {
    "description": "Enter date in YYYY-MM-DD format (e.g., 2024-12-25)",
    "placeholder": "Select start date"
  },
  "validations": null
}
```

**User Input Example:**
When calling the API, users must provide the date as a string:
```json
{
  "input_data": {
    "timeframe": "2024-06-23",
    "username": "bmw",
    "user_query": "What is the general imagery like?"
  }
}
```

## Production Deployment

### 🌊 **DigitalOcean Deployment (Recommended)**

Deploy your Masumi Kodosuni Connector to production in ~25 minutes:

#### **Step 1: Create DigitalOcean Droplet**
1. Go to [cloud.digitalocean.com](https://cloud.digitalocean.com)
2. Create Ubuntu 22.04 droplet (minimum 2GB RAM, $12/month)
3. Note your droplet IP address

#### **Step 2: Auto-Setup Server**
```bash
# Connect to your droplet
ssh root@YOUR_DROPLET_IP

# Run automated setup script
curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/masumi_kodosuni_connector/main/digitalocean-setup.sh | bash
```

#### **Step 3: Upload Your Code**
```bash
cd /opt/masumi-connector
git clone https://github.com/YOUR_USERNAME/masumi_kodosuni_connector.git .
```

#### **Step 4: Configure Environment**
```bash
cp .env.docker .env
nano .env
```

**Update these values with your actual credentials:**
```bash
# Strong password for PostgreSQL
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE

# Your Masumi Payment credentials
PAYMENT_API_KEY=YOUR_ACTUAL_MASUMI_API_KEY
SELLER_VKEY=YOUR_ACTUAL_SELLER_VERIFICATION_KEY
NETWORK=preprod  # Change to 'mainnet' for production
MASUMI_TEST_MODE=false

# Your agent identifiers
AGENT_IDENTIFIER_-_127.0.0.1_8001_instagram_-_=YOUR_INSTAGRAM_AGENT_ID
AGENT_IDENTIFIER_-_127.0.0.1_8001_linkedin_insights_-_=YOUR_LINKEDIN_AGENT_ID
AGENT_IDENTIFIER_-_127.0.0.1_8001_newsagent_-_=YOUR_NEWS_AGENT_ID
```

#### **Step 5: Deploy**
```bash
./deploy-docker.sh
```

#### **Step 6: Setup SSL (Optional)**
```bash
# Point your domain to YOUR_DROPLET_IP, then:
certbot --nginx -d yourdomain.com
```

#### **Access Your Application**
- **Direct**: `http://YOUR_DROPLET_IP:8000`
- **Domain**: `https://yourdomain.com`
- **Admin**: `/admin`
- **API Docs**: `/docs`

#### **Management Commands**
```bash
masumi-connector start    # Start services
masumi-connector stop     # Stop services
masumi-connector restart  # Restart services
masumi-connector logs     # View logs
masumi-connector status   # Check status
masumi-connector backup   # Create backup
masumi-connector update   # Update application
```

**🚀 Total Cost: $12-24/month | Setup Time: ~25 minutes**

📚 **Full DigitalOcean Guide**: See `DIGITALOCEAN_SETUP.md` for detailed instructions.

### 🐳 **Docker Deployment (Alternative)**

For local or other cloud deployments:

```bash
# Configure environment
cp .env.docker .env
nano .env  # Update with your settings

# Deploy with Docker Compose
docker-compose up -d

# Check status
docker-compose ps
curl http://localhost:8000/health
```

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

## Virtual Environment Setup

**Important**: Always use the virtual environment with Python 3.12.11:

### Starting the Service (Updated Instructions)

```bash
# Navigate to project directory
cd masumi_kodosuni_connector

# Activate virtual environment
source venv/bin/activate

# Verify Python version
python --version  # Should show Python 3.12.11

# Start the service
python -m uvicorn masumi_kodosuni_connector.main:app --host 0.0.0.0 --port 8000
```

### Stopping the Service

```bash
# Stop with Ctrl+C if running in foreground

# Or kill by process name
pkill -f uvicorn
```

### Troubleshooting Python Version Issues

```bash
# Check if Python 3.12 is available
python3.12 --version

# Recreate virtual environment if needed
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration Reference

### Network Options

- **preprod**: Testnet for development and testing
- **mainnet**: Production Cardano network

### Test Mode

When `MASUMI_TEST_MODE=true`:
- Payments are simulated (5-second delay)
- No real payment processing occurs
- Useful for development and testing

## Security Notes

⚠️ **Important**: All example passwords, API keys, and agent identifiers shown in this documentation are random examples for template purposes only. Replace them with your actual secure credentials before deployment.

**Security Best Practices:**
- Generate strong random passwords for production
- Use unique agent identifiers for each deployment
- Keep your `.env` file secure and never commit it to version control
- Regularly update passwords and API keys
- Monitor access logs and system resources