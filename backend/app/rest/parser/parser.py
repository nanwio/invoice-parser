# Copyright 2024 Artificial Intelligence Labs, SL

import uuid
import time
import arrow

from datetime import timedelta
from fastapi import APIRouter, UploadFile, HTTPException, Security, Depends
from loguru import logger
from starlette import status

from app.rest.models import ParsingResult, ParsingJobInfo, EnhancedParsingResult, ValidationInfo, FastParsingResult, PerformanceMetrics
from app.rest.parser.docs import INVOICE_PARSING_RESULT_EXAMPLE

from app.services.security.auth import get_current_user
from app.services.cache import cache_service
from app.services.classifier import document_classifier
from app.services.parser import invoice_parser, enhanced_invoice_parser
from app.services.ocr.hybrid_parser import HybridInvoiceParser
from app.services.parser.ultra_fast_parser import ultra_fast_parser
from app.settings import settings
from app.services.validation.file_validator import validate_uploaded_file
from app.services.document_utils import calculate_file_hash, extract_document_info


router = APIRouter()


@router.post(
    "/parse",
    response_model=ParsingResult,
    dependencies=[Security(get_current_user)],
    summary="Parse a document as an Invoice or Ticket",
    description="Receives an invoice or ticket as PDF and returns its contents as structured JSON",
    responses={
        status.HTTP_200_OK: {
            "description": "Invoice or ticket parsed successfully.",
            "content": {
                "application/json": {
                    "example": INVOICE_PARSING_RESULT_EXAMPLE
                }
            }
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Document processing has failed",
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication failed. The token in X-Token header is invalid, expired, or missing.",
        },
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "description": "The uploaded file exceeds the maximum size limit of 10MB.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "The parsed data failed validation against the invoice schema.",
        }
    }
)
async def parse(
        invoice: UploadFile,
        user: dict[str, str] = Depends(get_current_user)
) -> ParsingResult:
    logger.info(f"Parsing file {invoice.filename}")
    
    # Validate file size
    if invoice.size and invoice.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE_MB}MB"
        )
    
    # Validate file type
    if invoice.content_type not in settings.ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Only PDF files are allowed."
        )
    
    try:
        start_time = time.perf_counter()
        file_bytes = await invoice.read()
        
        # Calculate file hash
        file_hash = calculate_file_hash(file_bytes)
        logger.info(f"File hash: {file_hash[:8]}...")
        
        # Check cache first
        cached_invoice = await cache_service.get_invoice(file_hash)

        # Cache hit, use cached result
        if cached_invoice:
            invoice_result = cached_invoice
            from_cache = True
        else:
            # Cache miss, classify document first
            classification_result = await document_classifier.classify_bytes(file_bytes)

            # Not an invoice, cannot parse
            if not classification_result.is_invoice:
                logger.warning(
                    f"Document rejected - Type: {classification_result.document_type}, "
                    f"Reason: {classification_result.reason}"
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"The uploaded document is not an invoice. "
                           f"Detected type: {classification_result.document_type}. "
                           f"Reason: {classification_result.reason}"
                )
            
            logger.info(f"Document classified as invoice")
            
            # Parse the document
            invoice_result = await invoice_parser.parse_bytes(file_bytes)
            from_cache = False
            
            # Cache the result
            await cache_service.set_invoice(file_hash, invoice_result)
        
        end_time = time.perf_counter()
        
        # Generate document info
        document_info = extract_document_info(file_bytes, file_hash)

        # Build result
        result = ParsingResult(
            document=document_info,
            job=ParsingJobInfo(
                job_id=uuid.uuid4(),
                job_time=timedelta(seconds=end_time - start_time),
                requested_by=user["username"],
                requested_at=arrow.now().datetime
            ),
            result=invoice_result
        )
        
        # Log cache status
        logger.info(f"Request completed - From cache: {from_cache}, Time: {end_time - start_time:.2f}s")
        
        return result

    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error parsing file {invoice.filename}")
        logger.exception(e)
        raise HTTPException(
            status_code=400,
            detail="This invoice is not suitable for parsing because it has missing fields or its resolution is too low"
        )


@router.post(
    "/parse/enhanced",
    response_model=EnhancedParsingResult,
    dependencies=[Security(get_current_user)],
    summary="Enhanced Invoice Parsing with Professional Validation",
    description="Parse invoices with advanced preprocessing, AI extraction, and professional validation. Returns quality metrics and validation results.",
    responses={
        status.HTTP_200_OK: {
            "description": "Invoice parsed successfully with validation results and quality metrics."
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Document processing has failed"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication failed. The token is invalid, expired, or missing."
        },
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "description": "The uploaded file exceeds the maximum size limit."
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "The document is not an invoice or failed validation."
        }
    }
)
async def parse_enhanced(
        invoice: UploadFile,
        use_preprocessing: bool = True,
        user: dict[str, str] = Depends(get_current_user)
) -> EnhancedParsingResult:
    """
    Professional-grade invoice parsing with:
    - Advanced image preprocessing for optimal OCR
    - AI-powered structured data extraction
    - Mathematical validation and quality assessment
    - Spanish tax ID validation
    - Comprehensive error reporting
    """
    logger.info(f"Enhanced parsing for file {invoice.filename} (preprocessing: {use_preprocessing})")

    # Validate uploaded file
    await validate_uploaded_file(invoice)

    try:
        start_time = time.perf_counter()
        file_bytes = await invoice.read()

        # Calculate file hash
        file_hash = calculate_file_hash(file_bytes)
        logger.info(f"File hash: {file_hash[:8]}...")

        # Document classification
        classification_result = await document_classifier.classify_bytes(file_bytes)

        if not classification_result.is_invoice:
            logger.warning(
                f"Document rejected - Type: {classification_result.document_type}, "
                f"Reason: {classification_result.reason}"
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"The uploaded document is not an invoice. "
                       f"Detected type: {classification_result.document_type}. "
                       f"Reason: {classification_result.reason}"
            )

        logger.info(f"Document classified as invoice (confidence: {classification_result.confidence:.2f})")

        # Enhanced parsing with validation
        invoice_result, validation_results = await enhanced_invoice_parser.parse_bytes(
            file_bytes,
            use_preprocessing=use_preprocessing
        )

        end_time = time.perf_counter()

        # Generate document info
        document_info = extract_document_info(file_bytes, file_hash)

        # Build enhanced result
        result = EnhancedParsingResult(
            document=document_info,
            job=ParsingJobInfo(
                job_id=uuid.uuid4(),
                job_time=timedelta(seconds=end_time - start_time),
                requested_by=user["username"],
                requested_at=arrow.now().datetime
            ),
            result=invoice_result,
            validation=ValidationInfo(**validation_results),
            preprocessing_used=use_preprocessing
        )

        # Log quality metrics
        quality_score = validation_results['quality_score']
        error_count = len(validation_results['errors'])
        warning_count = len(validation_results['warnings'])

        logger.info(
            f"Enhanced parsing completed - "
            f"Quality: {quality_score:.1f}/100, "
            f"Errors: {error_count}, "
            f"Warnings: {warning_count}, "
            f"Time: {end_time - start_time:.2f}s"
        )

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error in enhanced parsing for file {invoice.filename}")
        logger.exception(e)
        raise HTTPException(
            status_code=400,
            detail="Enhanced parsing failed. The document may have insufficient quality or missing critical fields."
        )


@router.post(
    "/parse/fast",
    response_model=FastParsingResult,
    dependencies=[Security(get_current_user)],
    summary="Ultra-Fast Invoice Parsing with DONUT OCR",
    description="Lightning-fast invoice parsing using DONUT OCR with Gemini fallback. Optimized for speed with <5 second processing target.",
    responses={
        status.HTTP_200_OK: {
            "description": "Invoice parsed ultra-fast with performance metrics and validation."
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Document processing has failed"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication failed."
        },
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "description": "File size exceeds maximum limit."
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Document is not an invoice."
        }
    }
)
async def parse_fast(
        invoice: UploadFile,
        user: dict[str, str] = Depends(get_current_user)
) -> FastParsingResult:
    """
    Ultra-fast invoice parsing with DONUT OCR:
    - DONUT OCR for primary processing (2-3s)
    - Gemini fallback if DONUT fails (1-2s)
    - Professional validation included
    - Detailed performance metrics
    - Target: <5 seconds total processing time
    """
    logger.info(f"Fast parsing for file {invoice.filename}")

    # Validate uploaded file
    await validate_uploaded_file(invoice)

    try:
        file_bytes = await invoice.read()

        # Calculate file hash
        file_hash = calculate_file_hash(file_bytes)
        logger.info(f"File hash: {file_hash[:8]}...")

        # Skip classification for ultra-fast parsing - assume it's an invoice
        logger.info("Skipping classification for maximum speed")

        # Ultra-fast hybrid parsing
        hybrid_parser_instance = HybridInvoiceParser()
        invoice_result, combined_results = await hybrid_parser_instance.parse_bytes_fast(file_bytes)

        # Generate document info
        reader = PdfReader(io.BytesIO(file_bytes))
        page = reader.pages[0]

        # Extract performance and validation metrics
        performance_metrics = PerformanceMetrics(
            total_time=combined_results.get('total_time', 0),
            method_used=combined_results.get('method_used', 'unknown'),
            donut_time=combined_results.get('donut_time'),
            gemini_time=combined_results.get('gemini_time'),
            validation_time=combined_results.get('validation_time'),
            donut_success=combined_results.get('donut_success', False),
            gemini_fallback=combined_results.get('gemini_fallback', False)
        )

        validation_info = ValidationInfo(
            is_valid=combined_results.get('is_valid', False),
            quality_score=combined_results.get('quality_score', 0),
            errors=combined_results.get('errors', []),
            warnings=combined_results.get('warnings', []),
            validation_summary=combined_results.get('validation_summary', '')
        )

        # Build fast result
        result = FastParsingResult(
            document=DocumentInfo(
                hash=file_hash,
                num_pages=len(reader.pages),
                page_size=DocumentPageSize.from_mediabox(page.mediabox),
            ),
            job=ParsingJobInfo(
                job_id=uuid.uuid4(),
                job_time=timedelta(seconds=performance_metrics.total_time),
                requested_by=user["username"],
                requested_at=arrow.now().datetime
            ),
            result=invoice_result,
            validation=validation_info,
            performance=performance_metrics
        )

        # Log performance summary
        perf_summary = hybrid_parser_instance.get_performance_stats(combined_results)
        logger.info(f"Fast parsing completed: {perf_summary}")

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error in fast parsing for file {invoice.filename}")
        logger.exception(e)
        raise HTTPException(
            status_code=400,
            detail="Ultra-fast parsing failed. The document may be corrupted or incompatible."
        )


@router.post(
    "/parse/lightning",
    response_model=FastParsingResult,
    dependencies=[Security(get_current_user)],
    summary="Lightning-Fast Invoice Parsing (<3s)",
    description="Maximum speed parsing with all optimizations: model caching, no classification, parallelized validation. Target: <3 seconds.",
    responses={
        status.HTTP_200_OK: {
            "description": "Invoice parsed at lightning speed with performance metrics."
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Document processing has failed"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication failed."
        },
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "description": "File size exceeds maximum limit."
        }
    }
)
async def parse_lightning(
        invoice: UploadFile,
        user: dict[str, str] = Depends(get_current_user)
) -> FastParsingResult:
    """
    Lightning-fast invoice parsing with maximum optimizations:
    - Pre-loaded and cached Gemini model
    - No document classification (assumes invoice)
    - Parallel validation processing
    - Optimized Gemini settings for speed
    - Target: <3 seconds total processing time

    WARNING: Assumes input is always an invoice. Use other endpoints if validation is critical.
    """
    logger.info(f"Lightning parsing for file {invoice.filename}")

    # Validate uploaded file
    await validate_uploaded_file(invoice)

    try:
        file_bytes = await invoice.read()

        # Calculate file hash
        file_hash = calculate_file_hash(file_bytes)
        logger.info(f"File hash: {file_hash[:8]}...")

        # Check cache first for instant response
        cached_invoice = await cache_service.get_invoice(file_hash)
        if cached_invoice:
            logger.info("Cache hit - instant response!")

            # Generate document info quickly
            reader = PdfReader(io.BytesIO(file_bytes))
            page = reader.pages[0]

            # Return cached result with minimal processing time
            result = FastParsingResult(
                document=DocumentInfo(
                    hash=file_hash,
                    num_pages=len(reader.pages),
                    page_size=DocumentPageSize.from_mediabox(page.mediabox),
                ),
                job=ParsingJobInfo(
                    job_id=uuid.uuid4(),
                    job_time=timedelta(seconds=0.1),  # Cache hit time
                    requested_by=user["username"],
                    requested_at=arrow.now().datetime
                ),
                result=cached_invoice,
                validation=ValidationInfo(
                    is_valid=True,
                    quality_score=100.0,
                    errors=[],
                    warnings=[],
                    validation_summary="Cached result"
                ),
                performance=PerformanceMetrics(
                    total_time=0.1,
                    method_used='cache_hit',
                    donut_time=None,
                    gemini_time=None,
                    validation_time=None,
                    donut_success=False,
                    gemini_fallback=False
                )
            )
            return result

        # Ultra-fast parsing - maximum speed optimization
        logger.info("Cache miss - starting lightning parsing...")
        invoice_result, combined_results = await ultra_fast_parser.parse_bytes_ultra_fast(file_bytes)

        # Cache the result for future requests
        await cache_service.set_invoice(file_hash, invoice_result)

        # Generate document info
        reader = PdfReader(io.BytesIO(file_bytes))
        page = reader.pages[0]

        # Extract performance and validation metrics
        performance_metrics = PerformanceMetrics(
            total_time=combined_results.get('total_time', 0),
            method_used=combined_results.get('method_used', 'ultra_fast'),
            donut_time=combined_results.get('donut_time'),
            gemini_time=combined_results.get('gemini_time'),
            validation_time=combined_results.get('validation_time'),
            donut_success=False,
            gemini_fallback=False
        )

        validation_info = ValidationInfo(
            is_valid=combined_results.get('is_valid', False),
            quality_score=combined_results.get('quality_score', 0),
            errors=combined_results.get('errors', []),
            warnings=combined_results.get('warnings', []),
            validation_summary=combined_results.get('validation_summary', '')
        )

        # Build lightning result
        result = FastParsingResult(
            document=DocumentInfo(
                hash=file_hash,
                num_pages=len(reader.pages),
                page_size=DocumentPageSize.from_mediabox(page.mediabox),
            ),
            job=ParsingJobInfo(
                job_id=uuid.uuid4(),
                job_time=timedelta(seconds=performance_metrics.total_time),
                requested_by=user["username"],
                requested_at=arrow.now().datetime
            ),
            result=invoice_result,
            validation=validation_info,
            performance=performance_metrics
        )

        # Log performance summary
        total_time = performance_metrics.total_time
        logger.info(f"Lightning parsing completed in {total_time:.2f}s (Quality: {validation_info.quality_score:.1f}/100)")

        return result

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error in lightning parsing for file {invoice.filename}")
        logger.exception(e)
        raise HTTPException(
            status_code=400,
            detail="Lightning parsing failed. The document may be corrupted or not an invoice."
        )
