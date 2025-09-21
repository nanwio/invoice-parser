# Copyright 2024 Artificial Intelligence Labs, SL

from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    # Security
    SECRET_KEY: str

    # Model Configuration
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-2.5-flash-lite"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True

    # Document Processing
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_MIME_TYPES: Optional[list[str]] = [
        "application/pdf"
    ]

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'


settings = Settings()
