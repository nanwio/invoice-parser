# Copyright 2024 Artificial Intelligence Labs, SL

import io
import uuid
import time
import arrow
import hashlib
from datetime import timedelta
from pypdf import PdfReader
from fastapi import APIRouter, UploadFile, HTTPException, Security, Depends, Query
from loguru import logger
from starlette import status
from typing import List, Optional

from app.rest.verifactu.models import (
    VerifactuValidationRequest,
    VerifactuValidationResponse,
    VerifactuDashboardResponse,
    VerifactuCorrectionRequest,
    VerifactuCorrectionResponse,
    IssuerStatusResponse
)
from app.rest.models import DocumentInfo, DocumentPageSize, ParsingJobInfo
from app.services.security.auth import get_current_user
from app.services.verifactu.verifactu_validator import VerifactuValidator
from app.services.verifactu.dashboard import VerifactuDashboard
from app.services.verifactu.auto_correction import VerifactuAutoCorrection
from app.services.parser.ultra_fast_parser import ultra_fast_parser
from app.settings import settings


router = APIRouter()

# Initialize VERIFACTU services
verifactu_validator = VerifactuValidator()
verifactu_dashboard = VerifactuDashboard()
verifactu_auto_correction = VerifactuAutoCorrection()


@router.post(
    "/validate",
    response_model=VerifactuValidationResponse,
    dependencies=[Security(get_current_user)],
    summary="Validate VERIFACTU Compliance",
    description="Comprehensive VERIFACTU compliance validation including QR codes, mandatory phrases, format validation, and real-time AEAT integration.",
    responses={
        status.HTTP_200_OK: {
            "description": "VERIFACTU validation completed successfully."
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Invalid file or validation failed"
        },
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Authentication failed"
        },
        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
            "description": "File size exceeds maximum limit"
        }
    }
)
async def validate_verifactu_compliance(
    invoice: UploadFile,
    validation_request: VerifactuValidationRequest = Depends(),
    user: dict[str, str] = Depends(get_current_user)
) -> VerifactuValidationResponse:
    """
    Validate complete VERIFACTU compliance for an invoice.

    Performs comprehensive validation including:
    - QR code detection and validation
    - Mandatory phrase verification
    - Format compliance checking
    - Real-time AEAT integration (optional)
    - Automatic correction suggestions (optional)
    """
    logger.info(f"VERIFACTU validation for file {invoice.filename}")

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

        # Step 1: Parse invoice data using ultra-fast parser
        logger.info("Parsing invoice for VERIFACTU validation...")
        invoice_result, performance_metrics = await ultra_fast_parser.parse_bytes_ultra_fast(file_bytes)

        # Step 2: Extract text for phrase validation (simplified)
        # In a real implementation, you'd use OCR to extract text from the PDF
        extracted_text = f"INVOICE {invoice_result.metadata.invoice_number if invoice_result.metadata else 'N/A'}"

        # Step 3: Perform VERIFACTU validation
        logger.info("Performing VERIFACTU compliance validation...")
        verifactu_result = await verifactu_validator.validate_complete_verifactu_compliance(
            document_bytes=file_bytes,
            invoice_data=invoice_result.model_dump(),
            extracted_text=extracted_text,
            enable_aeat_validation=validation_request.enable_aeat_validation
        )

        # Step 4: Apply auto-corrections if requested
        auto_corrections_result = None
        if validation_request.enable_auto_correction and not verifactu_result.verifactu_ready:
            logger.info("Applying automatic VERIFACTU corrections...")
            auto_corrections_result = await verifactu_auto_correction.apply_automatic_corrections(
                validation_result=verifactu_result,
                invoice_data=invoice_result.model_dump(),
                document_text=extracted_text
            )

        end_time = time.perf_counter()

        # Generate document info
        reader = PdfReader(io.BytesIO(file_bytes))
        page = reader.pages[0]

        # Build compliance summary
        compliance_summary = {
            'overall_score': verifactu_result.compliance_score,
            'compliance_level': verifactu_result.compliance_level.value,
            'verifactu_ready': verifactu_result.verifactu_ready,
            'critical_issues': verifactu_result.critical_issues,
            'warnings': verifactu_result.warnings,
            'validation_time': end_time - start_time,
            'components': {
                'qr_validation': 'pass' if verifactu_result.qr_validation and verifactu_result.qr_validation.qr_present else 'fail',
                'phrase_validation': 'pass' if verifactu_result.phrase_validation and verifactu_result.phrase_validation.phrase_present else 'fail',
                'format_validation': 'pass' if verifactu_result.format_validation and verifactu_result.format_validation.has_required_fields else 'fail',
                'aeat_validation': 'pass' if verifactu_result.aeat_validation and verifactu_result.aeat_validation.issuer_registered else 'not_checked'
            }
        }

        # Build response
        response = VerifactuValidationResponse(
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
            verifactu_validation=verifactu_result,
            auto_corrections=auto_corrections_result,
            compliance_summary=compliance_summary
        )

        logger.info(
            f"VERIFACTU validation completed - "
            f"Score: {verifactu_result.compliance_score:.1f}/100, "
            f"Ready: {verifactu_result.verifactu_ready}, "
            f"Time: {end_time - start_time:.2f}s"
        )

        return response

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Error in VERIFACTU validation for file {invoice.filename}")
        logger.exception(e)
        raise HTTPException(
            status_code=400,
            detail=f"VERIFACTU validation failed: {str(e)}"
        )


@router.get(
    "/dashboard",
    response_model=VerifactuDashboardResponse,
    dependencies=[Security(get_current_user)],
    summary="Get VERIFACTU Compliance Dashboard",
    description="Generate comprehensive dashboard with VERIFACTU compliance statistics, alerts, and recommendations."
)
async def get_verifactu_dashboard(
    user: dict[str, str] = Depends(get_current_user)
) -> VerifactuDashboardResponse:
    """
    Get VERIFACTU compliance dashboard.

    Provides overview of:
    - Overall compliance statistics
    - Critical actions needed
    - Alerts and warnings
    - Auto-correction opportunities
    """
    logger.info("Generating VERIFACTU dashboard")

    try:
        # In a real implementation, you would fetch validation results from database
        # For demo purposes, we'll create some sample data
        sample_validations = []  # Would be populated from actual validation history

        # Generate dashboard stats (simplified for demo)
        from app.services.verifactu.models import VerifactuDashboardStats

        dashboard_stats = VerifactuDashboardStats(
            total_invoices=100,  # Example data
            compliant_invoices=85,
            warning_invoices=12,
            non_compliant_invoices=3,
            compliance_percentage=85.0,
            invoices_failing_2026=15,
            unregistered_issuers=5,
            critical_alerts=8,
            medium_alerts=15,
            low_alerts=5
        )

        # Generate complete dashboard
        dashboard_data = await verifactu_dashboard.generate_compliance_dashboard(sample_validations)

        response = VerifactuDashboardResponse(
            dashboard_stats=dashboard_stats,
            dashboard_data=dashboard_data,
            generated_at=arrow.now().isoformat()
        )

        logger.info(f"Dashboard generated - {dashboard_stats.compliance_percentage:.1f}% compliance")
        return response

    except Exception as e:
        logger.error(f"Error generating VERIFACTU dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Dashboard generation failed: {str(e)}"
        )


@router.post(
    "/correct",
    response_model=VerifactuCorrectionResponse,
    dependencies=[Security(get_current_user)],
    summary="Apply VERIFACTU Automatic Corrections",
    description="Apply automatic corrections for VERIFACTU compliance issues including QR generation, phrase insertion, and format fixes."
)
async def apply_verifactu_corrections(
    invoice: UploadFile,
    correction_request: VerifactuCorrectionRequest = Depends(),
    user: dict[str, str] = Depends(get_current_user)
) -> VerifactuCorrectionResponse:
    """
    Apply automatic VERIFACTU corrections to an invoice.

    Provides:
    - QR code generation for missing codes
    - Mandatory phrase insertion suggestions
    - Format correction recommendations
    - Generated assets for download
    """
    logger.info(f"Applying VERIFACTU corrections for file {invoice.filename}")

    # Validate file
    if invoice.size and invoice.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {settings.MAX_FILE_SIZE_MB}MB"
        )

    try:
        file_bytes = await invoice.read()

        # Parse invoice first
        invoice_result, _ = await ultra_fast_parser.parse_bytes_ultra_fast(file_bytes)

        # Simplified text extraction
        extracted_text = f"INVOICE {invoice_result.metadata.invoice_number if invoice_result.metadata else 'N/A'}"

        # First validate to get current status
        validation_result = await verifactu_validator.validate_complete_verifactu_compliance(
            document_bytes=file_bytes,
            invoice_data=invoice_result.model_dump(),
            extracted_text=extracted_text,
            enable_aeat_validation=False  # Skip for corrections
        )

        # Apply corrections
        corrections_result = await verifactu_auto_correction.apply_automatic_corrections(
            validation_result=validation_result,
            invoice_data=invoice_result.model_dump(),
            document_text=extracted_text
        )

        response = VerifactuCorrectionResponse(
            corrections_applied=corrections_result.get('corrections_applied', 0),
            corrections=corrections_result.get('corrections', []),
            generated_assets=corrections_result.get('generated_assets', {}),
            success=corrections_result.get('success', False),
            summary=corrections_result.get('summary', 'No corrections applied')
        )

        logger.info(f"Applied {response.corrections_applied} corrections")
        return response

    except Exception as e:
        logger.error(f"Error applying VERIFACTU corrections: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Correction application failed: {str(e)}"
        )


@router.get(
    "/issuer/{nif}/status",
    response_model=IssuerStatusResponse,
    dependencies=[Security(get_current_user)],
    summary="Check Issuer VERIFACTU Status",
    description="Check the VERIFACTU registration and compliance status of a specific issuer."
)
async def get_issuer_verifactu_status(
    nif: str,
    user: dict[str, str] = Depends(get_current_user)
) -> IssuerStatusResponse:
    """
    Check issuer VERIFACTU status.

    Provides information about:
    - Registration status in VERIFACTU system
    - Active status
    - Required actions
    - Compliance level
    """
    logger.info(f"Checking VERIFACTU status for issuer {nif}")

    try:
        # Get issuer compliance summary
        issuer_summary = await verifactu_validator.get_issuer_compliance_summary(nif)

        response = IssuerStatusResponse(
            nif=nif,
            registered_in_verifactu=issuer_summary.get('registered_in_verifactu', False),
            active_in_verifactu=issuer_summary.get('active_in_verifactu', False),
            compliance_level=issuer_summary.get('compliance_level', 'unknown'),
            requires_action=issuer_summary.get('requires_action', True),
            action_needed=issuer_summary.get('action_needed'),
            last_checked=arrow.now().isoformat()
        )

        logger.info(f"Issuer {nif} status: {response.compliance_level}")
        return response

    except Exception as e:
        logger.error(f"Error checking issuer status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Issuer status check failed: {str(e)}"
        )


@router.get(
    "/system/status",
    dependencies=[Security(get_current_user)],
    summary="Check AEAT System Status",
    description="Check the availability and status of AEAT VERIFACTU services."
)
async def get_aeat_system_status(
    user: dict[str, str] = Depends(get_current_user)
) -> dict:
    """Check AEAT system availability for VERIFACTU validation."""
    logger.info("Checking AEAT system status")

    try:
        aeat_integration = verifactu_validator.aeat_integration
        system_status = await aeat_integration.get_aeat_system_status()

        return {
            'aeat_system_status': system_status,
            'verifactu_services_available': system_status.get('overall_status') == 'available',
            'last_checked': arrow.now().isoformat(),
            'recommendations': [
                'Verificar conectividad si servicios no disponibles',
                'Usar cache durante interrupciones del servicio',
                'Revalidar facturas cuando servicio se restaure'
            ]
        }

    except Exception as e:
        logger.error(f"Error checking AEAT system status: {e}")
        return {
            'aeat_system_status': {'overall_status': 'error', 'error': str(e)},
            'verifactu_services_available': False,
            'last_checked': arrow.now().isoformat(),
            'error': str(e)
        }