# Copyright 2024 Artificial Intelligence Labs, SL

from fastapi import UploadFile, HTTPException
from starlette import status
from app.settings import settings


async def validate_uploaded_file(file: UploadFile) -> None:
    """
    Validate uploaded file size and content type.

    Args:
        file: The uploaded file to validate

    Raises:
        HTTPException: If file validation fails
    """
    # Validate file size
    if file.size and file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE_MB}MB"
        )

    # Validate file type
    if file.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only PDF files are allowed."
        )