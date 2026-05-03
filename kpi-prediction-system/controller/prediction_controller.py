"""
Prediction controller for prediction endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from data.schema import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    PredictionRequest,
    PredictionResponse
)
from services.prediction_service import PredictionService
from util.helpers import parse_timestamp
from util.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Prediction"])


def get_prediction_service() -> PredictionService:
    """Dependency for prediction service."""
    return PredictionService()


@router.post("/predict", response_model=PredictionResponse)
async def predict(
    request: PredictionRequest,
    prediction_service: PredictionService = Depends(get_prediction_service)
) -> PredictionResponse:
    """
    Generate prediction for a specific timestamp.
    
    Args:
        request: Prediction request
        prediction_service: Prediction service instance
        
    Returns:
        PredictionResponse: Prediction result
        
    Raises:
        HTTPException: If prediction fails
    """
    logger.info(f"Prediction request for dataset: {request.dataset_name}")
    
    try:
        # Parse timestamp if provided
        timestamp = None
        if request.timestamp:
            timestamp = parse_timestamp(request.timestamp)
        
        # Generate prediction
        prediction = prediction_service.predict(
            dataset_name=request.dataset_name,
            timestamp=timestamp,
            features=request.features
        )
        
        return prediction
        
    except ValueError as e:
        logger.error(f"Invalid prediction request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except FileNotFoundError as e:
        logger.error(f"Model not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(
    request: BatchPredictionRequest,
    prediction_service: PredictionService = Depends(get_prediction_service)
) -> BatchPredictionResponse:
    """
    Generate predictions for multiple timestamps.
    
    Args:
        request: Batch prediction request
        prediction_service: Prediction service instance
        
    Returns:
        BatchPredictionResponse: Batch prediction results
    """
    logger.info(
        f"Batch prediction request for dataset: {request.dataset_name}, "
        f"count: {len(request.timestamps)}"
    )
    
    try:
        # Parse timestamps
        timestamps = [parse_timestamp(ts) for ts in request.timestamps]
        
        # Generate predictions
        predictions = prediction_service.predict_batch(
            dataset_name=request.dataset_name,
            timestamps=timestamps
        )
        
        # Format response
        prediction_dicts = [
            {
                'timestamp': pred.timestamp.isoformat(),
                'predicted_value': pred.predicted_value,
                'confidence': pred.confidence
            }
            for pred in predictions
        ]
        
        return BatchPredictionResponse(
            dataset_name=request.dataset_name,
            predictions=prediction_dicts,
            total_count=len(request.timestamps),
            successful_count=len(predictions),
            failed_count=len(request.timestamps) - len(predictions)
        )
        
    except Exception as e:
        logger.error(f"Batch prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


@router.get("/predict/next/{dataset_name}")
async def predict_next_n_minutes(
    dataset_name: str,
    n_minutes: int = Query(default=10, ge=1, le=1440),
    prediction_service: PredictionService = Depends(get_prediction_service)
) -> List[PredictionResponse]:
    """
    Predict values for next N minutes.
    
    Args:
        dataset_name: Dataset identifier
        n_minutes: Number of minutes to predict
        prediction_service: Prediction service instance
        
    Returns:
        List[PredictionResponse]: Predictions for next N minutes
    """
    logger.info(f"Predicting next {n_minutes} minutes for {dataset_name}")
    
    try:
        predictions = prediction_service.predict_next_n_minutes(
            dataset_name=dataset_name,
            n_minutes=n_minutes
        )
        
        return predictions
        
    except ValueError as e:
        logger.error(f"Invalid request: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Multi-step prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-step prediction failed: {str(e)}"
        )


@router.get("/predict/history/{dataset_name}")
async def get_prediction_history(
    dataset_name: str,
    limit: int = Query(default=100, ge=1, le=1000),
    prediction_service: PredictionService = Depends(get_prediction_service)
) -> dict:
    """
    Get recent prediction history.
    
    Args:
        dataset_name: Dataset identifier
        limit: Maximum number of values to return
        prediction_service: Prediction service instance
        
    Returns:
        dict: Prediction history
    """
    try:
        history = prediction_service.get_prediction_history(
            dataset_name=dataset_name,
            limit=limit
        )
        
        return {
            'dataset_name': dataset_name,
            'history': history,
            'count': len(history)
        }
        
    except Exception as e:
        logger.error(f"Failed to get prediction history: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prediction history: {str(e)}"
        )


@router.post("/predict/update/{dataset_name}")
async def update_recent_values(
    dataset_name: str,
    value: float,
    prediction_service: PredictionService = Depends(get_prediction_service)
) -> dict:
    """
    Update recent values cache for a dataset.
    
    Args:
        dataset_name: Dataset identifier
        value: New value to add
        prediction_service: Prediction service instance
        
    Returns:
        dict: Update confirmation
    """
    try:
        prediction_service.update_recent_values(dataset_name, value)
        
        return {
            'message': 'Recent values updated',
            'dataset_name': dataset_name,
            'value': value
        }
        
    except Exception as e:
        logger.error(f"Failed to update recent values: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update recent values: {str(e)}"
        )


@router.delete("/predict/cache/{dataset_name}")
async def clear_prediction_cache(
    dataset_name: str,
    prediction_service: PredictionService = Depends(get_prediction_service)
) -> dict:
    """
    Clear prediction cache for a dataset.
    
    Args:
        dataset_name: Dataset identifier
        prediction_service: Prediction service instance
        
    Returns:
        dict: Clear confirmation
    """
    try:
        prediction_service.clear_cache(dataset_name)
        
        return {
            'message': 'Prediction cache cleared',
            'dataset_name': dataset_name
        }
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )


@router.get("/predict/cache/stats")
async def get_cache_stats(
    prediction_service: PredictionService = Depends(get_prediction_service)
) -> dict:
    """
    Get prediction cache statistics.
    
    Args:
        prediction_service: Prediction service instance
        
    Returns:
        dict: Cache statistics
    """
    try:
        stats = prediction_service.get_cache_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cache stats: {str(e)}"
        )
