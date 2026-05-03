"""
Main application entry point for KPI Prediction System with real-time monitoring.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from controller import (
    alert_controller,
    health_controller,
    monitoring_controller,
    prediction_controller,
    training_controller
)
from middleware.auth_middleware import APIKeyMiddleware
from middleware.error_handler import register_exception_handlers
from middleware.logging_middleware import (
    LoggingMiddleware,
    PerformanceMiddleware,
    RequestIDMiddleware
)
from services.startup_wizard import StartupWizard
from util.config import settings
from util.helpers import ensure_directory_exists
from util.logger import app_logger


# Global monitoring service
monitoring_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Args:
        app: FastAPI application instance
    """
    global monitoring_service
    
    # Startup
    app_logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    app_logger.info(f"Environment: {settings.environment}")
    app_logger.info(f"Debug mode: {settings.debug}")
    
    # Ensure required directories exist
    ensure_directory_exists(settings.model_storage_path)
    ensure_directory_exists(settings.dataset_storage_path)
    ensure_directory_exists("logs")
    ensure_directory_exists("static")
    
    # Run startup wizard
    app_logger.info("Running startup wizard...")
    wizard = StartupWizard()
    monitoring_service = wizard.run()
    
    # Set monitoring service in controller
    monitoring_controller.set_monitoring_service(monitoring_service)
    
    # Ask if user wants to start monitoring immediately
    print("\n" + "="*80)
    start_now = input("Start monitoring now? [Y/n]: ").strip().lower()
    
    if start_now in ['', 'y', 'yes']:
        monitoring_service.start_monitoring()
        app_logger.info("Monitoring started automatically")
        print("✅ Monitoring started!")
    else:
        print("ℹ️  Monitoring not started. Use the UI or API to start when ready.")
    
    print("="*80)
    print(f"\n🌐 Access the dashboard at: http://{settings.host}:{settings.port}")
    print(f"📚 API documentation at: http://{settings.host}:{settings.port}/docs")
    print("="*80 + "\n")
    
    app_logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    app_logger.info("Shutting down application")
    
    if monitoring_service:
        app_logger.info("Stopping all monitors...")
        monitoring_service.stop_monitoring()
    
    app_logger.info("Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-based real-time KPI monitoring and prediction system",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers
)

# Add custom middleware (order matters - first added is outermost)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(PerformanceMiddleware, slow_request_threshold=2.0)

# Add authentication middleware (optional)
if settings.api_key_enabled:
    app.add_middleware(APIKeyMiddleware)
    app_logger.info("API key authentication enabled")

# Register exception handlers
register_exception_handlers(app)

# Mount static files for UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(health_controller.router)
app.include_router(training_controller.router)
app.include_router(prediction_controller.router)
app.include_router(alert_controller.router)
app.include_router(monitoring_controller.router)

app_logger.info("All routers registered")


@app.get("/")
async def root():
    """
    Root endpoint - redirect to dashboard.
    
    Returns:
        dict: Redirect information
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")


@app.get("/info")
async def info():
    """
    Application information endpoint.
    
    Returns:
        dict: Application information
    """
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
            "dashboard": "/",
            "health": "/health",
            "monitoring": "/api/v1/monitoring",
            "train": "/api/v1/train",
            "predict": "/api/v1/predict",
            "compare": "/api/v1/compare",
            "alerts": "/api/v1/alerts",
            "models": "/api/v1/models"
        }
    }


def main():
    """Main entry point for running the application."""
    import uvicorn
    
    app_logger.info(
        f"Starting server on {settings.host}:{settings.port}"
    )
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()