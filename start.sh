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

# Check if Docker containers are running and shut them down if they are
echo "🔍 Checking for existing Docker containers..."
if docker compose ps -q 2>/dev/null | grep -q .; then
    echo "🛑 Stopping existing Docker containers..."
    docker compose down
    echo "✅ Containers stopped."
else
    echo "✅ No existing containers found."
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

# Give the service a bit more time to fully initialize
echo "⏳ Waiting for service to fully initialize..."
sleep 5

# Reload API routes after service is healthy
echo "🔄 Reloading API routes..."
# Check if API_KEY is set in .env
API_KEY=$(grep "^API_KEY=" .env 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'")

# Create a temporary file to capture response
RESPONSE_FILE=$(mktemp)

if [ -n "$API_KEY" ]; then
    echo "   Using API key authentication..."
    # Use API key if available
    HTTP_CODE=$(curl -X POST http://localhost:8000/admin/reload-routes \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -w "%{http_code}" \
        -o "$RESPONSE_FILE" \
        -s)
else
    echo "   No API key found, trying without authentication..."
    # Try without API key (for backwards compatibility)
    HTTP_CODE=$(curl -X POST http://localhost:8000/admin/reload-routes \
        -H "Content-Type: application/json" \
        -w "%{http_code}" \
        -o "$RESPONSE_FILE" \
        -s)
fi

RESPONSE=$(cat "$RESPONSE_FILE")
rm -f "$RESPONSE_FILE"

echo "   HTTP Response Code: $HTTP_CODE"
if [ -n "$RESPONSE" ]; then
    echo "   Response: $RESPONSE"
fi

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "204" ]; then
    echo "✅ API routes reloaded successfully!"
else
    echo "⚠️  Warning: Could not reload API routes (HTTP $HTTP_CODE). You may need to manually reload them via the admin panel."
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