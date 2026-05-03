"""
Configuration management using Pydantic settings.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=()
    )
    
    # Application
    app_name: str = Field(default="KPI Prediction System", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    
    # Model Configuration
    model_type: str = Field(default="LSTM", alias="MODEL_TYPE")
    sequence_length: int = Field(default=60, alias="SEQUENCE_LENGTH")
    hidden_size: int = Field(default=128, alias="HIDDEN_SIZE")
    num_layers: int = Field(default=2, alias="NUM_LAYERS")
    dropout: float = Field(default=0.2, alias="DROPOUT")
    learning_rate: float = Field(default=0.001, alias="LEARNING_RATE")
    batch_size: int = Field(default=32, alias="BATCH_SIZE")
    epochs: int = Field(default=50, alias="EPOCHS")
    
    # Alert Configuration
    default_upper_threshold_percentage: float = Field(
        default=30.0, 
        alias="DEFAULT_UPPER_THRESHOLD_PERCENTAGE"
    )
    default_lower_threshold_percentage: float = Field(
        default=30.0, 
        alias="DEFAULT_LOWER_THRESHOLD_PERCENTAGE"
    )
    default_consecutive_violations: int = Field(
        default=5, 
        alias="DEFAULT_CONSECUTIVE_VIOLATIONS"
    )
    alert_check_interval: int = Field(default=60, alias="ALERT_CHECK_INTERVAL")
    
    # Database
    database_url: str = Field(
        default="sqlite:///./data/kpi_system.db", 
        alias="DATABASE_URL"
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    
    # Redis (Optional)
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    
    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: str = Field(default="logs/app.log", alias="LOG_FILE")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_rotation: str = Field(default="1 day", alias="LOG_ROTATION")
    log_retention: str = Field(default="30 days", alias="LOG_RETENTION")
    
    # Security (Optional)
    api_key_enabled: bool = Field(default=False, alias="API_KEY_ENABLED")
    api_key: Optional[str] = Field(default=None, alias="API_KEY")
    secret_key: str = Field(
        default="your-secret-key-change-in-production", 
        alias="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30, 
        alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(
        default=True, 
        alias="CORS_ALLOW_CREDENTIALS"
    )
    cors_allow_methods: List[str] = Field(default=["*"], alias="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], alias="CORS_ALLOW_HEADERS")
    
    # Storage
    model_storage_path: str = Field(default="data/models", alias="MODEL_STORAGE_PATH")
    dataset_storage_path: str = Field(
        default="data/datasets", 
        alias="DATASET_STORAGE_PATH"
    )
    
    # Performance
    max_workers: int = Field(default=4, alias="MAX_WORKERS")
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")
    
    # Monitoring
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")
    
    # Real-time Data Collection
    data_collection_interval: int = Field(default=60, alias="DATA_COLLECTION_INTERVAL")
    data_flush_interval: int = Field(default=3600, alias="DATA_FLUSH_INTERVAL")
    auto_train_threshold: int = Field(default=1000, alias="AUTO_TRAIN_THRESHOLD")

    
    # Email Configuration
    email_enabled: bool = Field(default=False, alias="EMAIL_ENABLED")
    smtp_server: str = Field(default="smtp.gmail.com", alias="SMTP_SERVER")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    sender_email: str = Field(default="", alias="SENDER_EMAIL")
    sender_password: str = Field(default="", alias="SENDER_PASSWORD")
    alert_recipient_emails: List[str] = Field(default=[], alias="ALERT_RECIPIENT_EMAILS")

    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v_upper
    
    @field_validator("dropout")
    @classmethod
    def validate_dropout(cls, v: float) -> float:
        """Validate dropout rate."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Dropout must be between 0.0 and 1.0")
        return v
    
    @field_validator("default_upper_threshold_percentage", "default_lower_threshold_percentage")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        """Validate threshold percentage."""
        if not 0.0 < v <= 100.0:
            raise ValueError("Threshold percentage must be between 0 and 100")
        return v
    
    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Returns:
        Settings: Application settings
    """
    return Settings()


# Global settings instance
settings = get_settings()
