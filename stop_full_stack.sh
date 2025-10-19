#!/bin/bash

echo "🛑 Stopping AI FTES Full Stack..."

# Stop backend service first
echo "🖥️  Stopping backend service..."
docker-compose -f docker-compose-be.yml down

# Stop monitoring services
echo "📊 Stopping monitoring services..."
docker-compose -f docker-compose.monitoring.yml down

# Clean up network if no other containers are using it
echo "🌐 Cleaning up network..."
docker network ls --format "{{.Name}}" | grep -q "monitoring" && {
    echo "🧹 Removing monitoring network..."
    docker network rm monitoring 2>/dev/null || echo "⚠️  Network 'monitoring' is still in use by other containers"
}

echo ""
echo "✅ All services stopped successfully!"
echo ""
echo "🔄 To start services again:"
echo "   ./start_full_stack.sh" 