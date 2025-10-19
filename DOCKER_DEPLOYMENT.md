# Docker Deployment Guide

Hướng dẫn triển khai AI FTES Backend với Docker và monitoring stack hoàn chỉnh.

## 🚀 Quick Start

### 1. Chọn deployment mode (Khuyến nghị):

```bash
cd BE
./start_monitoring.sh
```

Script sẽ cho phép bạn chọn:

- **Option 1**: 📊 Monitoring Only (Backend chạy riêng, monitoring scrape qua host)
- **Option 2**: 🔧 Standalone Backend (chỉ chạy backend, không có monitoring)
- **Option 3**: 🔍 Full Monitoring (backend + monitoring cùng network)
- **Option 4**: 🛑 Stop tất cả services

### 2. Hoặc start trực tiếp:

**Backend riêng biệt:**

```bash
./start_backend_standalone.sh
```

**Monitoring Only (scrape backend từ host):**

```bash
./start_monitoring_only.sh
```

**Full Stack (backend + monitoring cùng network):**

```bash
./start_full_stack.sh
```

### 3. Chỉ build backend:

```bash
./build_backend.sh
```

## 💡 Usage Examples

### Scenario 1: Backend riêng + Monitoring riêng (Khuyến nghị cho VPS)

```bash
# Terminal 1: Start backend standalone
./start_backend_standalone.sh

# Terminal 2: Start monitoring
./start_monitoring_only.sh
```

### Scenario 2: Chỉ cần backend, không monitoring

```bash
./start_backend_standalone.sh
```

### Scenario 3: All-in-one với shared network

```bash
./start_full_stack.sh
```

### Scenario 4: Interactive selector

```bash
./start_monitoring.sh
# Chọn mode theo nhu cầu
```

## 🔧 Các thay đổi đã fix lỗi Jaeger Connection Refused:

### 1. **Health Check cho Jaeger**

- Thêm health check để đảm bảo Jaeger sẵn sàng trước khi backend start
- Backend chỉ start khi Jaeger container healthy

### 2. **Wait Script**

- `wait-for-jaeger.sh`: Script đợi Jaeger sẵn sàng
- Timeout 60s với graceful fallback
- Backend vẫn start được nếu Jaeger không ready

### 3. **Dependencies và Startup Order**

```yaml
depends_on:
  jaeger:
    condition: service_healthy
  prometheus:
    condition: service_started
```

### 4. **Improved Container Command**

```yaml
command:
  [
    "./wait-for-jaeger.sh",
    "uvicorn",
    "app:app",
    "--host",
    "0.0.0.0",
    "--port",
    "7860",
  ]
```

### 5. **Environment Variable Control**

Backend có thể tự động phát hiện mode thông qua environment variables:

- `ENABLE_JAEGER=true`: Full monitoring mode với Jaeger
- `ENABLE_JAEGER=false`: Prometheus-only mode
- Wait script tự động skip Jaeger nếu `ENABLE_JAEGER=false`

## 🎛️ Deployment Modes

### 📊 Monitoring Only Mode

Monitoring services scrape backend từ host (backend chạy riêng):

- ❌ Backend (chạy riêng với `./start_backend_standalone.sh`)
- ✅ Prometheus (scrape qua `host.docker.internal:7860`)
- ✅ Grafana (dashboards)
- ✅ Node Exporter (system metrics)
- ❌ Jaeger - **DISABLED**

### 🔧 Standalone Backend Mode

Chỉ chạy backend, không có monitoring:

- ✅ Backend Application (standalone container)
- ❌ Prometheus - **DISABLED**
- ❌ Grafana - **DISABLED**
- ❌ Node Exporter - **DISABLED**
- ❌ Jaeger - **DISABLED**

### 🔍 Full Monitoring Mode

Backend và monitoring cùng chạy trong shared network:

- ✅ Backend Application (trong docker-compose)
- ✅ Prometheus + Grafana + Node Exporter
- ✅ Jaeger (distributed tracing)
- ✅ OpenTelemetry Collector

## 📋 Services

| Service                     | Port      | URL                    | Monitoring Only | Standalone Backend | Full Mode | Mô tả                       |
| --------------------------- | --------- | ---------------------- | --------------- | ------------------ | --------- | --------------------------- |
| **AI FTES Backend**         | 7860      | http://localhost:7860  | ⚠️ (riêng)      | ✅                 | ✅        | Main application            |
| **Grafana**                 | 3030      | http://localhost:3030  | ✅              | ❌                 | ✅        | Dashboards (admin/admin123) |
| **Prometheus**              | 9090      | http://localhost:9090  | ✅              | ❌                 | ✅        | Metrics collection          |
| **Node Exporter**           | 9100      | http://localhost:9100  | ✅              | ❌                 | ✅        | System metrics              |
| **Jaeger**                  | 16686     | http://localhost:16686 | ❌              | ❌                 | ✅        | Distributed tracing         |
| **OpenTelemetry Collector** | 4317/4318 | -                      | ❌              | ❌                 | ✅        | Trace collection            |

**Chú thích:**

- ⚠️ (riêng): Backend chạy riêng biệt, phải start manually với `./start_backend_standalone.sh`

## 🔍 Troubleshooting

### Kiểm tra container status:

```bash
docker-compose -f docker-compose.monitoring.yml ps
```

### Xem logs:

```bash
# Backend logs
docker-compose -f docker-compose.monitoring.yml logs ai-ftes-backend

# Jaeger logs
docker-compose -f docker-compose.monitoring.yml logs jaeger

# Tất cả logs
docker-compose -f docker-compose.monitoring.yml logs
```

### Test connections:

```bash
# Test backend health
curl http://localhost:7860/health

# Test backend metrics
curl http://localhost:7860/metrics

# Test Jaeger
curl http://localhost:16686/

# Test Grafana
curl http://localhost:3030/api/health
```

## 🛑 Stop Services

```bash
docker-compose -f docker-compose.monitoring.yml down
```

Xóa volumes (cẩn thận - sẽ mất data):

```bash
docker-compose -f docker-compose.monitoring.yml down -v
```

## 📝 Configuration Files

### Docker Compose Files:

- **`docker-compose.monitoring.yml`**: Full monitoring stack (with Jaeger)
- **`docker-compose.prometheus-only.yml`**: Prometheus-only stack

### Prometheus Configurations:

- **`monitoring/prometheus.yml`**: Full stack Prometheus config (with Jaeger scraping)
- **`monitoring/prometheus-only.yml`**: Prometheus-only config (no Jaeger)

### Scripts:

- **`start_monitoring.sh`**: Interactive deployment mode selector (Khuyến nghị)
- **`start_backend_standalone.sh`**: Start backend riêng biệt
- **`start_monitoring_only.sh`**: Start monitoring services only (scrape từ host)
- **`start_full_stack.sh`**: Start full monitoring stack (shared network)
- **`build_backend.sh`**: Build backend Docker image
- **`wait-for-jaeger.sh`**: Smart startup script (handles Jaeger on/off)

### Other Files:

- **`Dockerfile`**: Backend container definition
- **`DOCKER_DEPLOYMENT.md`**: This documentation file

## 🔄 Updates

Nếu có thay đổi code:

1. Rebuild image: `./build_backend.sh`
2. Restart stack: `./start_full_stack.sh`

Hoặc restart chỉ backend:

```bash
docker-compose -f docker-compose.monitoring.yml restart ai-ftes-backend
```

## 🌟 Features

✅ **Flexible Deployment Modes**

- **Monitoring Only**: Monitoring services scrape backend từ host (tách biệt hoàn toàn)
- **Standalone Backend**: Chỉ chạy backend, không monitoring
- **Full Monitoring**: Backend + monitoring trong shared network
- Interactive deployment selector
- Easy switching between architectures

✅ **Fixed Jaeger Connection Issues**

- Graceful startup với wait mechanism
- Health checks đảm bảo dependencies ready
- Automatic fallback khi Jaeger disabled
- Smart environment variable detection

✅ **Flexible Network Architecture**

- **Monitoring Only**: Backend chạy trên host, monitoring trong Docker network
- **Full Mode**: Tất cả containers trong shared network với service discovery
- **Standalone**: Backend chạy riêng biệt, không phụ thuộc monitoring
- Hỗ trợ `host.docker.internal` cho cross-network communication

✅ **Production Ready**

- Restart policies
- Health monitoring
- Proper dependency management
- Comprehensive logging
- Resource-efficient configurations
