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
]

@router.post(
    "/v1/invoice/parse",
    response_model=Dict[str, Any],
    summary="Upload, parse, and validate an invoice document (PDF or Image)",
    tags=["Invoices"]
)
async def upload_and_parse_invoice(
    file: UploadFile = File(...),
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
            response = InvoiceParseResponse(cached_invoice, processing_results, user["username"], job_id)
            return response.__dict__
        
        logger.info(f"[Job {job_id}] PDF Cache MISS. Starting full processing pipeline.")
    else:
        file_hash = None
        logger.info(f"[Job {job_id}] Image file detected. Starting full processing pipeline.")

    processor = InvoiceProcessor()
    invoice_data, processing_results = await processor.process_invoice(file_bytes, file.content_type)
    
    if file_hash:
        await invoice_cache.cache_invoice(file_hash, invoice_data)
    
    response = InvoiceParseResponse(invoice_data, processing_results, user["username"], job_id)
    return response.__dict__