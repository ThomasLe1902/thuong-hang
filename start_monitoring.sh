#!/bin/bash

# Start monitoring services with Loki
echo "Starting AI FTES Monitoring Stack with Loki..."

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start monitoring services
echo "Starting monitoring services..."
docker-compose -f docker-compose.monitoring.yml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 30

# Check if services are running
echo "Checking service status..."
docker-compose -f docker-compose.monitoring.yml ps

echo ""
echo "=== Monitoring Stack Started ==="
echo "📊 Grafana: http://localhost:3030 (admin/admin123)"
echo "🔍 Prometheus: http://localhost:9090"
echo "📝 Loki: http://localhost:3100"
echo "🖥️  Node Exporter: http://localhost:9100"
echo "📋 Promtail: Running in background"
echo ""
echo "🎯 Grafana Dashboards:"
echo "  - AI FTES System Monitoring"
echo "  - AI FTES Loki Logs Dashboard"
echo ""
echo "To stop monitoring: docker-compose -f docker-compose.monitoring.yml down" 