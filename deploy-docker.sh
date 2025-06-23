#!/bin/bash

# Docker deployment script for Masumi Kodosuni Connector
set -e

echo "🚀 Deploying Masumi Kodosuni Connector with Docker..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.docker .env
    echo "⚠️  Please edit .env file with your configuration before continuing."
    echo "   nano .env"
    read -p "Press Enter after configuring .env file..."
fi

# Build and start services
echo "🔨 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

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
    docker-compose logs masumi-connector
    exit 1
fi

# Display status
echo ""
echo "🎉 Deployment successful!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🌐 URLs:"
echo "   Health: http://localhost:8000/health"
echo "   Admin:  http://localhost:8000/admin"
echo "   Docs:   http://localhost:8000/docs"
echo ""
echo "📋 Useful Commands:"
echo "   View logs:    docker-compose logs -f masumi-connector"
echo "   Stop services: docker-compose down"
echo "   Restart:      docker-compose restart masumi-connector"
echo ""
echo "📚 See DEPLOYMENT.md for detailed configuration and management."