# Copyright 2024 Artificial Intelligence Labs, SL

import io
import uuid
import time
import arrow
import hashlib

from datetime import timedelta
from PyPDF2 import PdfReader
from fastapi import APIRouter, UploadFile, HTTPException, Security, Depends
from loguru import logger
from starlette import status

from app.rest.models import ParsingResult, DocumentInfo, DocumentPageSize, ParsingJobInfo
from app.rest.parser.docs import INVOICE_PARSING_RESULT_EXAMPLE

from app.services.security.auth import get_current_user
from app.services.cache import cache_service
from app.services.classifier import document_classifier
from app.services.parser import invoice_parser
from app.settings import settings


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
        file_hash = hashlib.sha256(file_bytes).hexdigest()
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
        reader = PdfReader(io.BytesIO(file_bytes))
        page = reader.pages[0]
        
        # Build result
        result = ParsingResult(
            document=DocumentInfo(
                hash=file_hash,
                num_pages=len(reader.pages),
                page_size=DocumentPageSize.from_mediabox(page.mediabox),
            ),
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
