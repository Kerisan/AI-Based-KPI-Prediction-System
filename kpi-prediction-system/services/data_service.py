"""
Data service for loading, processing, and managing datasets.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from data.schema import DatasetInfo
from util.config import settings
from util.constants import FEATURE_COLUMNS, TARGET_COLUMNS
from util.helpers import (
    ensure_directory_exists,
    generate_time_features,
    validate_dataframe,
    get_scaler_path,
    save_pickle,
    load_pickle
)
from util.logger import LoggerMixin


class DataService(LoggerMixin):
    """Service for data processing and management."""
    
    def __init__(self):
        """Initialize data service."""
        self.dataset_storage = ensure_directory_exists(settings.dataset_storage_path)
        self.logger.info("DataService initialized")
    
    def load_dataset(
        self,
        file_path: str,
        target_column: str
    ) -> Tuple[pd.DataFrame, DatasetInfo]:
        """
        Load dataset from CSV file.
        
        Args:
            file_path: Path to CSV file
            target_column: Name of target column
            
        Returns:
            Tuple[pd.DataFrame, DatasetInfo]: Loaded dataframe and info
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If required columns are missing
        """
        self.logger.info(f"Loading dataset from {file_path}")
        
        # Check file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
        
        # Load CSV
        df = pd.read_csv(file_path)
        self.logger.info(f"Loaded {len(df)} records from {file_path}")
        
        # Validate target column exists
        if target_column not in df.columns:
            raise ValueError(f"Target column '{target_column}' not found in dataset")
        
        # Parse timestamp if exists
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')
            df = df.sort_values('timestamp')
        
        # Remove rows with null target values
        if target_column in df.columns:
            initial_count = len(df)
            df = df.dropna(subset=[target_column])
            dropped_count = initial_count - len(df)
            if dropped_count > 0:
                self.logger.info(f"Dropped {dropped_count} rows with null values in '{target_column}'")
        
        # Generate time features if timestamp exists
        if 'timestamp' in df.columns:
            df = self._add_time_features(df)
        
        # Create dataset info
        dataset_info = DatasetInfo(
            dataset_name=Path(file_path).stem,
            file_path=file_path,
            target_column=target_column,
            total_records=len(df),
            columns=df.columns.tolist(),
            date_range={
                'start': str(df['timestamp'].min()) if 'timestamp' in df.columns else None,
                'end': str(df['timestamp'].max()) if 'timestamp' in df.columns else None
            }
        )
        
        self.logger.info(f"Dataset info: {dataset_info.model_dump()}")
        return df, dataset_info
    
    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add time-based features to dataframe.
        
        Args:
            df: Input dataframe with timestamp column
            
        Returns:
            pd.DataFrame: Dataframe with added features
        """
        self.logger.debug("Adding time features")
        
        df['hour'] = df['timestamp'].dt.hour
        df['minute'] = df['timestamp'].dt.minute
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['day_of_month'] = df['timestamp'].dt.day
        df['month'] = df['timestamp'].dt.month
        df['is_weekend'] = (df['timestamp'].dt.dayofweek >= 5).astype(int)
        df['is_business_hour'] = ((df['timestamp'].dt.hour >= 9) & 
                                   (df['timestamp'].dt.hour <= 17)).astype(int)
        
        return df
    
    def prepare_training_data(
        self,
        df: pd.DataFrame,
        target_column: str,
        sequence_length: int,
        validation_split: float = 0.2
    ) -> Dict[str, np.ndarray]:
        """
        Prepare data for training.
        
        Args:
            df: Input dataframe
            target_column: Target column name
            sequence_length: Length of input sequences
            validation_split: Validation split ratio
            
        Returns:
            Dict: Dictionary with train/val data and scaler
        """
        self.logger.info(f"Preparing training data with sequence_length={sequence_length}")
        
        # Extract target values
        target_values = df[target_column].values
        
        # Normalize data
        scaler = MinMaxScaler(feature_range=(0, 1))
        normalized_data = scaler.fit_transform(target_values.reshape(-1, 1)).flatten()
        
        # Create sequences
        X, y = self._create_sequences(normalized_data, sequence_length)
        
        # Split into train and validation
        split_idx = int(len(X) * (1 - validation_split))
        
        X_train = X[:split_idx]
        y_train = y[:split_idx]
        X_val = X[split_idx:]
        y_val = y[split_idx:]
        
        self.logger.info(
            f"Training data prepared: "
            f"X_train={X_train.shape}, y_train={y_train.shape}, "
            f"X_val={X_val.shape}, y_val={y_val.shape}"
        )
        
        return {
            'X_train': X_train,
            'y_train': y_train,
            'X_val': X_val,
            'y_val': y_val,
            'scaler': scaler
        }
    
    def _create_sequences(
        self,
        data: np.ndarray,
        sequence_length: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create sequences for time series prediction.
        
        Args:
            data: Input data array
            sequence_length: Length of each sequence
            
        Returns:
            Tuple[np.ndarray, np.ndarray]: X sequences and y targets
        """
        X, y = [], []
        
        for i in range(len(data) - sequence_length):
            X.append(data[i:i + sequence_length])
            y.append(data[i + sequence_length])
        
        X = np.array(X)
        y = np.array(y)
        
        # Reshape X for LSTM input (samples, timesteps, features)
        X = X.reshape((X.shape[0], X.shape[1], 1))
        
        return X, y
    
    def save_scaler(self, dataset_name: str, scaler: MinMaxScaler) -> str:
        """
        Save scaler to disk.
        
        Args:
            dataset_name: Dataset identifier
            scaler: Fitted scaler
            
        Returns:
            str: Path to saved scaler
        """
        scaler_path = get_scaler_path(dataset_name)
        save_pickle(scaler, scaler_path)
        self.logger.info(f"Scaler saved to {scaler_path}")
        return str(scaler_path)
    
    def load_scaler(self, dataset_name: str) -> MinMaxScaler:
        """
        Load scaler from disk.
        
        Args:
            dataset_name: Dataset identifier
            
        Returns:
            MinMaxScaler: Loaded scaler
            
        Raises:
            FileNotFoundError: If scaler file doesn't exist
        """
        scaler_path = get_scaler_path(dataset_name)
        
        if not scaler_path.exists():
            raise FileNotFoundError(f"Scaler not found for dataset: {dataset_name}")
        
        scaler = load_pickle(scaler_path)
        self.logger.info(f"Scaler loaded from {scaler_path}")
        return scaler
    
    def prepare_prediction_input(
        self,
        dataset_name: str,
        recent_values: List[float],
        sequence_length: int
    ) -> np.ndarray:
        """
        Prepare input for prediction.
        
        Args:
            dataset_name: Dataset identifier
            recent_values: Recent target values
            sequence_length: Required sequence length
            
        Returns:
            np.ndarray: Prepared input array
            
        Raises:
            ValueError: If insufficient data
        """
        if len(recent_values) < sequence_length:
            raise ValueError(
                f"Insufficient data: need {sequence_length}, got {len(recent_values)}"
            )
        
        # Load scaler
        scaler = self.load_scaler(dataset_name)
        
        # Take last sequence_length values
        sequence = recent_values[-sequence_length:]
        
        # Normalize
        normalized = scaler.transform(np.array(sequence).reshape(-1, 1)).flatten()
        
        # Reshape for LSTM input (1, sequence_length, 1)
        X = normalized.reshape((1, sequence_length, 1))
        
        return X
    
    def denormalize_prediction(
        self,
        dataset_name: str,
        normalized_value: float
    ) -> float:
        """
        Denormalize predicted value.
        
        Args:
            dataset_name: Dataset identifier
            normalized_value: Normalized prediction
            
        Returns:
            float: Denormalized value
        """
        scaler = self.load_scaler(dataset_name)
        denormalized = scaler.inverse_transform([[normalized_value]])[0][0]
        return float(denormalized)
    
    def validate_dataset(
        self,
        df: pd.DataFrame,
        target_column: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate dataset structure and content.
        
        Args:
            df: Dataframe to validate
            target_column: Target column name
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check if dataframe is empty
        if df.empty:
            return False, "Dataset is empty"
        
        # Check target column exists
        if target_column not in df.columns:
            return False, f"Target column '{target_column}' not found"
        
        # Check for null values in target
        if df[target_column].isnull().any():
            return False, f"Target column '{target_column}' contains null values"
        
        # Check if target is numeric
        if not pd.api.types.is_numeric_dtype(df[target_column]):
            return False, f"Target column '{target_column}' must be numeric"
        
        # Check minimum data points
        if len(df) < 100:
            return False, f"Dataset too small: {len(df)} records (minimum 100 required)"
        
        return True, None
    
    def get_dataset_statistics(
        self,
        df: pd.DataFrame,
        target_column: str
    ) -> Dict[str, float]:
        """
        Calculate dataset statistics.
        
        Args:
            df: Input dataframe
            target_column: Target column name
            
        Returns:
            Dict: Statistics dictionary
        """
        target_data = df[target_column]
        
        stats = {
            'count': int(len(target_data)),
            'mean': float(target_data.mean()),
            'std': float(target_data.std()),
            'min': float(target_data.min()),
            'max': float(target_data.max()),
            'median': float(target_data.median()),
            'q25': float(target_data.quantile(0.25)),
            'q75': float(target_data.quantile(0.75))
        }
        
        self.logger.debug(f"Dataset statistics: {stats}")
        return stats
    
    def generate_sample_dataset(
        self,
        dataset_name: str,
        num_records: int = 1440,
        target_column: str = "traffic_count"
    ) -> str:
        """
        Generate a sample dataset for testing.
        
        Args:
            dataset_name: Name for the dataset
            num_records: Number of records to generate
            target_column: Name of target column
            
        Returns:
            str: Path to generated dataset
        """
        self.logger.info(f"Generating sample dataset: {dataset_name}")
        
        # Generate timestamps (1 minute intervals)
        start_time = datetime(2024, 1, 1, 0, 0, 0)
        timestamps = [start_time + pd.Timedelta(minutes=i) for i in range(num_records)]
        
        # Generate synthetic data with patterns
        base_values = []
        for ts in timestamps:
            # Daily pattern
            hour_factor = 1.0 + 0.5 * np.sin(2 * np.pi * ts.hour / 24)
            # Weekly pattern
            weekday_factor = 1.2 if ts.weekday() < 5 else 0.8
            # Random noise
            noise = np.random.normal(0, 0.1)
            
            value = 1000 * hour_factor * weekday_factor * (1 + noise)
            base_values.append(max(0, value))
        
        # Create dataframe
        df = pd.DataFrame({
            'timestamp': timestamps,
            target_column: base_values
        })
        
        # Add time features
        df = self._add_time_features(df)
        
        # Save to CSV
        file_path = self.dataset_storage / f"{dataset_name}.csv"
        df.to_csv(file_path, index=False)
        
        self.logger.info(f"Sample dataset saved to {file_path}")
        return str(file_path)
