"""
Monitoring controller for start/stop operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse

from services.realtime_monitor import RealtimeMonitoringService
from util.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])

# Global monitoring service instance
_monitoring_service: Optional[RealtimeMonitoringService] = None


def get_monitoring_service() -> RealtimeMonitoringService:
    """Get monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monitoring service not initialized. Please run startup wizard first."
        )
    return _monitoring_service


def set_monitoring_service(service: RealtimeMonitoringService):
    """Set monitoring service instance."""
    global _monitoring_service
    _monitoring_service = service


@router.post("/start")
async def start_monitoring(
    kpi_name: Optional[str] = Query(default=None, description="Specific KPI to start (all if None)"),
    monitoring_service: RealtimeMonitoringService = Depends(get_monitoring_service)
) -> dict:
    """
    Start monitoring for specific KPI or all KPIs.
    
    Args:
        kpi_name: Optional specific KPI name
        monitoring_service: Monitoring service instance
        
    Returns:
        dict: Start confirmation
    """
    try:
        monitoring_service.start_monitoring(kpi_name)
        
        if kpi_name:
            return {
                'message': f'Started monitoring {kpi_name}',
                'kpi_name': kpi_name,
                'status': 'running'
            }
        else:
            kpis = monitoring_service.list_kpis()
            return {
                'message': f'Started monitoring {len(kpis)} KPIs',
                'kpis': kpis,
                'status': 'running'
            }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring: {str(e)}"
        )


@router.post("/stop")
async def stop_monitoring(
    kpi_name: Optional[str] = Query(default=None, description="Specific KPI to stop (all if None)"),
    monitoring_service: RealtimeMonitoringService = Depends(get_monitoring_service)
) -> dict:
    """
    Stop monitoring for specific KPI or all KPIs.
    
    Args:
        kpi_name: Optional specific KPI name
        monitoring_service: Monitoring service instance
        
    Returns:
        dict: Stop confirmation
    """
    try:
        monitoring_service.stop_monitoring(kpi_name)
        
        if kpi_name:
            return {
                'message': f'Stopped monitoring {kpi_name}',
                'kpi_name': kpi_name,
                'status': 'stopped'
            }
        else:
            kpis = monitoring_service.list_kpis()
            return {
                'message': f'Stopped monitoring {len(kpis)} KPIs',
                'kpis': kpis,
                'status': 'stopped'
            }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop monitoring: {str(e)}"
        )


@router.get("/status")
async def get_monitoring_status(
    kpi_name: Optional[str] = Query(default=None, description="Specific KPI status (all if None)"),
    monitoring_service: RealtimeMonitoringService = Depends(get_monitoring_service)
) -> dict:
    """
    Get monitoring status for specific KPI or all KPIs.
    
    Args:
        kpi_name: Optional specific KPI name
        monitoring_service: Monitoring service instance
        
    Returns:
        dict: Status information
    """
    try:
        if kpi_name:
            return monitoring_service.get_kpi_status(kpi_name)
        else:
            return monitoring_service.get_all_status()
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )


@router.get("/kpis")
async def list_kpis(
    monitoring_service: RealtimeMonitoringService = Depends(get_monitoring_service)
) -> dict:
    """
    List all registered KPIs.
    
    Args:
        monitoring_service: Monitoring service instance
        
    Returns:
        dict: List of KPIs
    """
    try:
        kpis = monitoring_service.list_kpis()
        return {
            'kpis': kpis,
            'total_count': len(kpis)
        }
    
    except Exception as e:
        logger.error(f"Failed to list KPIs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list KPIs: {str(e)}"
        )


@router.get("/data/{kpi_name}")
async def get_kpi_data(
    kpi_name: str,
    minutes: int = Query(default=60, ge=1, le=1440, description="Number of minutes of data"),
    monitoring_service: RealtimeMonitoringService = Depends(get_monitoring_service)
) -> dict:
    """
    Get recent data for a KPI.
    
    Args:
        kpi_name: KPI name
        minutes: Number of minutes of data
        monitoring_service: Monitoring service instance
        
    Returns:
        dict: Recent data points
    """
    try:
        data = monitoring_service.get_recent_data(kpi_name, minutes)
        
        return {
            'kpi_name': kpi_name,
            'data': data,
            'count': len(data),
            'minutes': minutes
        }
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to get data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get data: {str(e)}"
        )
