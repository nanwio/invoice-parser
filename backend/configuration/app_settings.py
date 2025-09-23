"""
Application settings - SIMPLE and CLEAR
Every setting is self-explanatory
"""

import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from typing import Optional

load_dotenv()


class InvoiceProcessingSettings(BaseSettings):
    """Settings for invoice processing features."""

    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: list[str] = ["application/pdf"]
    PROCESSING_TIMEOUT_SECONDS: int = 30


class AIModelSettings(BaseSettings):
    """Settings for AI model configuration."""

    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash"
    GEMINI_TEMPERATURE: float = 0.1  # Lower = faster
    GEMINI_MAX_TOKENS: int = 2000   # Limit for speed

class DatabaseSettings(BaseSettings):
    """Settings for database and caching."""

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_ENABLED: bool = True


class SecuritySettings(BaseSettings):
    """Settings for security features."""

    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "default-dev-key")


class AppSettings(BaseSettings):
    """Main application settings container."""

    invoice_processing: InvoiceProcessingSettings = InvoiceProcessingSettings()
    ai_model: AIModelSettings = AIModelSettings()
    database: DatabaseSettings = DatabaseSettings()
    security: SecuritySettings = SecuritySettings()

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'

app_settings = AppSettings()