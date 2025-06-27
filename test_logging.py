#!/usr/bin/env python3

# Test script to verify flow submission logging works
import sys
import os
sys.path.insert(0, 'src')

from masumi_kodosuni_connector.config.logging import configure_logging
import logging

# Configure logging
configure_logging()

# Get the flow submission logger
flow_logger = logging.getLogger("flow_submission")

# Test logging
flow_logger.info("=== TESTING FLOW SUBMISSION LOGGING ===")
flow_logger.info("This is a test message")
flow_logger.error("This is a test error")
flow_logger.debug("This is a test debug message")

print("Test logging complete. Check flow_submissions.log file.")