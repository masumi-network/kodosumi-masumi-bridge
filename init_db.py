#!/usr/bin/env python3
"""
Database initialization script for Masumi Kodosuni Connector.
This script creates the database tables with the latest schema.
"""

import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from masumi_kodosuni_connector.database.connection import init_db


async def main():
    """Initialize the database with the latest schema."""
    print("Initializing database with latest schema...")
    try:
        await init_db()
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)