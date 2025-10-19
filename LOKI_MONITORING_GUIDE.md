# AI FTES - Loki Monitoring Guide

## Overview

This guide explains how to use Loki for log aggregation and monitoring in the AI FTES project. Loki is integrated with Grafana for visualization and Promtail for log collection.

## Architecture

```
Application Logs → Loki Handler → Loki → Grafana Dashboard
File Logs → Promtail → Loki → Grafana Dashboard
```

## Setup Instructions

### 1. Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 2. Start Monitoring Stack

```bash
# Make the script executable
chmod +x start_monitoring.sh

# Start monitoring services
./start_monitoring.sh
```

### 3. Configure Environment Variables (Optional)

```bash
# Set custom Loki URL
export LOKI_URL="http://localhost:3100/loki/api/v1/push"

# Set environment
export ENVIRONMENT="production"

# Set hostname
export HOSTNAME="ai-ftes-server"
```

## Services

### Loki (Port 3100)
- **Purpose**: Log aggregation and storage
- **URL**: http://localhost:3100
- **Config**: `monitoring/loki-config.yml/loki-config.yml`

### Promtail (Port 9080)
- **Purpose**: Log collection from files
- **Config**: `monitoring/promtail-config.yml/promtail-config.yml`
- **Collects logs from**:
  - `/var/log/*log` (system logs)
  - `/app/logs/*.log` (application logs)
  - Docker container logs

### Grafana (Port 3030)
- **Purpose**: Log visualization and dashboards
- **URL**: http://localhost:3030
- **Login**: admin/admin123
- **Dashboards**: AI FTES - Loki Logs Dashboard

## Using Custom Logger

### Basic Usage

```python
from src.utils.logger import logger

# Log messages
logger.info("Application started")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")
```

### Custom Logger for Specific Components

```python
from src.utils.logger import custom_logger

# Create custom logger
my_logger = custom_logger("MY_COMPONENT")

# Use it
my_logger.info("Component initialized")
```

## Log Destinations

1. **Console**: Colored output with custom formatting
2. **File**: Saved to `logs/` directory with date-based naming
3. **Loki**: Sent to Loki for aggregation and Grafana visualization

## Grafana Dashboard Features

### 1. Log Rate by Application
- Shows log volume per application over time
- Useful for identifying high-traffic components

### 2. Log Rate by Level
- Displays log volume by severity level (INFO, WARNING, ERROR, CRITICAL)
- Helps identify error patterns

### 3. Application Logs Table
- Real-time log viewer with filtering capabilities
- Sortable by timestamp, level, and application

### 4. Log Distribution by Level
- Pie chart showing log distribution by severity
- Updated every hour

### 5. Error Count
- Shows total error count in the last hour
- Quick indicator of system health

## Querying Logs in Grafana

### Basic Queries

```logql
# All logs from a specific application
{application="SCHEDULE AI"}

# Error logs only
{application="SCHEDULE AI"} |= "ERROR"

# Logs from specific component
{application="MY_COMPONENT"}

# Logs with specific text
{application=~".*"} |= "database connection"
```

### Advanced Queries

```logql
# Error rate per minute
sum(rate({application=~".*"} |= "ERROR" [1m]))

# Log count by level
sum by (level) (count_over_time({application=~".*"} [1h]))

# Specific time range
{application="SCHEDULE AI"} |= "ERROR" | json | level="ERROR"
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOKI_URL` | `http://localhost:3100/loki/api/v1/push` | Loki push endpoint |
| `ENVIRONMENT` | `development` | Environment tag for logs |
| `HOSTNAME` | `localhost` | Hostname tag for logs |

## File Structure

```
BE/
├── monitoring/
│   ├── loki-config.yml/
│   │   └── loki-config.yml
│   ├── promtail-config.yml/
│   │   └── promtail-config.yml
│   └── grafana/
│       ├── dashboards/
│       │   └── loki-logs-dashboard.json
│       └── provisioning/
│           └── datasources/
│               └── datasources.yml
├── docker-compose.monitoring.yml
├── start_monitoring.sh
└── src/utils/logger.py
```

## Troubleshooting

### Loki Handler Issues

1. **Connection Error**: Check if Loki is running
```bash
curl http://localhost:3100/ready
```

2. **Logs Not Appearing**: Verify Loki URL and network connectivity
```bash
# Check Loki logs
docker logs loki
```

3. **Permission Issues**: Ensure log directory has proper permissions
```bash
chmod 755 logs/
```

### Grafana Issues

1. **Dashboard Not Loading**: Check datasource configuration
2. **No Data**: Verify Loki datasource connection
3. **Query Errors**: Check LogQL syntax

### Common LogQL Patterns

```logql
# Find specific errors
{application="SCHEDULE AI"} |= "database" |= "error"

# Exclude debug logs
{application="SCHEDULE AI"} != "DEBUG"

# Extract JSON fields
{application="SCHEDULE AI"} | json | level="ERROR"

# Rate queries
rate({application="SCHEDULE AI"}[5m])
```

## Best Practices

1. **Use Structured Logging**: Include relevant context in log messages
2. **Appropriate Log Levels**: Use INFO for general info, ERROR for actual errors
3. **Add Labels**: Use meaningful labels for better filtering
4. **Monitor Error Rates**: Set up alerts for high error rates
5. **Regular Cleanup**: Configure log retention policies

## Monitoring Commands

```bash
# Start monitoring
./start_monitoring.sh

# Stop monitoring
docker-compose -f docker-compose.monitoring.yml down

# View logs
docker-compose -f docker-compose.monitoring.yml logs -f

# Restart specific service
docker-compose -f docker-compose.monitoring.yml restart loki
```

## Performance Considerations

- **Log Volume**: Monitor log ingestion rate
- **Storage**: Configure appropriate retention policies
- **Query Performance**: Use specific labels in queries
- **Resource Usage**: Monitor Loki and Grafana resource consumption

## Integration with Application

The custom logger automatically:
- Sends logs to Loki (if available)
- Writes to local files
- Displays in console with colors
- Includes timezone information (Asia/Ho_Chi_Minh)
- Adds application, environment, and host tags

This provides comprehensive observability for your AI FTES application with minimal configuration required. 