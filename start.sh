#!/bin/bash

# Masumi Kodosuni Connector - Docker Compose Startup Script
set -e

echo "🚀 Starting Masumi Kodosuni Connector..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not available. Please make sure Docker is up to date."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env file with your configuration before continuing."
    echo "   Required settings:"
    echo "   - KODOSUMI_USERNAME and KODOSUMI_PASSWORD"
    echo "   - PAYMENT_API_KEY and SELLER_VKEY"
    echo "   - Agent identifiers (AGENT_IDENTIFIER_*)"
    echo ""
    echo "   Edit now: nano .env"
    echo ""
    read -p "Press Enter after configuring .env file..."
fi

# Build and start services
echo "🔨 Building Docker images..."
docker compose build

echo "🚀 Starting services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Run database migration
echo "🔧 Running database migration..."
docker compose exec -T masumi-connector alembic upgrade head || echo "⚠️  Migration may have already been applied"

# Check health
echo "🔍 Checking service health..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Service is healthy!"
        break
    fi
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts - waiting for service..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Service failed to start. Checking logs..."
    docker compose logs masumi-connector
    exit 1
fi

# Display status
echo ""
echo "🎉 Deployment successful!"
echo ""
echo "📊 Service Status:"
docker compose ps
echo ""
echo "🌐 URLs:"
echo "   Health:      http://localhost:8000/health"
echo "   Admin:       http://localhost:8000/admin"
echo "   API Docs:    http://localhost:8000/docs"
echo ""
echo "📋 Useful Commands:"
echo "   View logs:        docker compose logs -f masumi-connector"
echo "   Stop services:    docker compose down"
echo "   Restart:          docker compose restart masumi-connector"
echo "   Rebuild:          docker compose down && docker compose build --no-cache && docker compose up -d"
echo ""