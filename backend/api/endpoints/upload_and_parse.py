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

from api.security.jwt_auth import get_current_user
from invoice_processing.caching.redis_cache import invoice_cache
from invoice_processing.parsing.invoice_pipeline import InvoiceProcessor
from invoice_processing.models.invoice_data import InvoiceParseResponse
from invoice_processing.utilities.document_utils import document_utils

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
    Parse an invoice document using either OCR or Vision mode:

    - **OCR mode** (default): Fast processing using PaddleOCR + Gemini Text (~2s)
      - Best for: Standard invoices, high-volume processing, cost-effectiveness
      - Method: Extract text with PaddleOCR → Structure with Gemini Text API

    - **Vision mode**: Accurate processing using Gemini Vision Multimodal (~7s)
      - Best for: Complex layouts, multi-page invoices, maximum accuracy
      - Method: Convert to images → Process with Gemini Vision API

    Query Parameters:
    - `mode`: "ocr" (default) or "vision"

    Example:
    - Fast: `POST /api/v1/invoice/parse?mode=ocr`
    - Accurate: `POST /api/v1/invoice/parse?mode=vision`
    """,
    tags=["Invoices"]
)
async def upload_and_parse_invoice(
    file: UploadFile = File(..., description="Invoice document (PDF or image file)"),
    mode: str = "ocr",  # Default to OCR mode for speed
    user: str = Depends(get_current_user)
):
    job_id = str(uuid4())
    logger.info(f"[Job {job_id}] Received file '{file.filename}' from user '{user['username']}' with mode='{mode}'")

    # Validate mode parameter
    if mode not in ["ocr", "vision"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Supported modes are: 'ocr' (fast, cost-effective) or 'vision' (slower, more accurate)"
        )

    if file.content_type not in SUPPORTED_MIMETYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Supported types are: {', '.join(SUPPORTED_MIMETYPES)}"
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

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

    # Initialize processor based on mode parameter
    use_vision = (mode == "vision")
    use_ocr_fallback = (mode == "ocr")  # Initialize PaddleOCR only in OCR mode

    processor = InvoiceProcessor(use_vision=use_vision, use_ocr_fallback=use_ocr_fallback)
    invoice_data, processing_results = await processor.process_invoice(file_bytes, file.content_type)

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