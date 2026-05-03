"""
Prediction service for generating and managing predictions.
"""

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np

from data.schema import PredictionRequest, PredictionResponse
from services.data_service import DataService
from services.model_service import ModelService
from util.helpers import generate_time_features, parse_timestamp
from util.logger import LoggerMixin


class PredictionService(LoggerMixin):
    """Service for making predictions."""
    
    def __init__(self):
        """Initialize prediction service."""
        self.model_service = ModelService()
        self.data_service = DataService()
        self.prediction_cache: Dict[str, List[float]] = {}
        self.logger.info("PredictionService initialized")
    
    def predict(
        self,
        dataset_name: str,
        timestamp: Optional[datetime] = None,
        features: Optional[Dict] = None,
        recent_values: Optional[List[float]] = None
    ) -> PredictionResponse:
        """
        Generate prediction for given timestamp.
        
        Args:
            dataset_name: Dataset identifier
            timestamp: Timestamp for prediction (default: now)
            features: Optional manual features
            recent_values: Recent historical values for sequence
            
        Returns:
            PredictionResponse: Prediction result
            
        Raises:
            ValueError: If model not found or insufficient data
        """
        # Use current time if not provided
        if timestamp is None:
            timestamp = datetime.now()
        elif isinstance(timestamp, str):
            timestamp = parse_timestamp(timestamp)
        
        self.logger.info(f"Generating prediction for {dataset_name} at {timestamp}")
        
        try:
            # Load model configuration
            config = self.model_service.get_model_config(dataset_name)
            sequence_length = config['sequence_length']
            
            # Prepare input sequence
            if recent_values is None:
                # Try to get from cache
                recent_values = self._get_recent_values(dataset_name, sequence_length)
            
            if len(recent_values) < sequence_length:
                raise ValueError(
                    f"Insufficient historical data: need {sequence_length} values, "
                    f"got {len(recent_values)}"
                )
            
            # Prepare input
            X = self.data_service.prepare_prediction_input(
                dataset_name,
                recent_values,
                sequence_length
            )
            
            # Make prediction (normalized)
            normalized_prediction = self.model_service.predict(dataset_name, X)
            
            # Denormalize
            predicted_value = self.data_service.denormalize_prediction(
                dataset_name,
                normalized_prediction
            )
            
            # Generate features used
            if features is None:
                features = generate_time_features(timestamp)
            
            self.logger.info(
                f"Prediction for {dataset_name}: {predicted_value:.2f} at {timestamp}"
            )
            
            return PredictionResponse(
                dataset_name=dataset_name,
                predicted_value=float(predicted_value),
                timestamp=timestamp,
                confidence=self._calculate_confidence(normalized_prediction),
                features_used=features,
                model_version=config.get('model_type', 'LSTM')
            )
            
        except FileNotFoundError as e:
            self.logger.error(f"Model not found for {dataset_name}: {e}")
            raise ValueError(f"Model not trained for dataset: {dataset_name}")
        except Exception as e:
            self.logger.error(f"Prediction failed for {dataset_name}: {e}", exc_info=True)
            raise
    
    def predict_batch(
        self,
        dataset_name: str,
        timestamps: List[datetime],
        recent_values: Optional[List[float]] = None
    ) -> List[PredictionResponse]:
        """
        Generate predictions for multiple timestamps.
        
        Args:
            dataset_name: Dataset identifier
            timestamps: List of timestamps
            recent_values: Recent historical values
            
        Returns:
            List[PredictionResponse]: List of predictions
        """
        self.logger.info(f"Generating batch predictions for {dataset_name}: {len(timestamps)} timestamps")
        
        predictions = []
        
        for timestamp in timestamps:
            try:
                prediction = self.predict(
                    dataset_name=dataset_name,
                    timestamp=timestamp,
                    recent_values=recent_values
                )
                predictions.append(prediction)
            except Exception as e:
                self.logger.warning(f"Failed to predict for {timestamp}: {e}")
        
        return predictions
    
    def update_recent_values(
        self,
        dataset_name: str,
        value: float,
        max_length: int = 1440  # 24 hours of minute data
    ) -> None:
        """
        Update cache of recent values for a dataset.
        
        Args:
            dataset_name: Dataset identifier
            value: New value to add
            max_length: Maximum cache length
        """
        if dataset_name not in self.prediction_cache:
            self.prediction_cache[dataset_name] = []
        
        self.prediction_cache[dataset_name].append(value)
        
        # Keep only recent values
        if len(self.prediction_cache[dataset_name]) > max_length:
            self.prediction_cache[dataset_name] = self.prediction_cache[dataset_name][-max_length:]
        
        self.logger.debug(
            f"Updated cache for {dataset_name}: {len(self.prediction_cache[dataset_name])} values"
        )
    
    def _get_recent_values(
        self,
        dataset_name: str,
        required_length: int
    ) -> List[float]:
        """
        Get recent values from cache.
        
        Args:
            dataset_name: Dataset identifier
            required_length: Required number of values
            
        Returns:
            List[float]: Recent values
        """
        if dataset_name not in self.prediction_cache:
            return []
        
        values = self.prediction_cache[dataset_name]
        
        if len(values) < required_length:
            self.logger.warning(
                f"Insufficient cached values for {dataset_name}: "
                f"need {required_length}, have {len(values)}"
            )
        
        return values[-required_length:] if values else []
    
    def _calculate_confidence(self, normalized_prediction: float) -> float:
        """
        Calculate prediction confidence score.
        
        Args:
            normalized_prediction: Normalized prediction value
            
        Returns:
            float: Confidence score (0-1)
        """
        # Simple confidence based on normalized value range
        # Values closer to 0.5 are more confident (middle of range)
        distance_from_center = abs(normalized_prediction - 0.5)
        confidence = 1.0 - (distance_from_center * 2)
        
        # Ensure confidence is between 0 and 1
        confidence = max(0.0, min(1.0, confidence))
        
        return round(confidence, 4)
    
    def get_prediction_history(
        self,
        dataset_name: str,
        limit: int = 100
    ) -> List[float]:
        """
        Get recent prediction history.
        
        Args:
            dataset_name: Dataset identifier
            limit: Maximum number of values to return
            
        Returns:
            List[float]: Recent values
        """
        if dataset_name not in self.prediction_cache:
            return []
        
        values = self.prediction_cache[dataset_name]
        return values[-limit:] if values else []
    
    def clear_cache(self, dataset_name: Optional[str] = None) -> None:
        """
        Clear prediction cache.
        
        Args:
            dataset_name: Optional dataset to clear (clears all if None)
        """
        if dataset_name:
            if dataset_name in self.prediction_cache:
                del self.prediction_cache[dataset_name]
                self.logger.info(f"Cleared cache for {dataset_name}")
        else:
            self.prediction_cache.clear()
            self.logger.info("Cleared all prediction cache")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dict: Cache statistics
        """
        stats = {
            'total_datasets': len(self.prediction_cache),
            'total_values': sum(len(values) for values in self.prediction_cache.values())
        }
        
        for dataset_name, values in self.prediction_cache.items():
            stats[f'{dataset_name}_count'] = len(values)
        
        return stats
    
    def predict_next_n_minutes(
        self,
        dataset_name: str,
        n_minutes: int,
        start_timestamp: Optional[datetime] = None
    ) -> List[PredictionResponse]:
        """
        Predict values for next N minutes.
        
        Args:
            dataset_name: Dataset identifier
            n_minutes: Number of minutes to predict
            start_timestamp: Starting timestamp (default: now)
            
        Returns:
            List[PredictionResponse]: Predictions for next N minutes
        """
        if start_timestamp is None:
            start_timestamp = datetime.now()
        
        self.logger.info(
            f"Predicting next {n_minutes} minutes for {dataset_name} "
            f"starting from {start_timestamp}"
        )
        
        predictions = []
        current_timestamp = start_timestamp
        
        # Get initial recent values
        config = self.model_service.get_model_config(dataset_name)
        sequence_length = config['sequence_length']
        recent_values = self._get_recent_values(dataset_name, sequence_length)
        
        if len(recent_values) < sequence_length:
            raise ValueError(
                f"Insufficient historical data for multi-step prediction: "
                f"need {sequence_length}, got {len(recent_values)}"
            )
        
        # Make predictions iteratively
        for i in range(n_minutes):
            # Predict next value
            prediction = self.predict(
                dataset_name=dataset_name,
                timestamp=current_timestamp,
                recent_values=recent_values
            )
            predictions.append(prediction)
            
            # Update recent values with prediction for next iteration
            recent_values.append(prediction.predicted_value)
            recent_values = recent_values[-sequence_length:]
            
            # Move to next minute
            from datetime import timedelta
            current_timestamp += timedelta(minutes=1)
        
        return predictions
    
    def validate_prediction_input(
        self,
        dataset_name: str,
        recent_values: List[float]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate prediction input data.
        
        Args:
            dataset_name: Dataset identifier
            recent_values: Recent values to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            config = self.model_service.get_model_config(dataset_name)
            sequence_length = config['sequence_length']
            
            if len(recent_values) < sequence_length:
                return False, f"Need {sequence_length} values, got {len(recent_values)}"
            
            # Check for invalid values
            if any(np.isnan(v) or np.isinf(v) for v in recent_values):
                return False, "Recent values contain NaN or Inf"
            
            # Check for negative values (if applicable)
            if any(v < 0 for v in recent_values):
                return False, "Recent values contain negative numbers"
            
            return True, None
            
        except FileNotFoundError:
            return False, f"Model not found for dataset: {dataset_name}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
