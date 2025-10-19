# Monitoring Setup Guide

This document explains how to configure and use Prometheus and OpenTelemetry monitoring in the AI FTES Backend.

## Features

✅ **Prometheus Metrics Collection**

- Request count, duration, and active connections
- AI agent call metrics
- Database query metrics
- Custom business metrics

✅ **OpenTelemetry Distributed Tracing**

- Automatic FastAPI instrumentation
- Request/response tracing
- Database operation tracing
- Custom operation tracing

✅ **Health and Metrics Endpoints**

- `/health` - Health check endpoint
- `/metrics` - Prometheus metrics endpoint

## Environment Configuration

Add these variables to your `.env` file:

```bash
# Service Information
SERVICE_NAME=ai-ftes-backend
SERVICE_VERSION=1.0.0
ENVIRONMENT=development

# Prometheus Configuration
ENABLE_PROMETHEUS=true

# OpenTelemetry Configuration
ENABLE_JAEGER=true
ENABLE_OTLP=false

# Jaeger Configuration (when ENABLE_JAEGER=true)
JAEGER_ENDPOINT=http://localhost:14268/api/traces

# OTLP Configuration (when ENABLE_OTLP=true)
OTLP_ENDPOINT=http://localhost:4317
```

## Production Configuration Example

```bash
ENVIRONMENT=production
ENABLE_PROMETHEUS=true
ENABLE_JAEGER=true
JAEGER_ENDPOINT=http://jaeger-collector:14268/api/traces
ENABLE_OTLP=true
OTLP_ENDPOINT=http://otel-collector:4317
```

## Available Metrics

### Automatic Metrics

- `fastapi_requests_total` - Total HTTP requests
- `fastapi_request_duration_seconds` - HTTP request duration
- `fastapi_active_connections` - Active connections

### AI-Specific Metrics

- `ai_agent_calls_total` - AI agent invocations
- `ai_agent_duration_seconds` - AI agent execution time
- `database_queries_total` - Database operations

## Using Custom Metrics in Your Code

```python
from src.config.monitoring import (
    increment_agent_calls,
    observe_agent_duration,
    increment_database_queries,
    trace_operation
)
import time

# Example: Tracking AI agent calls
def my_ai_agent_function(agent_type: str):
    start_time = time.time()
    try:
        # Your AI agent logic here
        result = process_with_ai()

        # Record successful call
        increment_agent_calls(agent_type, "success")
        return result

    except Exception as e:
        # Record failed call
        increment_agent_calls(agent_type, "error")
        raise
    finally:
        # Record duration
        duration = time.time() - start_time
        observe_agent_duration(agent_type, duration)

# Example: Using tracing context manager
def complex_operation():
    with trace_operation("complex_operation", user_id="123", operation_type="analysis"):
        # Your complex logic here
        pass

# Example: Database operation tracking
def save_to_database(collection_name: str, data: dict):
    increment_database_queries("insert", collection_name)
    # Your database save logic here
```

## Quick Setup with Docker Compose

The easiest way to set up the complete monitoring stack (Jaeger + Grafana + Prometheus) is using Docker Compose:

```bash
# Navigate to the BE directory
cd BE

# Start the monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Check if all services are running
docker-compose -f docker-compose.monitoring.yml ps
```

This will start:

- **Jaeger** on http://localhost:16686 (Distributed Tracing UI)
- **Grafana** on http://localhost:3030 (Visualization Dashboard)
- **Prometheus** on http://localhost:9090 (Metrics Collection)
- **Node Exporter** on http://localhost:9100 (System Metrics)
- **OpenTelemetry Collector** on ports 4317/4318 (Optional OTLP endpoint)

### Default Credentials

- **Grafana**: admin / admin123

## Setting Up External Systems Manually

### Prometheus Server

The included `monitoring/prometheus.yml` is configured to scrape your application. Run with Docker:

```bash
docker run -d -p 9090:9090 -v ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
```

### Jaeger for Distributed Tracing

Run Jaeger all-in-one:

```bash
docker run -d -p 16686:16686 -p 14268:14268 jaegertracing/all-in-one:latest
```

Access Jaeger UI at http://localhost:16686

### Grafana for Visualization

Run Grafana with pre-configured dashboards:

```bash
docker run -d -p 3030:3000 \
  -v ./monitoring/grafana/provisioning:/etc/grafana/provisioning \
  -v ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards \
  -e GF_SECURITY_ADMIN_PASSWORD=admin123 \
  grafana/grafana
```

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set environment variables in your `.env` file (enable Jaeger):

```bash
ENABLE_JAEGER=true
ENABLE_PROMETHEUS=true
```

3. Start the monitoring stack:

```bash
docker-compose -f docker-compose.monitoring.yml up -d
```

4. Start the application:

```bash
python app.py
```

5. Check endpoints:
   - **Application Health**: http://localhost:7860/health
   - **Application Metrics**: http://localhost:7860/metrics
   - **API Docs**: http://localhost:7860/docs
   - **Jaeger UI**: http://localhost:16686
   - **Grafana Dashboards**: http://localhost:3030 (admin/admin123)
   - **Prometheus**: http://localhost:9090
   - **Node Exporter (System Metrics)**: http://localhost:9100

## Using the Monitoring Tools

### Grafana Dashboards

After starting Grafana, you'll have access to:

1. **AI FTES Backend Monitoring Dashboard**

   - Request rate and active connections
   - Request duration percentiles (95th, 50th)
   - AI agent call rates and durations
   - Database operation rates

2. **System Monitoring Dashboard**
   - CPU usage and load averages
   - Memory usage and availability
   - Disk usage and I/O statistics
   - Network traffic monitoring
   - Filesystem usage breakdown

The dashboards will automatically populate with data as you use your application and as the system operates.

### Jaeger Distributed Tracing

Access Jaeger at http://localhost:16686 to:

- View request traces across your application
- Analyze AI agent execution times
- Debug performance bottlenecks
- Track errors in your request flow

Search for traces by:

- Service: `ai-ftes-backend`
- Operation: Look for your agent functions like `collection_info_agent`, `create_prompt`, etc.

### Prometheus Query Examples

Access Prometheus at http://localhost:9090 and try these queries:

```promql
# Request rate per second
rate(fastapi_requests_total[5m])

# 95th percentile response time
histogram_quantile(0.95, rate(fastapi_request_duration_seconds_bucket[5m]))

# AI agent error rate
rate(ai_agent_calls_total{status="error"}[5m])

# Database operations by collection
sum by (collection) (rate(database_queries_total[5m]))

# System CPU usage percentage
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage percentage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Disk usage percentage for root filesystem
100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})

# Network traffic rate
rate(node_network_receive_bytes_total{device!="lo"}[5m])
```

## Monitoring Best Practices

1. **Use meaningful labels** for metrics
2. **Don't create too many unique label combinations** (high cardinality)
3. **Use histogram for timing measurements**
4. **Use counter for counting events**
5. **Use gauge for current state values**
6. **Add tracing to critical business operations**
7. **Monitor error rates and latency**

## Troubleshooting

### Common Issues

1. **Import errors**: Make sure all monitoring dependencies are installed
2. **Metrics not appearing**: Check if ENABLE_PROMETHEUS=true in environment
3. **Traces not showing**: Verify Jaeger/OTLP endpoints are correct and accessible
4. **High memory usage**: Check for high cardinality metrics (too many unique labels)

### Debug Commands

```bash
# Check if metrics endpoint is working
curl http://localhost:3002/metrics

# Check health endpoint
curl http://localhost:3002/health

# View application logs for monitoring setup
tail -f app.log | grep -i "monitoring\|prometheus\|opentelemetry"
```
