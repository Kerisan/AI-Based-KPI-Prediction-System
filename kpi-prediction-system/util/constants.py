"""
Constants used throughout the application.
"""

from enum import Enum


class ModelType(str, Enum):
    """Supported model types."""
    LSTM = "LSTM"
    GRU = "GRU"
    TRANSFORMER = "TRANSFORMER"
    ARIMA = "ARIMA"


class AlertStatus(str, Enum):
    """Alert status types."""
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    MONITORING = "MONITORING"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DatasetStatus(str, Enum):
    """Dataset processing status."""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ModelStatus(str, Enum):
    """Model training status."""
    UNTRAINED = "UNTRAINED"
    TRAINING = "TRAINING"
    TRAINED = "TRAINED"
    FAILED = "FAILED"


# API Configuration
API_V1_PREFIX = "/api/v1"
API_TITLE = "KPI Prediction System API"
API_DESCRIPTION = "AI-based system for predicting and monitoring KPI metrics"

# Model Configuration
DEFAULT_SEQUENCE_LENGTH = 60  # minutes
DEFAULT_HIDDEN_SIZE = 128
DEFAULT_NUM_LAYERS = 2
DEFAULT_DROPOUT = 0.2
DEFAULT_LEARNING_RATE = 0.001
DEFAULT_BATCH_SIZE = 32
DEFAULT_EPOCHS = 50
DEFAULT_VALIDATION_SPLIT = 0.2

# Alert Configuration
DEFAULT_THRESHOLD_PERCENTAGE = 50
DEFAULT_CONSECUTIVE_VIOLATIONS = 5
MIN_THRESHOLD_PERCENTAGE = 1.0
MAX_THRESHOLD_PERCENTAGE = 100.0
MIN_CONSECUTIVE_VIOLATIONS = 1
MAX_CONSECUTIVE_VIOLATIONS = 60

# Data Processing
FEATURE_COLUMNS = [
    "hour",
    "minute",
    "day_of_week",
    "is_weekend",
    "is_holiday",
    "month",
    "day_of_month"
]

TARGET_COLUMNS = [
    "traffic_count",
    "orders",
    "shipping",
    "delivered"
]

# Time Configuration
SECONDS_PER_MINUTE = 60
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7

# File Paths
MODEL_FILE_EXTENSION = ".h5"
SCALER_FILE_EXTENSION = ".pkl"
CONFIG_FILE_EXTENSION = ".json"

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# HTTP Status Messages
HTTP_200_MESSAGE = "Success"
HTTP_201_MESSAGE = "Created"
HTTP_400_MESSAGE = "Bad Request"
HTTP_404_MESSAGE = "Not Found"
HTTP_500_MESSAGE = "Internal Server Error"

# Cache Keys
CACHE_KEY_MODEL = "model:{dataset_name}"
CACHE_KEY_SCALER = "scaler:{dataset_name}"
CACHE_KEY_CONFIG = "config:{dataset_name}"
CACHE_KEY_ALERT = "alert:{dataset_name}:{timestamp}"
CACHE_TTL_SECONDS = 3600  # 1 hour

# Validation
MAX_DATASET_NAME_LENGTH = 100
MAX_FILE_SIZE_MB = 500
ALLOWED_FILE_EXTENSIONS = [".csv", ".json", ".parquet"]

# Performance
MAX_PREDICTION_BATCH_SIZE = 1000
MAX_CONCURRENT_TRAINING_JOBS = 3
REQUEST_TIMEOUT_SECONDS = 30

# Metrics
METRIC_NAMESPACE = "kpi_prediction"
METRIC_SUBSYSTEM = "model"
