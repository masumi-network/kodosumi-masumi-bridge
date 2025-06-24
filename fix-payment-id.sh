#!/bin/bash

# Fix payment ID length issue
set -e

echo "🔧 Fixing payment ID length issue..."

# Method 1: Try Alembic migration first
echo "📝 Attempting Alembic migration..."
if docker-compose exec -T masumi-connector alembic upgrade head 2>/dev/null; then
    echo "✅ Alembic migration successful!"
else
    echo "⚠️  Alembic migration failed, trying direct SQL..."
    
    # Method 2: Direct SQL as fallback
    echo "📝 Running direct SQL migration..."
    docker-compose exec -T postgres psql -U postgres -d masumi_kodosuni -c "ALTER TABLE flow_runs ALTER COLUMN masumi_payment_id TYPE TEXT;" || {
        echo "❌ SQL migration failed. Database may not be ready."
        echo "🔄 Restarting services and trying again..."
        docker-compose restart
        sleep 15
        docker-compose exec -T postgres psql -U postgres -d masumi_kodosuni -c "ALTER TABLE flow_runs ALTER COLUMN masumi_payment_id TYPE TEXT;"
    }
fi

echo "✅ Payment ID length fix applied!"
echo "🔄 Restarting services to ensure changes take effect..."
docker-compose restart masumi-connector

echo "🎉 Fix complete! The payment ID field can now handle longer values."