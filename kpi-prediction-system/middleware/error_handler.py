"""
Global error handler middleware for FastAPI.
"""

import traceback
from typing import Union

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from data.schema import ErrorResponse
from util.logger import get_logger

logger = get_logger(__name__)


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException
) -> JSONResponse:
    """
    Handle HTTP exceptions.
    
    Args:
        request: HTTP request
        exc: HTTP exception
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    logger.warning(
        f"HTTP exception: {exc.status_code} - {exc.detail}",
        extra={
            'correlation_id': correlation_id,
            'status_code': exc.status_code,
            'path': request.url.path,
            'method': request.method
        }
    )
    
    error_response = ErrorResponse(
        error=exc.detail,
        detail=str(exc.detail),
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json'),
        headers={'X-Correlation-ID': correlation_id} if correlation_id else {}
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """
    Handle validation errors.
    
    Args:
        request: HTTP request
        exc: Validation exception
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        field = '.'.join(str(loc) for loc in error['loc'])
        message = error['msg']
        errors.append(f"{field}: {message}")
    
    error_detail = "; ".join(errors)
    
    logger.warning(
        f"Validation error: {error_detail}",
        extra={
            'correlation_id': correlation_id,
            'path': request.url.path,
            'method': request.method,
            'errors': exc.errors()
        }
    )
    
    error_response = ErrorResponse(
        error="Validation Error",
        detail=error_detail,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(mode='json'),
        headers={'X-Correlation-ID': correlation_id} if correlation_id else {}
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle general exceptions.
    
    Args:
        request: HTTP request
        exc: Exception
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    # Log full traceback
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            'correlation_id': correlation_id,
            'path': request.url.path,
            'method': request.method,
            'exception_type': type(exc).__name__
        },
        exc_info=True
    )
    
    # Don't expose internal errors in production
    error_message = "Internal Server Error"
    error_detail = str(exc)
    
    # In development, include more details
    from util.config import settings
    if settings.debug:
        error_detail = f"{type(exc).__name__}: {str(exc)}\n\n{traceback.format_exc()}"
    
    error_response = ErrorResponse(
        error=error_message,
        detail=error_detail,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(mode='json'),
        headers={'X-Correlation-ID': correlation_id} if correlation_id else {}
    )


async def value_error_handler(
    request: Request,
    exc: ValueError
) -> JSONResponse:
    """
    Handle ValueError exceptions.
    
    Args:
        request: HTTP request
        exc: ValueError exception
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    logger.warning(
        f"Value error: {str(exc)}",
        extra={
            'correlation_id': correlation_id,
            'path': request.url.path,
            'method': request.method
        }
    )
    
    error_response = ErrorResponse(
        error="Invalid Value",
        detail=str(exc),
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.model_dump(mode='json'),
        headers={'X-Correlation-ID': correlation_id} if correlation_id else {}
    )


async def file_not_found_handler(
    request: Request,
    exc: FileNotFoundError
) -> JSONResponse:
    """
    Handle FileNotFoundError exceptions.
    
    Args:
        request: HTTP request
        exc: FileNotFoundError exception
        
    Returns:
        JSONResponse: Error response
    """
    correlation_id = getattr(request.state, 'correlation_id', None)
    
    logger.warning(
        f"File not found: {str(exc)}",
        extra={
            'correlation_id': correlation_id,
            'path': request.url.path,
            'method': request.method
        }
    )
    
    error_response = ErrorResponse(
        error="Resource Not Found",
        detail=str(exc),
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_response.model_dump(mode='json'),
        headers={'X-Correlation-ID': correlation_id} if correlation_id else {}
    )


def register_exception_handlers(app) -> None:
    """
    Register all exception handlers with FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(FileNotFoundError, file_not_found_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers registered")
