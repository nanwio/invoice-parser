# Copyright 2024 Artificial Intelligence Labs, SL

"""
Health check endpoint - SIMPLE
One responsibility: check if the API is alive
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Simple health check endpoint."""
    return {
        "status": "healthy",
        "service": "invoice_processing_api",
        "version": "1.0.0"
    }