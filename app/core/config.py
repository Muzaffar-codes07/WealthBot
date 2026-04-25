"""
WealthBot Configuration Module
==============================
Centralized configuration management using Pydantic Settings.
"""

from functools import lru_cache
from typing import ClassVar

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Follows 12-factor app methodology for configuration management.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    app_env: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=False, description="Debug mode flag")
    log_level: str = Field(default="INFO", description="Logging level")

    # -------------------------------------------------------------------------
    # Database Configuration
    # -------------------------------------------------------------------------
    database_url: str = Field(
        default="",
        description="Async PostgreSQL connection string (set in .env)",
    )
    db_pool_size: int = Field(default=5, description="Database connection pool size")
    db_max_overflow: int = Field(default=10, description="Max overflow connections")
    db_pool_timeout: int = Field(default=30, description="Pool connection timeout")

    # -------------------------------------------------------------------------
    # Security Settings
    # -------------------------------------------------------------------------
    secret_key: str = Field(
        default="",
        description="Secret key for JWT encoding (set in .env)",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days",
    )

    # -------------------------------------------------------------------------
    # CORS Configuration
    # -------------------------------------------------------------------------
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins",
    )
    trusted_hosts: str = Field(
        default="localhost,127.0.0.1,test,testserver",
        description="Comma-separated list of trusted host headers",
    )
    gzip_minimum_size: int = Field(
        default=1024,
        description="Minimum response size in bytes before GZip compression",
    )
    hsts_max_age: int = Field(
        default=31536000,
        description="Strict-Transport-Security max-age value in seconds",
    )

    # -------------------------------------------------------------------------
    # Observability (Sentry)
    # -------------------------------------------------------------------------
    sentry_dsn: str = Field(
        default="",
        description="Sentry DSN for error tracking (leave empty to disable)",
    )
    sentry_enabled: bool = Field(
        default=False,
        description="Enable Sentry error tracking",
    )
    sentry_traces_sample_rate: float = Field(
        default=0.1,
        description="Sentry performance traces sample rate (0.0 to 1.0)",
    )

    # -------------------------------------------------------------------------
    # Redis Configuration
    # -------------------------------------------------------------------------
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL",
    )
    redis_enabled: bool = Field(
        default=False,
        description="Enable Redis for rate limiting and caching",
    )
    prediction_cache_ttl: int = Field(
        default=300,
        description="Safe-to-Spend prediction cache TTL in seconds",
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins string into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def trusted_hosts_list(self) -> list[str]:
        """Parse trusted hosts string into a list."""
        return [host.strip() for host in self.trusted_hosts.split(",") if host.strip()]

    # -------------------------------------------------------------------------
    # ML Model Configuration
    # -------------------------------------------------------------------------
    model_path: str = Field(
        default="./ml/models/xgboost_spending_model.pkl",
        description="Path to the XGBoost model artifact (legacy pkl)",
    )
    xgboost_onnx_path: str = Field(
        default="./ml/models/xgboost_spending.onnx",
        description="Path to the XGBoost ONNX spending model",
    )
    categorizer_onnx_path: str = Field(
        default="./ml/models/categorizer.onnx",
        description="Path to the DistilBERT ONNX categorizer model",
    )
    tokenizer_path: str = Field(
        default="./ml/models/tokenizer",
        description="Path to the tokenizer directory",
    )
    label_encoder_path: str = Field(
        default="./ml/models/label_encoder.json",
        description="Path to the label encoder JSON",
    )
    feature_config_path: str = Field(
        default="./ml/models/feature_config.json",
        description="Path to the feature config JSON",
    )
    transformer_model_name: str = Field(
        default="distilbert-base-uncased",
        description="Hugging Face transformer model name",
    )

    # -------------------------------------------------------------------------
    # PII Protection (GDPR/SOC 2 Compliance)
    # -------------------------------------------------------------------------
    enable_pii_masking: bool = Field(
        default=True,
        description="Enable PII masking in logs and responses",
    )
    data_retention_days: int = Field(
        default=365,
        description="Data retention period in days",
    )
    encryption_key: str = Field(
        default="",
        description="Encryption key for sensitive data",
    )

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return upper_v

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Ensure app environment is valid."""
        valid_envs = {"development", "staging", "production", "testing"}
        lower_v = v.lower()
        if lower_v not in valid_envs:
            raise ValueError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return lower_v

    # ClassVar so Pydantic v2 treats this as a true class constant, not a
    # PrivateAttr (underscore-prefixed bare attrs become unwrappable PrivateAttr
    # instances and iterating them raises TypeError at validator time).
    _INSECURE_SECRET_MARKERS: ClassVar[tuple[str, ...]] = (
        "change",
        "changeme",
        "dev-secret",
        "insecure",
        "placeholder",
        "secret-key",
        "your-secret",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Reject empty, too-short, or well-known insecure secret keys in non-dev environments.

        Runs unconditionally at Settings instantiation; use env var SKIP_SECRET_VALIDATION=1
        only in CI smoke-tests where a stable dev secret is intentional.
        """
        import os

        if os.getenv("SKIP_SECRET_VALIDATION") == "1":
            return v
        app_env = (os.getenv("APP_ENV") or "development").lower()
        if app_env in ("staging", "production"):
            if not v:
                raise ValueError(
                    "SECRET_KEY is not set. It is required in staging/production."
                )
            if len(v) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters in staging/production."
                )
            low = v.lower()
            if any(marker in low for marker in cls._INSECURE_SECRET_MARKERS):
                raise ValueError(
                    "SECRET_KEY contains a well-known insecure marker. "
                    "Generate a fresh random key for staging/production."
                )
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL is provided."""
        if not v:
            raise ValueError(
                "DATABASE_URL is not set. "
                "Copy .env.example to .env and configure your database URL."
            )
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Create cached settings instance.

    Uses LRU cache to ensure settings are only loaded once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
