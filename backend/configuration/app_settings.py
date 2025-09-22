# Copyright 2024 Artificial Intelligence Labs, SL

"""
Application settings - SIMPLE and CLEAR
Every setting is self-explanatory
"""

from pydantic_settings import BaseSettings
from typing import Optional


class InvoiceProcessingSettings(BaseSettings):
    """Settings for invoice processing features."""

    # File processing limits
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: list[str] = ["application/pdf"]
    PROCESSING_TIMEOUT_SECONDS: int = 30


class AIModelSettings(BaseSettings):
    """Settings for AI model configuration."""

    # Gemini AI configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.1  # Lower = faster
    GEMINI_MAX_TOKENS: int = 2000   # Limit for speed


class DatabaseSettings(BaseSettings):
    """Settings for database and caching."""

    # Redis cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True


class SecuritySettings(BaseSettings):
    """Settings for security features."""

    # JWT tokens
    SECRET_KEY: str


class AppSettings(BaseSettings):
    """Main application settings container."""

    # All settings in one place
    invoice_processing: InvoiceProcessingSettings = InvoiceProcessingSettings()
    ai_model: AIModelSettings = AIModelSettings()
    database: DatabaseSettings = DatabaseSettings()
    security: SecuritySettings = SecuritySettings()

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


# Global settings instance - ready to use
app_settings = AppSettings()