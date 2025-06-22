#!/bin/bash

echo "🚀 Starting Masumi Kodosuni Connector..."

# Export PYTHONPATH
export PYTHONPATH="/Users/patricktobler/masumi_kodosuni_connector/src:$PYTHONPATH"

# Use the correct Python version
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3.13 run.py