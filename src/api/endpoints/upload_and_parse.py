"""
Invoice upload and parsing API
One endpoint: upload PDF, get structured invoice data
"""

import uuid
import time
from datetime import timedelta
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from typing import Dict, Any
from uuid import uuid4
from loguru import logger

from src.api.security.jwt_auth import get_current_user
from src.cache.redis_cache import invoice_cache
from src.config.settings import app_settings
from src.core.pipeline.invoice_processor import InvoiceProcessor
from src.domain.models import InvoiceParseResponse
from src.utils.document_utils import document_utils

router = APIRouter()

SUPPORTED_MIMETYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/jpg",
    "image/webp",
    "image/bmp",
    "image/tiff",
    "image/heic",
    "image/heif",
]

@router.post(
    "/v1/invoice/parse",
    response_model=Dict[str, Any],
    summary="Upload, parse, and validate an invoice document (PDF or Image)",
    description="""
    Parse an invoice document using PaddleOCR + Gemini Text pipeline:

    - **Processing method**: PaddleOCR/PPStructure + Gemini Text API
    - **Speed**: Fast processing (~5-10s typical on CPU)
    - **Accuracy**: High quality with table recognition and layout analysis
    - **Cost-effective**: Text-based processing

    Example:
    - `POST /api/v1/invoice/parse`
    """,
    tags=["Invoices"]
)
async def upload_and_parse_invoice(
    file: UploadFile = File(..., description="Invoice document (PDF or image file)"),
    user: str = Depends(get_current_user)
):
    job_id = str(uuid4())
    logger.info(f"[Job {job_id}] Received file '{file.filename}' from user '{user['username']}'")

    if file.content_type not in SUPPORTED_MIMETYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Supported types are: {', '.join(SUPPORTED_MIMETYPES)}"
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    max_bytes = app_settings.invoice_processing.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds the {app_settings.invoice_processing.MAX_FILE_SIZE_MB} MB limit."
        )

    # Caching is currently enabled only for PDFs due to reliable hashing.
    if file.content_type == "application/pdf":
        file_hash = document_utils.calculate_file_hash(file_bytes)
        cached_invoice = await invoice_cache.get_cached_invoice(file_hash)
        if cached_invoice:
            logger.info(f"[Job {job_id}] Cache HIT for PDF. Returning cached result.")
            processing_results = {
                "validation": {"is_valid": True, "quality_score": 100.0, "errors": [], "warnings": []},
                "processing_method": "cache_hit",
                "total_processing_time": 0.01,
                "document_info": document_utils.extract_document_info(file_bytes, file_hash)
            }
            response = InvoiceParseResponse(
                invoice=cached_invoice,
                processing_results=processing_results,
                user=user["username"],
                job_id=job_id
            )
            return response.model_dump()
        
        logger.info(f"[Job {job_id}] PDF Cache MISS. Starting full processing pipeline.")
    else:
        file_hash = None
        logger.info(f"[Job {job_id}] Image file detected. Starting full processing pipeline.")

    # Initialize processor (single mode: OCR + Gemini Text)
    processor = InvoiceProcessor()
    invoice_data, processing_results = await processor.process_invoice(
        file_bytes, file.content_type, document_hash=file_hash
    )

    # Check if invoice processing failed (validation error, parsing error, etc.)
    if invoice_data is None:
        logger.error(
            f"[Job {job_id}] Invoice processing failed - could not extract or validate invoice data. "
            f"Processing results: {processing_results}"
        )
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Failed to process invoice. The document may contain invalid data or unexpected formats.",
                "job_id": job_id,
                "processing_results": processing_results
            }
        )

    if file_hash:
        await invoice_cache.cache_invoice(file_hash, invoice_data)

    response = InvoiceParseResponse(
        invoice=invoice_data,
        processing_results=processing_results,
        user=user["username"],
        job_id=job_id
    )
    return response.model_dump()