"""
Monitoring and observability configuration for Prometheus and OpenTelemetry
"""

import os
import logging
from typing import Optional

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from fastapi import FastAPI, Response
from fastapi.responses import Response as FastAPIResponse

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader

logger = logging.getLogger(__name__)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "fastapi_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_DURATION = Histogram(
    "fastapi_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
)

ACTIVE_CONNECTIONS = Gauge("fastapi_active_connections", "Number of active connections")

AGENT_CALLS = Counter(
    "ai_agent_calls_total", "Total number of AI agent calls", ["agent_type", "status"]
)

AGENT_DURATION = Histogram(
    "ai_agent_duration_seconds", "AI agent call duration in seconds", ["agent_type"]
)

DATABASE_QUERIES = Counter(
    "database_queries_total",
    "Total number of database queries",
    ["operation", "collection"],
)


class MonitoringConfig:
    """Configuration class for monitoring setup"""

    def __init__(self):
        self.service_name = os.getenv("SERVICE_NAME", "ai-ftes-backend")
        self.service_version = os.getenv("SERVICE_VERSION", "1.0.0")
        self.environment = os.getenv("ENVIRONMENT", "development")

        # OpenTelemetry configuration
        self.otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
        self.jaeger_endpoint = os.getenv(
            "JAEGER_ENDPOINT", "http://localhost:14268/api/traces"
        )
        self.enable_jaeger = os.getenv("ENABLE_JAEGER", "false").lower() == "true"
        self.enable_otlp = os.getenv("ENABLE_OTLP", "false").lower() == "true"

        # Prometheus configuration
        self.enable_prometheus = (
            os.getenv("ENABLE_PROMETHEUS", "true").lower() == "true"
        )


def setup_opentelemetry(config: MonitoringConfig) -> None:
    """Configure OpenTelemetry tracing and metrics"""

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": config.service_name,
            "service.version": config.service_version,
            "deployment.environment": config.environment,
        }
    )

    # Setup tracing
    trace_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(trace_provider)

    # Configure exporters based on environment variables
    if config.enable_jaeger:
        jaeger_exporter = JaegerExporter(
            collector_endpoint=config.jaeger_endpoint,
        )
        trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
        logger.info(f"Jaeger exporter configured: {config.jaeger_endpoint}")

    if config.enable_otlp:
        otlp_exporter = OTLPSpanExporter(
            endpoint=config.otlp_endpoint,
            insecure=True,
        )
        trace_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OTLP exporter configured: {config.otlp_endpoint}")

    # Setup metrics if Prometheus is enabled
    if config.enable_prometheus:
        metric_reader = PrometheusMetricReader()
        metric_provider = MeterProvider(
            resource=resource, metric_readers=[metric_reader]
        )
        metrics.set_meter_provider(metric_provider)
        logger.info("Prometheus metrics configured")


def instrument_app(app: FastAPI, config: MonitoringConfig) -> None:
    """Add instrumentation to FastAPI app"""

    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=trace.get_tracer_provider(),
        excluded_urls="/health,/metrics,/docs,/redoc,/openapi.json",
    )

    # Auto-instrument requests library
    RequestsInstrumentor().instrument()

    # Auto-instrument pymongo
    PymongoInstrumentor().instrument()

    logger.info("FastAPI app instrumented with OpenTelemetry")


def setup_prometheus_metrics(app: FastAPI) -> None:
    """Setup Prometheus metrics endpoint and middleware"""

    @app.get("/metrics")
    async def get_metrics():
        """Prometheus metrics endpoint"""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "service": "ai-ftes-backend"}

    logger.info("Prometheus metrics endpoint configured at /metrics")


def setup_monitoring(app: FastAPI) -> MonitoringConfig:
    """Complete monitoring setup for the FastAPI app"""

    config = MonitoringConfig()

    # Setup OpenTelemetry
    setup_opentelemetry(config)

    # Instrument the app
    instrument_app(app, config)

    # Setup Prometheus metrics
    if config.enable_prometheus:
        setup_prometheus_metrics(app)

    logger.info("Monitoring setup completed")
    return config


# Utility functions for custom metrics
def increment_request_count(method: str, endpoint: str, status_code: int):
    """Increment request counter"""
    REQUEST_COUNT.labels(
        method=method, endpoint=endpoint, status_code=str(status_code)
    ).inc()


def observe_request_duration(method: str, endpoint: str, duration: float):
    """Record request duration"""
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def increment_agent_calls(agent_type: str, status: str = "success"):
    """Increment AI agent calls counter"""
    AGENT_CALLS.labels(agent_type=agent_type, status=status).inc()


def observe_agent_duration(agent_type: str, duration: float):
    """Record AI agent call duration"""
    AGENT_DURATION.labels(agent_type=agent_type).observe(duration)


def increment_database_queries(operation: str, collection: str):
    """Increment database queries counter"""
    DATABASE_QUERIES.labels(operation=operation, collection=collection).inc()


# Context managers for easy tracing
class trace_operation:
    """Context manager for tracing operations"""

    def __init__(self, operation_name: str, **attributes):
        self.operation_name = operation_name
        self.attributes = attributes
        self.span = None

    def __enter__(self):
        tracer = trace.get_tracer(__name__)
        self.span = tracer.start_span(self.operation_name)
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc_val)))
        self.span.end()
