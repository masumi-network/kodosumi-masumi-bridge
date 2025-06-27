# Flow Submission Logging Setup

## Overview
The Masumi Kodosumi Connector now includes comprehensive logging for flow submissions and results in a dedicated log file: `flow_submissions.log`

## Log File Location
The log file will be created in the project root directory:
```
/path/to/masumi_kodosuni_connector/flow_submissions.log
```

## What Gets Logged
The logging captures the complete flow submission and processing lifecycle:

### 1. Flow Submission Start
- Flow key and name
- Input parameters (JSON formatted)
- Purchaser identifier
- Payment amount

### 2. Payment Processing
- Payment request creation
- Payment response data
- Payment ID assignment
- Payment monitoring start

### 3. Payment Confirmation
- Payment confirmation receipt
- Flow run status updates

### 4. Kodosumi Integration
- Flow launch to Kodosumi
- Kodosumi run ID assignment
- Status polling and updates
- Result and event retrieval

### 5. Error Handling
- All errors with full context
- API errors and HTTP status codes
- Service-level exceptions

## Log Format
```
YYYY-MM-DD HH:MM:SS,mmm - flow_submission - LEVEL - MESSAGE
```

Example:
```
2025-06-27 13:52:12,446 - flow_submission - INFO - === FLOW SUBMISSION STARTED ===
2025-06-27 13:52:12,446 - flow_submission - INFO - Flow Key: -_127.0.0.1_8001_advanced_web_research_-_
2025-06-27 13:52:12,446 - flow_submission - INFO - Inputs: {
  "question": "What are the latest trends in AI?"
}
```

## Deployment Instructions

### For Docker Deployment
1. **Update your code** on the remote server with the latest changes
2. **Rebuild and restart** the Docker container:
   ```bash
   docker-compose build masumi-connector
   docker-compose restart masumi-connector
   ```
3. **Check log file location**:
   ```bash
   docker-compose exec masumi-connector ls -la /app/flow_submissions.log
   ```

### For Direct Deployment
1. **Update your code** on the remote server
2. **Restart the service**:
   ```bash
   sudo systemctl restart masumi-connector
   ```
3. **Check log file location**:
   ```bash
   ls -la /opt/masumi-kodosuni-connector/flow_submissions.log
   ```

### Monitoring Logs
**Real-time monitoring:**
```bash
tail -f /path/to/masumi_kodosuni_connector/flow_submissions.log
```

**Recent entries:**
```bash
tail -50 /path/to/masumi_kodosuni_connector/flow_submissions.log
```

**Search for specific flow:**
```bash
grep "Flow run ID: your-run-id" /path/to/masumi_kodosuni_connector/flow_submissions.log
```

**Search for errors:**
```bash
grep "ERROR" /path/to/masumi_kodosuni_connector/flow_submissions.log
```

## Troubleshooting

### Log File Not Created
1. **Check working directory** - the service must start from the project root
2. **Check permissions** - ensure write access to the project directory  
3. **Check service logs** for startup errors:
   ```bash
   # Docker
   docker-compose logs masumi-connector
   
   # Systemd
   sudo journalctl -u masumi-connector -f
   ```

### Missing Log Entries
1. **Verify logging configuration** by running the test script:
   ```bash
   python test_logging.py
   ```
2. **Check if service is using updated code** - restart after code changes
3. **Verify flow submissions are actually being made** - check API endpoints

### Log File Too Large
The log file will grow over time. Consider setting up log rotation:
```bash
# Add to crontab for daily rotation
0 0 * * * /usr/sbin/logrotate /path/to/logrotate.conf
```

## API Changes
**Important:** The FlowRunRequest schema now includes a required `identifier_from_purchaser` field:

```json
{
  "inputs": {
    "question": "Your research question"
  },
  "identifier_from_purchaser": "user-identifier-123",
  "payment_amount": 10000000
}
```

Update any API clients to include this field in POST requests to `/{flow_key}/runs`.