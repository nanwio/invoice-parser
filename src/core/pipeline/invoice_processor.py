"""
Simplified Invoice processor (OCR + Gemini Text only)
One responsibility: coordinate the invoice processing pipeline
"""

import time
import asyncio
from typing import Tuple, Dict, Any
from loguru import logger
import tempfile
import os

from src.domain.models import Invoice
from src.services.ai.gemini_processor import GeminiInvoiceProcessor
from src.services.table_detection.processor import create_hybrid_processor
from src.domain.validation.orchestrator import InvoiceValidator
from src.domain.validation.validators.mathematical_validator import MathematicalValidator
from src.domain.corrections.orchestrator import CorrectionOrchestrator
from src.utils.document_utils import document_utils
from src.core.pipeline.utils.helpers import format_ocr_results_for_llm, cleanup_temp_file


class InvoiceProcessor:
    """
    Invoice processing pipeline with hybrid TATR + PaddleOCR:
    1. TATR: Detect table structures (cells with row/col indices)
    2. PaddleOCR: Extract text with bounding boxes
    3. Cell-Text Matching: Assign texts to cells using vectorized IoU
    4. Gemini Text: Structure extracted text into JSON
    5. Validation: Check financial data

    Single mode: Hybrid OCR → Gemini Text (no Vision mode)
    """

    def __init__(self):
        """Initialize processor with hybrid TATR + PaddleOCR pipeline."""
        self.gemini_processor = GeminiInvoiceProcessor()
        self.hybrid_processor = create_hybrid_processor()
        self.validator = InvoiceValidator()

        logger.info("InvoiceProcessor initialized with TATR + PaddleOCR hybrid pipeline")


    async def process_invoice(self, document_bytes: bytes, content_type: str) -> tuple[Invoice, dict]:
        """
        Processes an invoice using hybrid TATR + PaddleOCR + Gemini pipeline.

        Workflow:
        1. TATR: Detect table structures (GPU-accelerated)
        2. PaddleOCR: Extract text with bounding boxes (GPU-accelerated)
        3. Cell-Text Matching: Assign texts to cells (vectorized IoU)
        4. Gemini Text: Structure extracted text into Invoice JSON
        5. Corrections: Apply financial corrections
        6. Validation: Validate structured data

        Args:
            document_bytes: Raw document bytes
            content_type: MIME type (application/pdf or image/*)

        Returns:
            Tuple of (Invoice object, processing metadata dict)
        """
        start_time = time.perf_counter()
        logger.info(f"Starting invoice processing (OCR mode) for content type: {content_type}")

        ocr_time = 0.0
        structuring_time = 0.0
        correction_time = 0.0
        validation_time = 0.0

        try:
            # Step 1: Extract tables and text with TATR + PaddleOCR hybrid pipeline
            logger.info("Step 1/5: Extracting tables with TATR + PaddleOCR")
            ocr_start = time.perf_counter()

            # Create temporary file for processing
            if content_type == "application/pdf":
                temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                temp_pdf.write(document_bytes)
                temp_pdf.close()

                try:
                    ocr_results = await self.hybrid_processor.process_pdf_async(temp_pdf.name)
                finally:
                    await cleanup_temp_file(temp_pdf.name)
            else:
                # Process image directly from bytes
                ocr_results = await self.hybrid_processor.process_image_async(document_bytes)

            ocr_time = time.perf_counter() - ocr_start
            logger.info(f"Hybrid extraction completed in {ocr_time:.2f}s, {len(ocr_results)} page(s)")

            # Step 2: Format extracted text for Gemini
            logger.info("Step 2/5: Structuring data with Gemini Text")
            structuring_start = time.perf_counter()

            formatted_text = format_ocr_results_for_llm(ocr_results)

            # Log table summary
            total_tables = sum(r.get('table_count', 0) for r in ocr_results)
            logger.info(f"Hybrid extraction summary: {len(ocr_results)} pages, {total_tables} tables, {len(formatted_text)} chars")

            for idx, result in enumerate(ocr_results, 1):
                logger.info(f"  Page {idx}: {result.get('table_count', 0)} tables, "
                           f"{result.get('region_count', 0)} regions, "
                           f"{len(result.get('text', ''))} chars")

            # DEBUG: Log FULL extracted text when enabled (use env var DEBUG_OCR_OUTPUT=true)
            from src.config.settings import app_settings
            if app_settings.invoice_processing.DEBUG_OCR_OUTPUT:
                logger.info("="*80)
                logger.info("FULL EXTRACTED TEXT (TATR + PaddleOCR - DEBUG MODE):")
                logger.info("="*80)
                logger.info(formatted_text)
                logger.info("="*80)

            invoice, gemini_metadata = await self.gemini_processor.structure_invoice_data_from_text(formatted_text)

            structuring_time = time.perf_counter() - structuring_start

            # Check if Gemini extraction failed
            if invoice is None:
                logger.error("Gemini failed to extract valid invoice data")
                return None, {
                    **gemini_metadata,
                    "document_hash": "N/A for non-PDF files",
                    "processing_method": "tatr_paddleocr_gemini_text",
                    "total_processing_time": time.perf_counter() - start_time,
                    "performance_breakdown": {
                        "ocr_time": ocr_time,
                        "structuring_time": structuring_time,
                        "correction_time": 0,
                        "validation_time": 0
                    }
                }

            # Step 3: Apply financial corrections
            logger.info("Step 3/5: Applying intelligent financial corrections")
            correction_start = time.perf_counter()
            invoice = CorrectionOrchestrator.apply_all_corrections(invoice)
            correction_time = time.perf_counter() - correction_start

            # Step 4: Mathematical validation (with auto-correction)
            logger.info("Step 4/5: Applying mathematical validation")
            math_validation_start = time.perf_counter()
            math_validation_result = MathematicalValidator.validate(invoice, auto_correct=True)
            math_validation_time = time.perf_counter() - math_validation_start

            if not math_validation_result.is_valid:
                logger.warning(f"Mathematical validation found {len(math_validation_result.issues)} issues")
                for issue in math_validation_result.issues:
                    logger.warning(f"  [{issue.severity}] {issue.field}: {issue.message}")

            if math_validation_result.corrections_applied > 0:
                logger.info(f"Applied {math_validation_result.corrections_applied} automatic corrections")

            # Step 5: Semantic validation
            logger.info("Step 5/5: Validating structured data")
            validation_start = time.perf_counter()
            validation_result = self.validator.validate_invoice(invoice)
            validation_time = time.perf_counter() - validation_start

        except Exception as e:
            logger.error(f"Invoice processing failed: {e}")
            raise e

        total_time = time.perf_counter() - start_time

        logger.info(
            f"Invoice processed in {total_time:.2f}s "
            f"(OCR={ocr_time:.2f}s, structure={structuring_time:.2f}s, "
            f"correction={correction_time:.2f}s, math_val={math_validation_time:.2f}s, validation={validation_time:.2f}s)"
        )

        processing_results = {
            **gemini_metadata,
            "validation": validation_result.to_dict(),
            "mathematical_validation": math_validation_result.to_dict(),
            "document_hash": "N/A for non-PDF files",
            "processing_method": "tatr_paddleocr_gemini_text",
            "total_processing_time": total_time,
            "performance_breakdown": {
                "ocr_time": ocr_time,
                "structuring_time": structuring_time,
                "correction_time": correction_time,
                "mathematical_validation_time": math_validation_time,
                "validation_time": validation_time
            }
        }

        return invoice, processing_results
