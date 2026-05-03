"""
Simplified main application entry point - non-interactive startup.
"""

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from controller import (
    alert_controller,
    health_controller,
    monitoring_controller,
    prediction_controller,
    training_controller
)
from middleware.error_handler import register_exception_handlers
from middleware.logging_middleware import (
    LoggingMiddleware,
    PerformanceMiddleware,
    RequestIDMiddleware
)
from util.config import settings
from util.helpers import ensure_directory_exists
from util.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-based real-time KPI monitoring and prediction system",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers
)

# Add custom middleware
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(PerformanceMiddleware, slow_request_threshold=2.0)

# Register exception handlers
register_exception_handlers(app)

# Ensure required directories exist
ensure_directory_exists(settings.model_storage_path)
ensure_directory_exists(settings.dataset_storage_path)
ensure_directory_exists("logs")
ensure_directory_exists("static")

# Mount static files for UI
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

# Include routers
app.include_router(health_controller.router)
app.include_router(training_controller.router)
app.include_router(prediction_controller.router)
app.include_router(alert_controller.router)
app.include_router(monitoring_controller.router)

logger.info("All routers registered")


@app.get("/")
async def root():
    """Root endpoint - redirect to docs."""
    return RedirectResponse(url="/docs")


@app.get("/info")
async def info():
    """Application information endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "debug": settings.debug,
        "model_type": settings.model_type,
        "features": {
            "real_time_monitoring": True,
            "auto_training": True,
            "anomaly_detection": True,
            "multi_kpi_support": True,
            "web_dashboard": True
        },
        "api_endpoints": {
            "health": "/health",
            "monitoring": "/api/v1/monitoring",
            "train": "/api/v1/train",
            "predict": "/api/v1/predict",
            "alerts": "/api/v1/alerts"
        }
    }


@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"API documentation: http://{settings.host}:{settings.port}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    logger.info("Shutting down application")


def main():
    """Main entry point for running the application."""
    import uvicorn
    
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    
    print("\n" + "="*80)
    print(f"🚀 {settings.app_name} v{settings.app_version}")
    print("="*80)
    print(f"📚 API Documentation: http://{settings.host}:{settings.port}/docs")
    print(f"🏥 Health Check: http://{settings.host}:{settings.port}/health")
    print(f"📊 Monitoring API: http://{settings.host}:{settings.port}/api/v1/monitoring")
    print("="*80 + "\n")
    
    uvicorn.run(
        "main_simple:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
