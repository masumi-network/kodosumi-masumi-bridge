#!/bin/bash

echo "🚀 Setting up Masumi Kodosuni Connector..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your database credentials before continuing!"
    echo "   Update DATABASE_URL with your PostgreSQL connection string"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Install package in development mode
echo "📦 Installing package in development mode..."
pip install -e .

# Initialize database
echo "🗄️  Setting up database..."
alembic revision --autogenerate -m "Initial flow_runs schema"
alembic upgrade head

echo "✅ Setup complete!"
echo ""
echo "🔧 Next steps:"
echo "1. Edit .env file with your database credentials"
echo "2. Run: python -m masumi_kodosuni_connector.main"
echo ""
echo "🌐 The service will be available at:"
echo "   - Native API: http://localhost:8000/{flow_key}/runs"
echo "   - MIP-003 API: http://localhost:8000/mip003/{flow_key}/start_job"
echo "   - Documentation: http://localhost:8000/docs"