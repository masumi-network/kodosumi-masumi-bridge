#!/usr/bin/env python3

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing imports...")

try:
    import fastapi
    print("✅ FastAPI available")
except ImportError as e:
    print(f"❌ FastAPI not available: {e}")

try:
    import uvicorn
    print("✅ Uvicorn available")
except ImportError as e:
    print(f"❌ Uvicorn not available: {e}")

try:
    import structlog
    print("✅ Structlog available")
except ImportError as e:
    print(f"❌ Structlog not available: {e}")

try:
    import sqlalchemy
    print("✅ SQLAlchemy available")
except ImportError as e:
    print(f"❌ SQLAlchemy not available: {e}")

try:
    import aiosqlite
    print("✅ aiosqlite available")
except ImportError as e:
    print(f"❌ aiosqlite not available: {e}")

try:
    import httpx
    print("✅ httpx available")
except ImportError as e:
    print(f"❌ httpx not available: {e}")

try:
    import pydantic
    print("✅ pydantic available")
except ImportError as e:
    print(f"❌ pydantic not available: {e}")

print("\nTesting main module...")
try:
    import masumi_kodosuni_connector
    print("✅ Main package available")
except ImportError as e:
    print(f"❌ Main package not available: {e}")

print(f"\nPython version: {sys.version}")