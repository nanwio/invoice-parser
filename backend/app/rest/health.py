# Copyright 2024 Artificial Intelligence Labs, SL

from typing import Dict, Any
from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/metrics",
    summary="API metrics endpoint",
    description="Get metrics about API usage and performance",
    response_model=Dict[str, Any]
)
async def metrics() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": "1.0.0"
    }