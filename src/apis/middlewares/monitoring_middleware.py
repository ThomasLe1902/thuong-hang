"""
Monitoring middleware for automatic metrics collection
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.config.monitoring import (
    increment_request_count,
    observe_request_duration,
    ACTIVE_CONNECTIONS
)

logger = logging.getLogger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request metrics automatically"""
    
    def __init__(self, app, excluded_paths: set = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or {
            "/metrics", "/health", "/docs", "/redoc", "/openapi.json"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip monitoring for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Increment active connections
        ACTIVE_CONNECTIONS.inc()
        
        # Record start time
        start_time = time.time()
        
        # Extract request info
        method = request.method
        endpoint = request.url.path
        
        try:
            # Process request
            response = await call_next(request)
            status_code = response.status_code
            
            # Record success metrics
            increment_request_count(method, endpoint, status_code)
            
        except Exception as e:
            # Record error metrics
            status_code = 500
            increment_request_count(method, endpoint, status_code)
            logger.error(f"Request failed: {method} {endpoint} - {str(e)}")
            raise
        
        finally:
            # Record duration and decrement active connections
            duration = time.time() - start_time
            observe_request_duration(method, endpoint, duration)
            ACTIVE_CONNECTIONS.dec()
        
        return response 