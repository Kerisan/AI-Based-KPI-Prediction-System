"""
Data models and schemas using Pydantic.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from util.constants import AlertSeverity, AlertStatus, ModelStatus


class TimeFeatures(BaseModel):
    """Time-based features for prediction."""
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    minute: int = Field(..., ge=0, le=59, description="Minute of hour (0-59)")
    day_of_week: int = Field(..., ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    day_of_month: int = Field(..., ge=1, le=31, description="Day of month")
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    is_weekend: int = Field(..., ge=0, le=1, description="Is weekend (0 or 1)")
    is_business_hour: int = Field(default=0, ge=0, le=1, description="Is business hour (0 or 1)")


class TrainingRequest(BaseModel):
    """Request model for training a new model."""
    dataset_name: str = Field(..., min_length=1, max_length=100, description="Unique dataset identifier")
    file_path: str = Field(..., description="Path to training data CSV file")
    target_column: str = Field(..., description="Name of target column to predict")
    epochs: int = Field(default=50, ge=1, le=1000, description="Number of training epochs")
    batch_size: int = Field(default=32, ge=1, le=512, description="Training batch size")
    validation_split: float = Field(default=0.2, ge=0.1, le=0.5, description="Validation split ratio")
    sequence_length: Optional[int] = Field(default=None, ge=10, le=1440, description="Sequence length in minutes")
    
    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate file path ends with .csv"""
        if not v.endswith('.csv'):
            raise ValueError("File path must end with .csv")
        return v


class TrainingResponse(BaseModel):
    """Response model for training completion."""
    model_config = ConfigDict(protected_namespaces=())
    
    dataset_name: str
    status: ModelStatus
    message: str
    metrics: Optional[Dict[str, float]] = None
    model_path: Optional[str] = None
    training_time_seconds: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class PredictionRequest(BaseModel):
    """Request model for making a prediction."""
    dataset_name: str = Field(..., description="Dataset identifier")
    timestamp: Optional[str] = Field(default=None, description="Timestamp for prediction (ISO format)")
    features: Optional[Dict[str, Any]] = Field(default=None, description="Optional manual features")
    use_current_time: bool = Field(default=True, description="Use current time if timestamp not provided")


class PredictionResponse(BaseModel):
    """Response model for prediction result."""
    model_config = ConfigDict(protected_namespaces=())
    
    dataset_name: str
    predicted_value: float
    timestamp: datetime
    confidence: Optional[float] = None
    features_used: Dict[str, Any]
    model_version: Optional[str] = None


class ComparisonRequest(BaseModel):
    """Request model for comparing actual vs predicted."""
    dataset_name: str = Field(..., description="Dataset identifier")
    actual_value: float = Field(..., description="Actual observed value")
    timestamp: Optional[str] = Field(default=None, description="Timestamp (ISO format)")
    auto_predict: bool = Field(default=True, description="Automatically generate prediction")


class ComparisonResponse(BaseModel):
    """Response model for comparison result."""
    dataset_name: str
    actual_value: float
    predicted_value: float
    deviation_percentage: float
    is_anomaly: bool
    threshold_percentage: float
    timestamp: datetime
    alert_triggered: bool = False
    alert_id: Optional[str] = None


class AlertConfig(BaseModel):
    """Alert configuration for a dataset."""
    dataset_name: str
    threshold_percentage: float = Field(..., ge=0.1, le=100.0, description="Deviation threshold %")
    consecutive_minutes: int = Field(..., ge=1, le=60, description="Required consecutive minutes")
    enabled: bool = Field(default=True, description="Alert enabled status")
    severity: AlertSeverity = Field(default=AlertSeverity.MEDIUM, description="Alert severity level")
    
    @field_validator('threshold_percentage')
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """Validate threshold is reasonable."""
        if v < 0.1 or v > 100.0:
            raise ValueError("Threshold must be between 0.1 and 100.0")
        return v


class AlertConfigResponse(BaseModel):
    """Response model for alert configuration."""
    dataset_name: str
    threshold_percentage: float
    consecutive_minutes: int
    enabled: bool
    severity: AlertSeverity
    updated_at: datetime = Field(default_factory=datetime.now)


class Alert(BaseModel):
    """Alert model."""
    alert_id: str
    dataset_name: str
    status: AlertStatus
    severity: AlertSeverity
    actual_value: float
    predicted_value: float
    deviation_percentage: float
    consecutive_count: int
    threshold_percentage: float
    required_consecutive: int
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    message: str
    metadata: Optional[Dict[str, Any]] = None


class AlertListResponse(BaseModel):
    """Response model for listing alerts."""
    alerts: List[Alert]
    total_count: int
    active_count: int
    resolved_count: int


class ModelInfo(BaseModel):
    """Model information."""
    model_config = ConfigDict(protected_namespaces=())
    
    dataset_name: str
    model_type: str
    status: ModelStatus
    target_column: str
    sequence_length: int
    trained_at: Optional[datetime] = None
    metrics: Optional[Dict[str, float]] = None
    model_path: Optional[str] = None
    scaler_path: Optional[str] = None


class ModelListResponse(BaseModel):
    """Response model for listing models."""
    models: List[ModelInfo]
    total_count: int


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str
    uptime_seconds: Optional[float] = None
    models_loaded: int = 0
    active_alerts: int = 0


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    path: Optional[str] = None


class DatasetInfo(BaseModel):
    """Dataset information."""
    dataset_name: str
    file_path: str
    target_column: str
    total_records: int
    date_range: Optional[Dict[str, str]] = None
    columns: List[str]
    created_at: datetime = Field(default_factory=datetime.now)


class BatchPredictionRequest(BaseModel):
    """Request for batch predictions."""
    dataset_name: str
    timestamps: List[str] = Field(..., min_length=1, max_length=1000)
    
    @field_validator('timestamps')
    @classmethod
    def validate_timestamps(cls, v: List[str]) -> List[str]:
        """Validate timestamp list is not too large."""
        if len(v) > 1000:
            raise ValueError("Maximum 1000 timestamps per batch")
        return v


class BatchPredictionResponse(BaseModel):
    """Response for batch predictions."""
    dataset_name: str
    predictions: List[Dict[str, Any]]
    total_count: int
    successful_count: int
    failed_count: int


class MetricsResponse(BaseModel):
    """Model performance metrics."""
    dataset_name: str
    metrics: Dict[str, float]
    evaluation_date: datetime = Field(default_factory=datetime.now)
    sample_size: int


class SystemStats(BaseModel):
    """System statistics."""
    total_models: int
    total_predictions_today: int
    total_alerts_today: int
    active_alerts: int
    system_uptime_seconds: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.now)
