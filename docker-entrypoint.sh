#!/bin/sh
set -e

echo "🚀 Starting Masumi Kodosumi Connector..."

# Function to reload routes
reload_routes() {
    echo "🔄 Reloading API routes..."
    
    # Try to get API key from environment
    if [ -n "$API_KEY" ]; then
        # Use API key if available
        curl -X POST http://localhost:8000/admin/reload-routes \
            -H "Authorization: Bearer $API_KEY" \
            -H "Content-Type: application/json" \
            --silent --fail > /dev/null 2>&1
    else
        # Try without API key (for backwards compatibility)
        curl -X POST http://localhost:8000/admin/reload-routes \
            -H "Content-Type: application/json" \
            --silent --fail > /dev/null 2>&1
    fi
    
    if [ $? -eq 0 ]; then
        echo "✅ API routes reloaded successfully!"
    else
        echo "⚠️  Warning: Could not reload API routes. You may need to manually reload them via the admin panel."
    fi
}

# Start the application in the background
python -m uvicorn masumi_kodosuni_connector.main:app --host 0.0.0.0 --port 8000 &
APP_PID=$!

# Wait for the service to be healthy
echo "⏳ Waiting for service to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Service is healthy!"
        
        # Reload routes after service is healthy
        reload_routes
        
        # Keep the script running by waiting for the app process
        wait $APP_PID
        exit 0
    fi
    
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts - waiting for service..."
    sleep 2
done

echo "❌ Service failed to start within timeout"
kill $APP_PID 2>/dev/null
exit 1