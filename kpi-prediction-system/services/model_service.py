"""
Model service for training, loading, and managing ML models.
"""

import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

from data.schema import ModelInfo, TrainingResponse
from services.data_service import DataService
from util.config import settings
from util.constants import ModelStatus, ModelType
from util.helpers import (
    calculate_metrics,
    ensure_directory_exists,
    get_config_path,
    get_model_path,
    load_json,
    save_json
)
from util.logger import LoggerMixin


class ModelService(LoggerMixin):
    """Service for ML model management."""
    
    def __init__(self):
        """Initialize model service."""
        self.model_storage = ensure_directory_exists(settings.model_storage_path)
        self.data_service = DataService()
        self.loaded_models: Dict[str, keras.Model] = {}
        self.logger.info("ModelService initialized")
    
    def build_lstm_model(
        self,
        sequence_length: int,
        hidden_size: Optional[int] = None,
        num_layers: Optional[int] = None,
        dropout: Optional[float] = None
    ) -> keras.Model:
        """
        Build LSTM model architecture.
        
        Args:
            sequence_length: Input sequence length
            hidden_size: Number of LSTM units
            num_layers: Number of LSTM layers
            dropout: Dropout rate
            
        Returns:
            keras.Model: Compiled LSTM model
        """
        hidden_size = hidden_size or settings.hidden_size
        num_layers = num_layers or settings.num_layers
        dropout = dropout or settings.dropout
        
        self.logger.info(
            f"Building LSTM model: sequence_length={sequence_length}, "
            f"hidden_size={hidden_size}, num_layers={num_layers}, dropout={dropout}"
        )
        
        model = keras.Sequential()
        
        # First LSTM layer
        model.add(layers.LSTM(
            hidden_size,
            return_sequences=(num_layers > 1),
            input_shape=(sequence_length, 1)
        ))
        model.add(layers.Dropout(dropout))
        
        # Additional LSTM layers
        for i in range(1, num_layers):
            return_sequences = (i < num_layers - 1)
            model.add(layers.LSTM(hidden_size, return_sequences=return_sequences))
            model.add(layers.Dropout(dropout))
        
        # Output layer
        model.add(layers.Dense(1))
        
        # Compile model
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=settings.learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        self.logger.info(f"Model built with {model.count_params()} parameters")
        return model
    
    def train_model(
        self,
        dataset_name: str,
        file_path: str,
        target_column: str,
        epochs: int = 50,
        batch_size: int = 32,
        validation_split: float = 0.2,
        sequence_length: Optional[int] = None
    ) -> TrainingResponse:
        """
        Train a new model on provided dataset.
        
        Args:
            dataset_name: Unique dataset identifier
            file_path: Path to training data
            target_column: Target column name
            epochs: Number of training epochs
            batch_size: Training batch size
            validation_split: Validation split ratio
            sequence_length: Sequence length (default from config)
            
        Returns:
            TrainingResponse: Training result
        """
        start_time = time.time()
        self.logger.info(f"Starting training for dataset: {dataset_name}")
        
        try:
            # Load and validate dataset
            df, dataset_info = self.data_service.load_dataset(file_path, target_column)
            
            is_valid, error_msg = self.data_service.validate_dataset(df, target_column)
            if not is_valid:
                return TrainingResponse(
                    dataset_name=dataset_name,
                    status=ModelStatus.FAILED,
                    message=f"Dataset validation failed: {error_msg}"
                )
            
            # Prepare training data
            seq_length = sequence_length or settings.sequence_length
            training_data = self.data_service.prepare_training_data(
                df, target_column, seq_length, validation_split
            )
            
            # Save scaler
            self.data_service.save_scaler(dataset_name, training_data['scaler'])
            
            # Build model
            model = self.build_lstm_model(seq_length)
            
            # Setup callbacks
            model_path = get_model_path(dataset_name)
            callbacks = [
                EarlyStopping(
                    monitor='val_loss',
                    patience=10,
                    restore_best_weights=True,
                    verbose=1
                ),
                ModelCheckpoint(
                    str(model_path),
                    monitor='val_loss',
                    save_best_only=True,
                    verbose=1
                )
            ]
            
            # Train model
            self.logger.info(f"Training model for {epochs} epochs")
            history = model.fit(
                training_data['X_train'],
                training_data['y_train'],
                epochs=epochs,
                batch_size=batch_size,
                validation_data=(training_data['X_val'], training_data['y_val']),
                callbacks=callbacks,
                verbose=1
            )
            
            # Evaluate model
            y_pred = model.predict(training_data['X_val'])
            metrics = calculate_metrics(training_data['y_val'], y_pred.flatten())
            
            # Save model configuration
            config = {
                'dataset_name': dataset_name,
                'target_column': target_column,
                'sequence_length': seq_length,
                'hidden_size': settings.hidden_size,
                'num_layers': settings.num_layers,
                'dropout': settings.dropout,
                'epochs_trained': len(history.history['loss']),
                'batch_size': batch_size,
                'validation_split': validation_split,
                'metrics': metrics,
                'model_type': ModelType.LSTM.value
            }
            save_json(config, get_config_path(dataset_name))
            
            # Cache model
            self.loaded_models[dataset_name] = model
            
            training_time = time.time() - start_time
            self.logger.info(
                f"Training completed for {dataset_name} in {training_time:.2f}s"
            )
            
            return TrainingResponse(
                dataset_name=dataset_name,
                status=ModelStatus.TRAINED,
                message="Model trained successfully",
                metrics=metrics,
                model_path=str(model_path),
                training_time_seconds=training_time
            )
            
        except Exception as e:
            self.logger.error(f"Training failed for {dataset_name}: {str(e)}", exc_info=True)
            return TrainingResponse(
                dataset_name=dataset_name,
                status=ModelStatus.FAILED,
                message=f"Training failed: {str(e)}"
            )
    
    def load_model(self, dataset_name: str) -> keras.Model:
        """
        Load trained model from disk.
        
        Args:
            dataset_name: Dataset identifier
            
        Returns:
            keras.Model: Loaded model
            
        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        # Check cache first
        if dataset_name in self.loaded_models:
            self.logger.debug(f"Model {dataset_name} loaded from cache")
            return self.loaded_models[dataset_name]
        
        # Load from disk
        model_path = get_model_path(dataset_name)
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found for dataset: {dataset_name}")
        
        self.logger.info(f"Loading model from {model_path}")
        model = keras.models.load_model(str(model_path))
        
        # Cache model
        self.loaded_models[dataset_name] = model
        
        return model
    
    def get_model_config(self, dataset_name: str) -> Dict:
        """
        Get model configuration.
        
        Args:
            dataset_name: Dataset identifier
            
        Returns:
            Dict: Model configuration
            
        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        config_path = get_config_path(dataset_name)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found for dataset: {dataset_name}")
        
        return load_json(config_path)
    
    def get_model_info(self, dataset_name: str) -> ModelInfo:
        """
        Get model information.
        
        Args:
            dataset_name: Dataset identifier
            
        Returns:
            ModelInfo: Model information
        """
        try:
            config = self.get_model_config(dataset_name)
            model_path = get_model_path(dataset_name)
            
            return ModelInfo(
                dataset_name=dataset_name,
                model_type=config.get('model_type', ModelType.LSTM.value),
                status=ModelStatus.TRAINED if model_path.exists() else ModelStatus.UNTRAINED,
                target_column=config.get('target_column'),
                sequence_length=config.get('sequence_length'),
                metrics=config.get('metrics'),
                model_path=str(model_path) if model_path.exists() else None,
                scaler_path=str(self.data_service.get_scaler_path(dataset_name))
            )
        except FileNotFoundError:
            return ModelInfo(
                dataset_name=dataset_name,
                model_type=ModelType.LSTM.value,
                status=ModelStatus.UNTRAINED,
                target_column="unknown",
                sequence_length=settings.sequence_length
            )
    
    def list_models(self) -> list[ModelInfo]:
        """
        List all available models.
        
        Returns:
            list[ModelInfo]: List of model information
        """
        models = []
        
        # Find all model files
        for model_file in self.model_storage.glob("*_model.h5"):
            dataset_name = model_file.stem.replace("_model", "")
            try:
                model_info = self.get_model_info(dataset_name)
                models.append(model_info)
            except Exception as e:
                self.logger.warning(f"Failed to load info for {dataset_name}: {e}")
        
        return models
    
    def delete_model(self, dataset_name: str) -> bool:
        """
        Delete a trained model and associated files.
        
        Args:
            dataset_name: Dataset identifier
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            # Remove from cache
            if dataset_name in self.loaded_models:
                del self.loaded_models[dataset_name]
            
            # Delete files
            model_path = get_model_path(dataset_name)
            scaler_path = self.data_service.get_scaler_path(dataset_name)
            config_path = get_config_path(dataset_name)
            
            deleted = False
            for path in [model_path, scaler_path, config_path]:
                if path.exists():
                    path.unlink()
                    deleted = True
                    self.logger.info(f"Deleted {path}")
            
            return deleted
            
        except Exception as e:
            self.logger.error(f"Failed to delete model {dataset_name}: {e}")
            return False
    
    def predict(
        self,
        dataset_name: str,
        input_sequence: np.ndarray
    ) -> float:
        """
        Make prediction using trained model.
        
        Args:
            dataset_name: Dataset identifier
            input_sequence: Input sequence (normalized)
            
        Returns:
            float: Predicted value (normalized)
        """
        model = self.load_model(dataset_name)
        
        # Make prediction
        prediction = model.predict(input_sequence, verbose=0)
        
        return float(prediction[0][0])
    
    def evaluate_model(
        self,
        dataset_name: str,
        X_test: np.ndarray,
        y_test: np.ndarray
    ) -> Dict[str, float]:
        """
        Evaluate model on test data.
        
        Args:
            dataset_name: Dataset identifier
            X_test: Test input sequences
            y_test: Test target values
            
        Returns:
            Dict: Evaluation metrics
        """
        model = self.load_model(dataset_name)
        
        # Make predictions
        y_pred = model.predict(X_test, verbose=0).flatten()
        
        # Calculate metrics
        metrics = calculate_metrics(y_test, y_pred)
        
        self.logger.info(f"Model evaluation for {dataset_name}: {metrics}")
        return metrics
    
    def retrain_model(
        self,
        dataset_name: str,
        file_path: str,
        target_column: str,
        **kwargs
    ) -> TrainingResponse:
        """
        Retrain an existing model.
        
        Args:
            dataset_name: Dataset identifier
            file_path: Path to training data
            target_column: Target column name
            **kwargs: Additional training parameters
            
        Returns:
            TrainingResponse: Training result
        """
        self.logger.info(f"Retraining model: {dataset_name}")
        
        # Delete existing model
        self.delete_model(dataset_name)
        
        # Train new model
        return self.train_model(
            dataset_name=dataset_name,
            file_path=file_path,
            target_column=target_column,
            **kwargs
        )
