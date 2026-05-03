"""
Helper utility functions used across the application.
"""

import hashlib
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from util.config import settings
from util.logger import get_logger

logger = get_logger(__name__)


def ensure_directory_exists(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, create it if it doesn't.
    
    Args:
        path: Directory path
        
    Returns:
        Path: Path object
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def get_model_path(dataset_name: str) -> Path:
    """
    Get the file path for a trained model.
    
    Args:
        dataset_name: Name of the dataset
        
    Returns:
        Path: Model file path
    """
    model_dir = ensure_directory_exists(settings.model_storage_path)
    return model_dir / f"{dataset_name}_model.h5"


def get_scaler_path(dataset_name: str) -> Path:
    """
    Get the file path for a saved scaler.
    
    Args:
        dataset_name: Name of the dataset
        
    Returns:
        Path: Scaler file path
    """
    model_dir = ensure_directory_exists(settings.model_storage_path)
    return model_dir / f"{dataset_name}_scaler.pkl"


def get_config_path(dataset_name: str) -> Path:
    """
    Get the file path for model configuration.
    
    Args:
        dataset_name: Name of the dataset
        
    Returns:
        Path: Config file path
    """
    model_dir = ensure_directory_exists(settings.model_storage_path)
    return model_dir / f"{dataset_name}_config.json"


def save_json(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        file_path: File path
    """
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    logger.debug(f"Saved JSON to {file_path}")


def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load data from JSON file.
    
    Args:
        file_path: File path
        
    Returns:
        Dict: Loaded data
    """
    with open(file_path, 'r') as f:
        data = json.load(f)
    logger.debug(f"Loaded JSON from {file_path}")
    return data


def save_pickle(obj: Any, file_path: Union[str, Path]) -> None:
    """
    Save object to pickle file.
    
    Args:
        obj: Object to save
        file_path: File path
    """
    with open(file_path, 'wb') as f:
        pickle.dump(obj, f)
    logger.debug(f"Saved pickle to {file_path}")


def load_pickle(file_path: Union[str, Path]) -> Any:
    """
    Load object from pickle file.
    
    Args:
        file_path: File path
        
    Returns:
        Any: Loaded object
    """
    with open(file_path, 'rb') as f:
        obj = pickle.load(f)
    logger.debug(f"Loaded pickle from {file_path}")
    return obj


def calculate_percentage_deviation(
    actual: float,
    predicted: float
) -> float:
    """
    Calculate percentage deviation between actual and predicted values.
    
    Args:
        actual: Actual value
        predicted: Predicted value
        
    Returns:
        float: Percentage deviation
    """
    if predicted == 0:
        return 100.0 if actual != 0 else 0.0
    
    deviation = abs(actual - predicted) / abs(predicted) * 100
    return round(deviation, 2)


def is_anomaly(
    actual: float,
    predicted: float,
    threshold_percentage: float
) -> bool:
    """
    Check if actual value is an anomaly compared to predicted.
    
    Args:
        actual: Actual value
        predicted: Predicted value
        threshold_percentage: Threshold for anomaly detection
        
    Returns:
        bool: True if anomaly detected
    """
    deviation = calculate_percentage_deviation(actual, predicted)
    return deviation > threshold_percentage


def generate_time_features(timestamp: datetime) -> Dict[str, int]:
    """
    Generate time-based features from timestamp.
    
    Args:
        timestamp: Timestamp
        
    Returns:
        Dict: Time features
    """
    return {
        'hour': timestamp.hour,
        'minute': timestamp.minute,
        'day_of_week': timestamp.weekday(),
        'day_of_month': timestamp.day,
        'month': timestamp.month,
        'is_weekend': 1 if timestamp.weekday() >= 5 else 0,
        'is_business_hour': 1 if 9 <= timestamp.hour <= 17 else 0
    }


def create_sequences(
    data: np.ndarray,
    sequence_length: int
) -> tuple[np.ndarray, np.ndarray]:
    """
    Create sequences for time series prediction.
    
    Args:
        data: Input data array
        sequence_length: Length of each sequence
        
    Returns:
        tuple: (X sequences, y targets)
    """
    X, y = [], []
    
    for i in range(len(data) - sequence_length):
        X.append(data[i:i + sequence_length])
        y.append(data[i + sequence_length])
    
    return np.array(X), np.array(y)


def normalize_data(
    data: np.ndarray,
    scaler: Optional[MinMaxScaler] = None
) -> tuple[np.ndarray, MinMaxScaler]:
    """
    Normalize data using MinMaxScaler.
    
    Args:
        data: Input data
        scaler: Optional pre-fitted scaler
        
    Returns:
        tuple: (normalized data, scaler)
    """
    if scaler is None:
        scaler = MinMaxScaler(feature_range=(0, 1))
        normalized = scaler.fit_transform(data.reshape(-1, 1))
    else:
        normalized = scaler.transform(data.reshape(-1, 1))
    
    return normalized.flatten(), scaler


def denormalize_data(
    data: np.ndarray,
    scaler: MinMaxScaler
) -> np.ndarray:
    """
    Denormalize data using fitted scaler.
    
    Args:
        data: Normalized data
        scaler: Fitted scaler
        
    Returns:
        np.ndarray: Denormalized data
    """
    return scaler.inverse_transform(data.reshape(-1, 1)).flatten()


def validate_dataframe(
    df: pd.DataFrame,
    required_columns: List[str]
) -> tuple[bool, Optional[str]]:
    """
    Validate DataFrame has required columns.
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Returns:
        tuple: (is_valid, error_message)
    """
    missing_columns = set(required_columns) - set(df.columns)
    
    if missing_columns:
        return False, f"Missing required columns: {missing_columns}"
    
    return True, None


def parse_timestamp(
    timestamp: Union[str, datetime]
) -> datetime:
    """
    Parse timestamp string or datetime object.
    
    Args:
        timestamp: Timestamp string or datetime
        
    Returns:
        datetime: Parsed datetime
    """
    if isinstance(timestamp, datetime):
        return timestamp
    
    # Try common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ"
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(timestamp, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse timestamp: {timestamp}")


def generate_dataset_hash(dataset_name: str, file_path: str) -> str:
    """
    Generate unique hash for dataset.
    
    Args:
        dataset_name: Dataset name
        file_path: File path
        
    Returns:
        str: Hash string
    """
    content = f"{dataset_name}:{file_path}:{datetime.now().isoformat()}"
    return hashlib.md5(content.encode()).hexdigest()


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray
) -> Dict[str, float]:
    """
    Calculate regression metrics.
    
    Args:
        y_true: True values
        y_pred: Predicted values
        
    Returns:
        Dict: Metrics dictionary
    """
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)
    
    # Mean Absolute Percentage Error
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    
    return {
        'mae': round(float(mae), 4),
        'mse': round(float(mse), 4),
        'rmse': round(float(rmse), 4),
        'r2': round(float(r2), 4),
        'mape': round(float(mape), 4)
    }


def get_time_range(
    start_time: datetime,
    end_time: datetime,
    interval_minutes: int = 1
) -> List[datetime]:
    """
    Generate list of timestamps in a time range.
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        interval_minutes: Interval in minutes
        
    Returns:
        List[datetime]: List of timestamps
    """
    timestamps = []
    current = start_time
    
    while current <= end_time:
        timestamps.append(current)
        current += timedelta(minutes=interval_minutes)
    
    return timestamps


def format_alert_message(
    dataset_name: str,
    actual: float,
    predicted: float,
    deviation: float,
    timestamp: datetime
) -> str:
    """
    Format alert message.
    
    Args:
        dataset_name: Dataset name
        actual: Actual value
        predicted: Predicted value
        deviation: Deviation percentage
        timestamp: Timestamp
        
    Returns:
        str: Formatted message
    """
    return (
        f"ALERT: {dataset_name} - "
        f"Deviation: {deviation:.2f}% | "
        f"Actual: {actual:.2f} | "
        f"Predicted: {predicted:.2f} | "
        f"Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    )


def truncate_string(text: str, max_length: int = 100) -> str:
    """
    Truncate string to maximum length.
    
    Args:
        text: Input text
        max_length: Maximum length
        
    Returns:
        str: Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
        
    Returns:
        float: Result
    """
    if denominator == 0:
        return default
    return numerator / denominator


def convert_to_serializable(obj: Any) -> Any:
    """
    Convert object to JSON-serializable format.
    
    Args:
        obj: Object to convert
        
    Returns:
        Any: Serializable object
    """
    if isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_to_serializable(item) for item in obj]
    return obj
