"""
Logging middleware for request/response logging.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from util.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    def __init__(self, app: ASGIApp):
        """
        Initialize logging middleware.
        
        Args:
            app: ASGI application
        """
        super().__init__(app)
        self.logger = logger
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request and log details.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            Response: HTTP response
        """
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        
        # Log request
        start_time = time.time()
        
        self.logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                'correlation_id': correlation_id,
                'method': request.method,
                'path': request.url.path,
                'query_params': str(request.query_params),
                'client_host': request.client.host if request.client else None
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            self.logger.info(
                f"Request completed: {request.method} {request.url.path} - "
                f"Status: {response.status_code} - Duration: {duration:.3f}s",
                extra={
                    'correlation_id': correlation_id,
                    'method': request.method,
                    'path': request.url.path,
                    'status_code': response.status_code,
                    'duration_seconds': round(duration, 3)
                }
            )
            
            # Add correlation ID to response headers
            response.headers['X-Correlation-ID'] = correlation_id
            
            return response
            
        except Exception as e:
            # Calculate duration
            duration = time.time() - start_time
            
            # Log error
            self.logger.error(
                f"Request failed: {request.method} {request.url.path} - "
                f"Error: {str(e)} - Duration: {duration:.3f}s",
                extra={
                    'correlation_id': correlation_id,
                    'method': request.method,
                    'path': request.url.path,
                    'error': str(e),
                    'duration_seconds': round(duration, 3)
                },
                exc_info=True
            )
            
            # Re-raise exception to be handled by error handler
            raise


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests."""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Add request ID to request state.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            Response: HTTP response
        """
        # Generate or use existing request ID
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response
        response.headers['X-Request-ID'] = request_id
        
        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track performance metrics."""
    
    def __init__(self, app: ASGIApp, slow_request_threshold: float = 1.0):
        """
        Initialize performance middleware.
        
        Args:
            app: ASGI application
            slow_request_threshold: Threshold in seconds for slow requests
        """
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold
        self.logger = get_logger(__name__)
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Track request performance.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            Response: HTTP response
        """
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Add performance header
        response.headers['X-Response-Time'] = f"{duration:.3f}s"
        
        # Log slow requests
        if duration > self.slow_request_threshold:
            self.logger.warning(
                f"Slow request detected: {request.method} {request.url.path} - "
                f"Duration: {duration:.3f}s",
                extra={
                    'method': request.method,
                    'path': request.url.path,
                    'duration_seconds': round(duration, 3),
                    'threshold_seconds': self.slow_request_threshold
                }
            )
        
        return response
