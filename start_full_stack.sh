#!/bin/bash

echo "🚀 Starting AI FTES Full Stack with Monitoring..."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Create external network if it doesn't exist
echo "🌐 Creating monitoring network..."
docker network create monitoring 2>/dev/null || echo "✅ Network 'monitoring' already exists"

# Create logs directory if it doesn't exist
echo "📁 Creating logs directory..."
mkdir -p logs

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.monitoring.yml down 2>/dev/null || true
docker-compose -f docker-compose-be.yml down 2>/dev/null || true

# Start monitoring services first
echo "📊 Starting monitoring services..."
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for monitoring services to be ready
echo "⏳ Waiting for monitoring services to be ready..."
sleep 30

# Check if Loki is accessible
echo "🔍 Checking Loki connectivity..."
max_attempts=30
attempt=1
while [ $attempt -le $max_attempts ]; do
    if curl -s "http://localhost:3100/ready" > /dev/null; then
        echo "✅ Loki is ready!"
        break
    fi
    echo "⏳ Waiting for Loki... (attempt $attempt/$max_attempts)"
    sleep 5
    ((attempt++))
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ Loki failed to start after $max_attempts attempts"
    exit 1
fi

# Start backend service
echo "🖥️  Starting backend service..."
docker-compose -f docker-compose-be.yml up -d

# Wait for backend to be ready
echo "⏳ Waiting for backend service to be ready..."
sleep 15

# Check service status
echo "📋 Checking all services status..."
echo ""
echo "=== Monitoring Services ==="
docker-compose -f docker-compose.monitoring.yml ps
echo ""
echo "=== Backend Service ==="
docker-compose -f docker-compose-be.yml ps
echo ""

# Test Loki connectivity from backend
echo "🔗 Testing Loki connectivity from backend..."
docker exec ai-ftes-be curl -s http://loki:3100/ready > /dev/null && echo "✅ Backend can connect to Loki!" || echo "❌ Backend cannot connect to Loki"

echo ""
echo "🎉 === Full Stack Started Successfully ==="
echo "🌐 Services URLs:"
echo "   📊 Grafana: http://localhost:3030 (admin/admin123)"
echo "   🔍 Prometheus: http://localhost:9090"
echo "   📝 Loki: http://localhost:3100"
echo "   🖥️  Node Exporter: http://localhost:9100"
echo "   🚀 AI FTES Backend: http://localhost:7860"
echo ""
echo "🎯 Grafana Dashboards:"
echo "   - AI FTES System Monitoring"
echo "   - AI FTES Loki Logs Dashboard"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose -f docker-compose-be.yml down"
echo "   docker-compose -f docker-compose.monitoring.yml down"
echo ""
echo "📄 To check backend logs:"
echo "   docker logs ai-ftes-be" 