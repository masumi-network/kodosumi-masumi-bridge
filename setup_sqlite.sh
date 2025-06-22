#!/bin/bash

echo "🚀 Setting up Masumi Kodosuni Connector with SQLite..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file for SQLite..."
    cp .env.example .env
    # Replace PostgreSQL with SQLite
    sed -i '' 's|DATABASE_URL=postgresql+asyncpg://user:password@localhost/masumi_kodosuni|DATABASE_URL=sqlite+aiosqlite:///./masumi_kodosuni.db|g' .env
    echo "✅ Created .env with SQLite configuration"
fi

# Install dependencies (skip asyncpg for SQLite)
echo "📦 Installing dependencies..."
pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 sqlalchemy==2.0.23 alembic==1.12.1 httpx==0.25.2 pydantic==2.4.2 pydantic-settings==2.0.3 python-dotenv==1.0.0 structlog==23.2.0 pytest==7.4.3 pytest-asyncio==0.21.1 aiosqlite==0.19.0

# Install package in development mode
echo "📦 Installing package in development mode..."
pip install -e .

# Initialize database
echo "🗄️  Setting up SQLite database..."
alembic revision --autogenerate -m "Initial flow_runs schema"
alembic upgrade head

echo "✅ Setup complete!"
echo ""
echo "🔧 Next steps:"
echo "1. The .env file is configured with SQLite (no additional setup needed)"
echo "2. Run: python -m masumi_kodosuni_connector.main"
echo ""
echo "🌐 The service will be available at:"
echo "   - Native API: http://localhost:8000/{flow_key}/runs"
echo "   - MIP-003 API: http://localhost:8000/mip003/{flow_key}/start_job"
echo "   - Documentation: http://localhost:8000/docs"
echo ""
echo "📄 Database file: ./masumi_kodosuni.db"