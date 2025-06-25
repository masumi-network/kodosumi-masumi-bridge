#!/usr/bin/env python3
"""
Simple runner script for the payment completion hash generator.
Run this from the project root directory.
"""

import sys
import os

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

# Import and run the script
from generate_payment_completion_hashes import main
import asyncio

if __name__ == "__main__":
    asyncio.run(main())