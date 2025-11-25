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
    DEBUG_OCR_OUTPUT: bool = os.getenv("DEBUG_OCR_OUTPUT", "false").lower() == "true"


class AIModelSettings(BaseSettings):
    """Settings for AI model configuration."""

    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash-lite"  # 40% faster, 50% fewer tokens
    GEMINI_TEMPERATURE: float = 0.0  # Zero for maximum speed and consistency
    GEMINI_MAX_TOKENS: int = 1500   # Reduced for speed (was 2000)

class DatabaseSettings(BaseSettings):
    """Settings for database and caching."""

    REDIS_URL: Optional[str] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_ENABLED: bool = True


class SecuritySettings(BaseSettings):
    """Settings for security features."""

    JWT_SECRET_KEY: str = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET_KEY", "dev-secret-change-in-production")


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