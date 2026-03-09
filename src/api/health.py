"""
Health check endpoint
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