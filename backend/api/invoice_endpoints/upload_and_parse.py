# Copyright 2024 Artificial Intelligence Labs, SL

"""
Invoice upload and parsing API - SIMPLE and FOCUSED
One endpoint: upload PDF, get structured invoice data
"""

import uuid
import time
from datetime import timedelta
from fastapi import APIRouter, UploadFile, HTTPException, Depends
from loguru import logger

from invoice_processing.parsing.multi_mode_processor import InvoiceProcessor
from invoice_processing.caching.redis_cache import invoice_cache
from invoice_processing.classification.document_classifier import document_classifier
from invoice_processing.utilities.document_utils import document_utils
from api.security.jwt_auth import get_current_user
from configuration.app_settings import app_settings


router = APIRouter(prefix="/v1/invoice", tags=["Invoice Processing"])


class InvoiceParseResponse:
    """Standard response for a parsed invoice."""

    def __init__(self, invoice_data, processing_results, user, job_id):
        self.success = True
        self.job_id = job_id
        self.invoice_data = invoice_data
        self.validation = processing_results.get("validation", {})
        self.processing_method = processing_results.get("processing_method", "unknown")
        self.processing_time_seconds = processing_results.get("total_processing_time", 0.0)
        self.document_info = processing_results.get("document_info", {})
        self.user = user


@router.post("/parse", status_code=200)
async def parse_invoice(
    file: UploadFile,
    user: dict[str, str] = Depends(get_current_user)
) -> dict:
    """
    Uploads a PDF invoice, processes it through the pipeline, and returns structured data.
    This is the single, canonical endpoint for all invoice processing.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    if file.size > app_settings.invoice_processing.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {app_settings.invoice_processing.MAX_FILE_SIZE_MB}MB."
        )

    try:
        job_id = str(uuid.uuid4())
        logger.info(f"[Job {job_id}] Processing new file: {file.filename}")
        
        file_bytes = await file.read()
        file_hash = document_utils.calculate_file_hash(file_bytes)
        
        # 1. Check cache
        cached_invoice = await invoice_cache.get_cached_invoice(file_hash)
        if cached_invoice:
            logger.info(f"[Job {job_id}] Cache HIT. Returning cached result.")
            processing_results = {
                "validation": {"is_valid": True, "quality_score": 100.0, "errors": [], "warnings": []},
                "processing_method": "cache_hit",
                "total_processing_time": 0.01, # Simulate small cache access time
                "document_info": document_utils.extract_document_info(file_bytes, file_hash)
            }
            response = InvoiceParseResponse(cached_invoice, processing_results, user["username"], job_id)
            return response.__dict__

        logger.info(f"[Job {job_id}] Cache MISS. Starting full processing pipeline.")
        
        # 2. Classify document
        classification = await document_classifier.classify_bytes(file_bytes)
        if not classification.is_invoice:
            raise HTTPException(
                status_code=422,
                detail=f"Document is not an invoice. Detected: {classification.document_type}."
            )

        # 3. Process with the single, optimized processor
        processor = InvoiceProcessor()
        invoice_data, processing_results = await processor.process_invoice(file_bytes)
        
        # 4. Cache the new result
        await invoice_cache.cache_invoice(file_hash, invoice_data)
        
        # 5. Build and return response
        processing_results["document_info"] = document_utils.extract_document_info(file_bytes, file_hash)
        response = InvoiceParseResponse(invoice_data, processing_results, user["username"], job_id)
        
        logger.info(f"[Job {job_id}] Processing successful in {response.processing_time_seconds:.2f}s.")
        return response.__dict__

    except HTTPException as http_exc:
        # Re-raise HTTP exceptions to let FastAPI handle them
        raise http_exc
    except Exception as e:
        logger.error(f"A critical error occurred during invoice processing: {e}")
        raise HTTPException(status_code=500, detail="A critical error occurred during processing.")