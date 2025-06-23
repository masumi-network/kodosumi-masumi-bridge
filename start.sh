#!/bin/bash
# Masumi Kodosumi Connector Startup Script

echo "🚀 Starting Masumi Kodosumi Connector..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run the setup first:"
    echo "  python3.12 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your settings"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Verify Python version
PYTHON_VERSION=$(python --version)
echo "🐍 Using $PYTHON_VERSION"

if [[ ! $PYTHON_VERSION == *"3.12"* ]]; then
    echo "⚠️  Warning: This project requires Python 3.12.11"
    echo "   Current version: $PYTHON_VERSION"
fi

# Check if masumi package is available
echo "🔍 Checking masumi package..."
python -c "import masumi; print('✅ Masumi package available')" 2>/dev/null || {
    echo "❌ Masumi package not found!"
    echo "Installing requirements..."
    pip install -r requirements.txt
}

echo "🌐 Starting server on http://localhost:8000"
echo "   Admin Panel: http://localhost:8000/admin"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
PYTHONPATH=src python -m uvicorn masumi_kodosuni_connector.main:app --host 0.0.0.0 --port 8000