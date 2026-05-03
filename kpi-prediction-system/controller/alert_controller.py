"""
Alert controller for alert management endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from data.schema import (
    AlertConfig,
    AlertConfigResponse,
    AlertListResponse,
    ComparisonRequest,
    ComparisonResponse
)
from services.alert_service import AlertService
from util.constants import AlertSeverity
from util.helpers import parse_timestamp
from util.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Alerts"])


def get_alert_service() -> AlertService:
    """Dependency for alert service."""
    return AlertService()


@router.post("/compare", response_model=ComparisonResponse)
async def compare_actual_vs_predicted(
    request: ComparisonRequest,
    alert_service: AlertService = Depends(get_alert_service)
) -> ComparisonResponse:
    """
    Compare actual value vs predicted and trigger alert if needed.
    
    Args:
        request: Comparison request
        alert_service: Alert service instance
        
    Returns:
        ComparisonResponse: Comparison result with alert status
    """
    logger.info(
        f"Comparison request for dataset: {request.dataset_name}, "
        f"actual_value: {request.actual_value}"
    )
    
    try:
        # Parse timestamp if provided
        timestamp = None
        if request.timestamp:
            timestamp = parse_timestamp(request.timestamp)
        
        # Compare and check for alerts
        result = alert_service.compare_and_alert(
            dataset_name=request.dataset_name,
            actual_value=request.actual_value,
            timestamp=timestamp
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"Invalid comparison request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Comparison failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {str(e)}"
        )


@router.get("/alerts", response_model=AlertListResponse)
async def get_alerts(
    dataset_name: Optional[str] = Query(default=None),
    active_only: bool = Query(default=False),
    alert_service: AlertService = Depends(get_alert_service)
) -> AlertListResponse:
    """
    Get alerts with optional filtering.
    
    Args:
        dataset_name: Optional dataset filter
        active_only: Return only active alerts
        alert_service: Alert service instance
        
    Returns:
        AlertListResponse: List of alerts with statistics
    """
    try:
        alerts = alert_service.get_all_alerts(
            dataset_name=dataset_name,
            active_only=active_only
        )
        
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alerts: {str(e)}"
        )


@router.get("/alerts/{alert_id}")
async def get_alert_by_id(
    alert_id: str,
    alert_service: AlertService = Depends(get_alert_service)
) -> dict:
    """
    Get specific alert by ID.
    
    Args:
        alert_id: Alert identifier
        alert_service: Alert service instance
        
    Returns:
        dict: Alert details
    """
    try:
        alert = alert_service.get_alert_by_id(alert_id)
        
        if alert is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert not found: {alert_id}"
            )
        
        return alert.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert: {str(e)}"
        )


@router.get("/alerts/config/{dataset_name}", response_model=AlertConfig)
async def get_alert_config(
    dataset_name: str,
    alert_service: AlertService = Depends(get_alert_service)
) -> AlertConfig:
    """
    Get alert configuration for a dataset.
    
    Args:
        dataset_name: Dataset identifier
        alert_service: Alert service instance
        
    Returns:
        AlertConfig: Alert configuration
    """
    try:
        config = alert_service.get_alert_config(dataset_name)
        return config
        
    except Exception as e:
        logger.error(f"Failed to get alert config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert config: {str(e)}"
        )


@router.put("/alerts/config", response_model=AlertConfigResponse)
async def update_alert_config(
    config: AlertConfig,
    alert_service: AlertService = Depends(get_alert_service)
) -> AlertConfigResponse:
    """
    Update alert configuration for a dataset.
    
    Args:
        config: Alert configuration
        alert_service: Alert service instance
        
    Returns:
        AlertConfigResponse: Updated configuration
    """
    logger.info(f"Updating alert config for dataset: {config.dataset_name}")
    
    try:
        response = alert_service.set_alert_config(
            dataset_name=config.dataset_name,
            upper_threshold_percentage=config.upper_threshold_percentage,
            lower_threshold_percentage=config.lower_threshold_percentage,
            consecutive_violations=config.consecutive_violations,
            enabled=config.enabled,
            severity=config.severity
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Invalid alert config: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to update alert config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert config: {str(e)}"
        )


@router.post("/alerts/config/{dataset_name}")
async def set_alert_config_simple(
    dataset_name: str,
    threshold_percentage: float = Query(..., ge=0.1, le=100.0),
    consecutive_violations: int = Query(..., ge=1, le=60),
    enabled: bool = Query(default=True),
    severity: AlertSeverity = Query(default=AlertSeverity.MEDIUM),
    alert_service: AlertService = Depends(get_alert_service)
) -> AlertConfigResponse:
    """
    Set alert configuration using query parameters.
    
    Args:
        dataset_name: Dataset identifier
        threshold_percentage: Deviation threshold (applied to both upper and lower)
        consecutive_violations: Required consecutive violations
        enabled: Alert enabled status
        severity: Alert severity level
        alert_service: Alert service instance
        
    Returns:
        AlertConfigResponse: Updated configuration
    """
    try:
        response = alert_service.set_alert_config(
            dataset_name=dataset_name,
            upper_threshold_percentage=threshold_percentage,
            lower_threshold_percentage=threshold_percentage,
            consecutive_violations=consecutive_violations,
            enabled=enabled,
            severity=severity
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Failed to set alert config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set alert config: {str(e)}"
        )


@router.post("/alerts/enable/{dataset_name}")
async def enable_alerts(
    dataset_name: str,
    alert_service: AlertService = Depends(get_alert_service)
) -> dict:
    """
    Enable alerts for a dataset.
    
    Args:
        dataset_name: Dataset identifier
        alert_service: Alert service instance
        
    Returns:
        dict: Enable confirmation
    """
    try:
        alert_service.enable_alerts(dataset_name)
        
        return {
            'message': f'Alerts enabled for {dataset_name}',
            'dataset_name': dataset_name,
            'enabled': True
        }
        
    except Exception as e:
        logger.error(f"Failed to enable alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable alerts: {str(e)}"
        )


@router.post("/alerts/disable/{dataset_name}")
async def disable_alerts(
    dataset_name: str,
    alert_service: AlertService = Depends(get_alert_service)
) -> dict:
    """
    Disable alerts for a dataset.
    
    Args:
        dataset_name: Dataset identifier
        alert_service: Alert service instance
        
    Returns:
        dict: Disable confirmation
    """
    try:
        alert_service.disable_alerts(dataset_name)
        
        return {
            'message': f'Alerts disabled for {dataset_name}',
            'dataset_name': dataset_name,
            'enabled': False
        }
        
    except Exception as e:
        logger.error(f"Failed to disable alerts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable alerts: {str(e)}"
        )


@router.delete("/alerts/history")
async def clear_alert_history(
    dataset_name: Optional[str] = Query(default=None),
    alert_service: AlertService = Depends(get_alert_service)
) -> dict:
    """
    Clear alert history.
    
    Args:
        dataset_name: Optional dataset to clear (clears all if None)
        alert_service: Alert service instance
        
    Returns:
        dict: Clear confirmation
    """
    try:
        cleared_count = alert_service.clear_alert_history(dataset_name)
        
        return {
            'message': 'Alert history cleared',
            'dataset_name': dataset_name or 'all',
            'cleared_count': cleared_count
        }
        
    except Exception as e:
        logger.error(f"Failed to clear alert history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear alert history: {str(e)}"
        )


@router.get("/alerts/statistics")
async def get_alert_statistics(
    dataset_name: Optional[str] = Query(default=None),
    alert_service: AlertService = Depends(get_alert_service)
) -> dict:
    """
    Get alert statistics.
    
    Args:
        dataset_name: Optional dataset filter
        alert_service: Alert service instance
        
    Returns:
        dict: Alert statistics
    """
    try:
        stats = alert_service.get_alert_statistics(dataset_name)
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get alert statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get alert statistics: {str(e)}"
        )
