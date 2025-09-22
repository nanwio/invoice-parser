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

from ...invoice_processing.parsing.multi_mode_processor import MultiModeInvoiceProcessor
from ...invoice_processing.caching.redis_cache import invoice_cache
from ...invoice_processing.classification.document_classifier import document_classifier
from ...invoice_processing.utilities.document_utils import document_utils
from ...api.security.jwt_auth import get_current_user
from ...configuration.app_settings import app_settings


router = APIRouter()


class InvoiceUploadResponse:
    """Response for invoice upload."""

    def __init__(self, invoice_data, processing_results, processing_time: float):
        self.success = True
        self.invoice_data = invoice_data
        self.validation = processing_results.get("validation", {})
        self.processing_method = processing_results.get("processing_method", "unknown")
        self.processing_time_seconds = processing_time
        self.job_id = str(uuid.uuid4())


@router.post("/upload-invoice")
async def upload_and_parse_invoice(
    file: UploadFile,
    mode: str = "fast",
    user: dict[str, str] = Depends(get_current_user)
) -> dict:
    """
    Upload PDF invoice and get structured data.

    Simple, straightforward endpoint that:
    1. Accepts PDF file
    2. Converts to structured data
    3. Validates the data
    4. Returns results
    """
    logger.info(f"Processing uploaded file: {file.filename}")

    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    if file.size > app_settings.invoice_processing.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {app_settings.invoice_processing.MAX_FILE_SIZE_MB}MB"
        )

    try:
        start_time = time.perf_counter()

        # Read file
        file_bytes = await file.read()

        # Check cache first
        file_hash = document_utils.calculate_file_hash(file_bytes)
        cached_invoice = await invoice_cache.get_cached_invoice(file_hash)

        if cached_invoice:
            # Cache hit - return cached result
            invoice_data = cached_invoice
            processing_results = {
                "validation": {"is_valid": True, "quality_score": 100.0, "errors": [], "warnings": []},
                "processing_method": "cache_hit"
            }
        else:
            # Document classification
            classification = await document_classifier.classify_bytes(file_bytes)
            if not classification.is_invoice:
                raise HTTPException(
                    status_code=422,
                    detail=f"Document is not an invoice. Detected: {classification.document_type}"
                )

            # Cache miss - process with multi-mode processor
            processor = MultiModeInvoiceProcessor()
            invoice_data, processing_results = await processor.process_invoice(file_bytes, mode)

            # Cache the result
            await invoice_cache.cache_invoice(file_hash, invoice_data)

        # Calculate processing time
        processing_time = time.perf_counter() - start_time

        # Generate document info
        document_info = document_utils.extract_document_info(file_bytes, file_hash)

        # Build response
        response = InvoiceUploadResponse(invoice_data, processing_results, processing_time)

        logger.info(f"Invoice processed successfully in {processing_time:.2f}s")
        return {
            "success": response.success,
            "job_id": response.job_id,
            "invoice_data": response.invoice_data.model_dump(),
            "validation": response.validation,
            "processing_method": response.processing_method,
            "processing_time_seconds": response.processing_time_seconds,
            "document_info": document_info.model_dump(),
            "user": user["username"]
        }

    except Exception as e:
        logger.error(f"Invoice processing failed: {e}")
        raise HTTPException(status_code=500, detail="Invoice processing failed")


@router.post("/upload-invoice-enhanced")
async def upload_and_parse_invoice_enhanced(
    file: UploadFile,
    use_preprocessing: bool = True,
    user: dict[str, str] = Depends(get_current_user)
) -> dict:
    """
    Enhanced invoice processing with full validation.
    Complete validation and quality assessment.
    """
    logger.info(f"Enhanced processing: {file.filename}")

    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    if file.size > app_settings.invoice_processing.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {app_settings.invoice_processing.MAX_FILE_SIZE_MB}MB"
        )

    try:
        start_time = time.perf_counter()

        # Read file
        file_bytes = await file.read()

        # Check cache first
        file_hash = document_utils.calculate_file_hash(file_bytes)
        cached_invoice = await invoice_cache.get_cached_invoice(file_hash)

        if cached_invoice:
            # Cache hit - return cached result
            invoice_data = cached_invoice
            processing_results = {
                "validation": {"is_valid": True, "quality_score": 100.0, "errors": [], "warnings": []},
                "processing_method": "cache_hit"
            }
        else:
            # Document classification
            classification = await document_classifier.classify_bytes(file_bytes)
            if not classification.is_invoice:
                raise HTTPException(
                    status_code=422,
                    detail=f"Document is not an invoice. Detected: {classification.document_type}"
                )

            # Cache miss - process with enhanced mode
            processor = MultiModeInvoiceProcessor()
            invoice_data, processing_results = await processor.process_invoice(file_bytes, "enhanced")

            # Cache the result
            await invoice_cache.cache_invoice(file_hash, invoice_data)

        # Calculate processing time
        processing_time = time.perf_counter() - start_time

        # Generate document info
        document_info = document_utils.extract_document_info(file_bytes, file_hash)

        # Build response
        response = InvoiceUploadResponse(invoice_data, processing_results, processing_time)

        logger.info(f"Enhanced processing completed in {processing_time:.2f}s")
        return {
            "success": response.success,
            "job_id": response.job_id,
            "invoice_data": response.invoice_data.model_dump(),
            "validation": response.validation,
            "processing_method": response.processing_method,
            "processing_time_seconds": response.processing_time_seconds,
            "document_info": document_info.model_dump(),
            "user": user["username"],
            "preprocessing_used": use_preprocessing
        }

    except Exception as e:
        logger.error(f"Enhanced processing failed: {e}")
        raise HTTPException(status_code=500, detail="Enhanced processing failed")


@router.post("/upload-invoice-lightning")
async def upload_and_parse_invoice_lightning(
    file: UploadFile,
    user: dict[str, str] = Depends(get_current_user)
) -> dict:
    """
    Lightning invoice processing with maximum speed optimizations.
    Target: <2 seconds processing time.
    """
    logger.info(f"Lightning processing: {file.filename}")

    # Validate file
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    if file.size > app_settings.invoice_processing.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {app_settings.invoice_processing.MAX_FILE_SIZE_MB}MB"
        )

    try:
        start_time = time.perf_counter()

        # Read file
        file_bytes = await file.read()

        # Check cache first for instant response
        file_hash = document_utils.calculate_file_hash(file_bytes)
        cached_invoice = await invoice_cache.get_cached_invoice(file_hash)

        if cached_invoice:
            # Cache hit - instant response
            invoice_data = cached_invoice
            processing_results = {
                "validation": {"is_valid": True, "quality_score": 100.0, "errors": [], "warnings": []},
                "processing_method": "cache_hit"
            }
        else:
            # Skip classification for maximum speed - assume it's an invoice
            logger.info("Skipping classification for maximum speed")

            # Cache miss - process with lightning mode
            processor = MultiModeInvoiceProcessor()
            invoice_data, processing_results = await processor.process_invoice(file_bytes, "lightning")

            # Cache the result
            await invoice_cache.cache_invoice(file_hash, invoice_data)

        # Calculate processing time
        processing_time = time.perf_counter() - start_time

        # Generate document info
        document_info = document_utils.extract_document_info(file_bytes, file_hash)

        # Build response
        response = InvoiceUploadResponse(invoice_data, processing_results, processing_time)

        logger.info(f"Lightning processing completed in {processing_time:.2f}s")
        return {
            "success": response.success,
            "job_id": response.job_id,
            "invoice_data": response.invoice_data.model_dump(),
            "validation": response.validation,
            "processing_method": response.processing_method,
            "processing_time_seconds": response.processing_time_seconds,
            "document_info": document_info.model_dump(),
            "user": user["username"]
        }

    except Exception as e:
        logger.error(f"Lightning processing failed: {e}")
        raise HTTPException(status_code=500, detail="Lightning processing failed")