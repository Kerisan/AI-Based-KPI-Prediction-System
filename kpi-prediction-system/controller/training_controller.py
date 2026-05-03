"""
Training controller for model training endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from data.schema import (
    ModelInfo,
    ModelListResponse,
    TrainingRequest,
    TrainingResponse
)
from services.model_service import ModelService
from util.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Training"])


def get_model_service() -> ModelService:
    """Dependency for model service."""
    return ModelService()


@router.post("/train", response_model=TrainingResponse)
async def train_model(
    request: TrainingRequest,
    model_service: ModelService = Depends(get_model_service)
) -> TrainingResponse:
    """
    Train a new model on provided dataset.
    
    Args:
        request: Training request parameters
        model_service: Model service instance
        
    Returns:
        TrainingResponse: Training result
        
    Raises:
        HTTPException: If training fails
    """
    logger.info(f"Training request received for dataset: {request.dataset_name}")
    
    try:
        response = model_service.train_model(
            dataset_name=request.dataset_name,
            file_path=request.file_path,
            target_column=request.target_column,
            epochs=request.epochs,
            batch_size=request.batch_size,
            validation_split=request.validation_split,
            sequence_length=request.sequence_length
        )
        
        return response
        
    except FileNotFoundError as e:
        logger.error(f"Dataset file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        logger.error(f"Invalid training parameters: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Training failed: {str(e)}"
        )


@router.post("/retrain", response_model=TrainingResponse)
async def retrain_model(
    request: TrainingRequest,
    model_service: ModelService = Depends(get_model_service)
) -> TrainingResponse:
    """
    Retrain an existing model.
    
    Args:
        request: Training request parameters
        model_service: Model service instance
        
    Returns:
        TrainingResponse: Training result
    """
    logger.info(f"Retrain request received for dataset: {request.dataset_name}")
    
    try:
        response = model_service.retrain_model(
            dataset_name=request.dataset_name,
            file_path=request.file_path,
            target_column=request.target_column,
            epochs=request.epochs,
            batch_size=request.batch_size,
            validation_split=request.validation_split,
            sequence_length=request.sequence_length
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Retraining failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retraining failed: {str(e)}"
        )


@router.get("/models", response_model=ModelListResponse)
async def list_models(
    model_service: ModelService = Depends(get_model_service)
) -> ModelListResponse:
    """
    List all trained models.
    
    Args:
        model_service: Model service instance
        
    Returns:
        ModelListResponse: List of models
    """
    try:
        models = model_service.list_models()
        
        return ModelListResponse(
            models=models,
            total_count=len(models)
        )
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@router.get("/models/{dataset_name}", response_model=ModelInfo)
async def get_model_info(
    dataset_name: str,
    model_service: ModelService = Depends(get_model_service)
) -> ModelInfo:
    """
    Get information about a specific model.
    
    Args:
        dataset_name: Dataset identifier
        model_service: Model service instance
        
    Returns:
        ModelInfo: Model information
    """
    try:
        model_info = model_service.get_model_info(dataset_name)
        return model_info
        
    except Exception as e:
        logger.error(f"Failed to get model info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model info: {str(e)}"
        )


@router.delete("/models/{dataset_name}")
async def delete_model(
    dataset_name: str,
    model_service: ModelService = Depends(get_model_service)
) -> dict:
    """
    Delete a trained model.
    
    Args:
        dataset_name: Dataset identifier
        model_service: Model service instance
        
    Returns:
        dict: Deletion result
    """
    try:
        success = model_service.delete_model(dataset_name)
        
        if success:
            return {
                "message": f"Model {dataset_name} deleted successfully",
                "dataset_name": dataset_name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model not found: {dataset_name}"
            )
            
    except Exception as e:
        logger.error(f"Failed to delete model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete model: {str(e)}"
        )


@router.get("/models/{dataset_name}/config")
async def get_model_config(
    dataset_name: str,
    model_service: ModelService = Depends(get_model_service)
) -> dict:
    """
    Get model configuration.
    
    Args:
        dataset_name: Dataset identifier
        model_service: Model service instance
        
    Returns:
        dict: Model configuration
    """
    try:
        config = model_service.get_model_config(dataset_name)
        return config
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model configuration not found: {dataset_name}"
        )
    except Exception as e:
        logger.error(f"Failed to get model config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model config: {str(e)}"
        )
