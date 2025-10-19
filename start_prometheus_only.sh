#!/bin/bash

# AI FTES Prometheus-Only Stack Startup Script
# Starts backend application with Prometheus monitoring (no Jaeger)

set -e

echo "📊 Starting AI FTES with Prometheus-Only Monitoring..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Check if backend image exists, rebuild if needed
if ! docker images | grep -q "hotonbao/ai-ftes-be"; then
    echo "❌ Backend image 'hotonbao/ai-ftes-be:latest' not found."
    echo "🔨 Building backend image automatically..."
    ./build_backend.sh
else
    echo "✅ Backend image found. Checking if rebuild is needed..."
    # Check if wait-for-jaeger.sh exists in current directory (indicates need for rebuild)
    if [ -f "wait-for-jaeger.sh" ] && [ "wait-for-jaeger.sh" -nt "$(docker inspect --format='{{.Created}}' hotonbao/ai-ftes-be:latest 2>/dev/null || echo '1970-01-01')" ]; then
        echo "🔄 Rebuilding image with latest changes..."
        ./build_backend.sh
    fi
fi

# Create monitoring directories if they don't exist
echo "📁 Creating monitoring directories..."
mkdir -p monitoring/grafana/provisioning/datasources
mkdir -p monitoring/grafana/provisioning/dashboards
mkdir -p monitoring/grafana/dashboards

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.prometheus-only.yml down 2>/dev/null || true

# Start the Prometheus-only stack
echo "🐳 Starting Prometheus-only stack (Backend + Prometheus + Grafana)..."
docker-compose -f docker-compose.prometheus-only.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Check Backend
if curl -s http://localhost:7860/health > /dev/null; then
    echo "✅ AI FTES Backend is running on http://localhost:7860"
    echo "   Health: http://localhost:7860/health"
    echo "   Metrics: http://localhost:7860/metrics"
    echo "   API Docs: http://localhost:7860/docs"
else
    echo "⚠️  Backend might not be ready yet"
fi

# Check Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "✅ Prometheus is running on http://localhost:9090"
else
    echo "⚠️  Prometheus might not be ready yet"
fi

# Check Grafana
if curl -s http://localhost:3030/api/health > /dev/null; then
    echo "✅ Grafana is running on http://localhost:3030"
    echo "   Login: admin / admin123"
else
    echo "⚠️  Grafana might not be ready yet"
fi

echo ""
echo "📊 Prometheus-Only Stack is running!"
echo ""
echo "🔧 Active Services:"
echo "   📈 AI FTES Backend:"
echo "      • Main App: http://localhost:7860"
echo "      • Health Check: http://localhost:7860/health"
echo "      • API Documentation: http://localhost:7860/docs"
echo "      • Metrics Endpoint: http://localhost:7860/metrics"
echo ""
echo "   📊 Monitoring (Prometheus Only):"
echo "      • Grafana Dashboard: http://localhost:3030 (admin/admin123)"
echo "        - AI FTES Backend Monitoring (Application metrics)"
echo "        - System Monitoring Dashboard (CPU, Memory, Disk, Network)"
echo "      • Prometheus: http://localhost:9090"
echo "      • Node Exporter (System metrics): http://localhost:9100"
echo ""
echo "ℹ️  Services NOT running:"
echo "   ❌ Jaeger (Distributed Tracing) - Disabled"
echo "   ❌ OpenTelemetry Collector - Disabled"
echo ""
echo "🔧 Container Status:"
docker-compose -f docker-compose.prometheus-only.yml ps
echo ""
echo "💡 Tips:"
echo "   • Wait 2-3 minutes for dashboards to populate with data"
echo "   • Generate some API traffic to see metrics in Grafana"
echo "   • Check logs: docker-compose -f docker-compose.prometheus-only.yml logs [service-name]"
echo "   • To enable Jaeger: Use './start_full_stack.sh' instead"
echo ""
echo "🛑 To stop: docker-compose -f docker-compose.prometheus-only.yml down"
echo "" 