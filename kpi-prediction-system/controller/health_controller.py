"""
Health check controller.
"""

import time
from datetime import datetime

from fastapi import APIRouter, Depends

from data.schema import HealthResponse, SystemStats
from services.alert_service import AlertService
from services.model_service import ModelService
from util.config import settings
from util.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])

# Track application start time
app_start_time = time.time()


def get_model_service() -> ModelService:
    """Dependency for model service."""
    return ModelService()


def get_alert_service() -> AlertService:
    """Dependency for alert service."""
    return AlertService()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    model_service: ModelService = Depends(get_model_service),
    alert_service: AlertService = Depends(get_alert_service)
) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        HealthResponse: Health status
    """
    try:
        # Get loaded models count
        models_loaded = len(model_service.loaded_models)
        
        # Get active alerts count
        active_alerts = len(alert_service.get_active_alerts())
        
        # Calculate uptime
        uptime = time.time() - app_start_time
        
        return HealthResponse(
            status="healthy",
            version=settings.app_version,
            uptime_seconds=round(uptime, 2),
            models_loaded=models_loaded,
            active_alerts=active_alerts
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            version=settings.app_version
        )


@router.get("/health/detailed", response_model=SystemStats)
async def detailed_health_check(
    model_service: ModelService = Depends(get_model_service),
    alert_service: AlertService = Depends(get_alert_service)
) -> SystemStats:
    """
    Detailed health check with system statistics.
    
    Returns:
        SystemStats: Detailed system statistics
    """
    try:
        # Get model count
        models = model_service.list_models()
        total_models = len(models)
        
        # Get alert statistics
        alert_stats = alert_service.get_alert_statistics()
        
        # Calculate uptime
        uptime = time.time() - app_start_time
        
        # Get memory usage (optional)
        memory_usage_mb = None
        cpu_usage_percent = None
        
        try:
            import psutil
            process = psutil.Process()
            memory_usage_mb = round(process.memory_info().rss / 1024 / 1024, 2)
            cpu_usage_percent = round(process.cpu_percent(interval=0.1), 2)
        except ImportError:
            pass
        
        return SystemStats(
            total_models=total_models,
            total_predictions_today=0,  # Would need to track this
            total_alerts_today=0,  # Would need to track this
            active_alerts=alert_stats.get('active_alerts', 0),
            system_uptime_seconds=round(uptime, 2),
            memory_usage_mb=memory_usage_mb,
            cpu_usage_percent=cpu_usage_percent
        )
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}", exc_info=True)
        raise


@router.get("/health/ready")
async def readiness_check() -> dict:
    """
    Readiness check for Kubernetes/container orchestration.
    
    Returns:
        dict: Readiness status
    """
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/health/live")
async def liveness_check() -> dict:
    """
    Liveness check for Kubernetes/container orchestration.
    
    Returns:
        dict: Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }
