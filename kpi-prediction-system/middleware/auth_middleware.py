"""
Authentication middleware (optional).
"""

from typing import Callable, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from data.schema import ErrorResponse
from util.config import settings
from util.logger import get_logger

logger = get_logger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware for API key authentication."""
    
    def __init__(
        self,
        app: ASGIApp,
        api_key: Optional[str] = None,
        header_name: str = "X-API-Key"
    ):
        """
        Initialize API key middleware.
        
        Args:
            app: ASGI application
            api_key: Expected API key
            header_name: Header name for API key
        """
        super().__init__(app)
        self.api_key = api_key or settings.api_key
        self.header_name = header_name
        self.enabled = settings.api_key_enabled
        self.logger = logger
        
        # Paths that don't require authentication
        self.public_paths = [
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> JSONResponse:
        """
        Validate API key for protected endpoints.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            Response: HTTP response
        """
        # Skip authentication if disabled
        if not self.enabled:
            return await call_next(request)
        
        # Skip authentication for public paths
        if request.url.path in self.public_paths:
            return await call_next(request)
        
        # Check for API key in header
        provided_key = request.headers.get(self.header_name)
        
        if not provided_key:
            self.logger.warning(
                f"Missing API key for {request.url.path}",
                extra={
                    'path': request.url.path,
                    'method': request.method,
                    'client_host': request.client.host if request.client else None
                }
            )
            
            error_response = ErrorResponse(
                error="Authentication Required",
                detail=f"API key required in {self.header_name} header",
                path=request.url.path
            )
            
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content=error_response.model_dump(),
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        # Validate API key
        if provided_key != self.api_key:
            self.logger.warning(
                f"Invalid API key for {request.url.path}",
                extra={
                    'path': request.url.path,
                    'method': request.method,
                    'client_host': request.client.host if request.client else None
                }
            )
            
            error_response = ErrorResponse(
                error="Authentication Failed",
                detail="Invalid API key",
                path=request.url.path
            )
            
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=error_response.model_dump()
            )
        
        # API key is valid, proceed
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware."""
    
    def __init__(
        self,
        app: ASGIApp,
        max_requests: int = 100,
        window_seconds: int = 60
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            app: ASGI application
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_counts = {}
        self.logger = logger
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> JSONResponse:
        """
        Check rate limit for client.
        
        Args:
            request: HTTP request
            call_next: Next middleware/handler
            
        Returns:
            Response: HTTP response
        """
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"
        
        # Simple in-memory rate limiting (not production-ready)
        # In production, use Redis or similar
        import time
        current_time = time.time()
        
        if client_id not in self.request_counts:
            self.request_counts[client_id] = []
        
        # Remove old requests outside window
        self.request_counts[client_id] = [
            req_time for req_time in self.request_counts[client_id]
            if current_time - req_time < self.window_seconds
        ]
        
        # Check if limit exceeded
        if len(self.request_counts[client_id]) >= self.max_requests:
            self.logger.warning(
                f"Rate limit exceeded for {client_id}",
                extra={
                    'client_id': client_id,
                    'path': request.url.path,
                    'requests_in_window': len(self.request_counts[client_id])
                }
            )
            
            error_response = ErrorResponse(
                error="Rate Limit Exceeded",
                detail=f"Maximum {self.max_requests} requests per {self.window_seconds} seconds",
                path=request.url.path
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=error_response.model_dump(),
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(current_time + self.window_seconds))
                }
            )
        
        # Add current request
        self.request_counts[client_id].append(current_time)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.max_requests - len(self.request_counts[client_id])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response
