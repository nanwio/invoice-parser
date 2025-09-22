# Copyright 2024 Artificial Intelligence Labs, SL

"""
Multi-mode invoice processor - SIMPLE and FOCUSED
One responsibility: coordinate different processing modes
"""

import time
from typing import Tuple, Dict, Any
from loguru import logger

from invoice_processing.models.invoice_data import Invoice
from invoice_processing.ai_services.gemini_processor import GeminiInvoiceProcessor
from invoice_processing.ai_services.donut_processor import DonutOCRProcessor
from invoice_processing.validation.invoice_checker import InvoiceValidator, QuickValidator
from invoice_processing.classification.document_classifier import document_classifier
from invoice_processing.utilities.document_utils import document_utils


class MultiModeInvoiceProcessor:
    """
    Processes invoices using different modes for speed vs accuracy tradeoffs.

    Modes:
    - lightning: Ultra-fast with minimal validation
    - fast: DONUT OCR with Gemini fallback
    - enhanced: Full Gemini processing with complete validation
    """

    def __init__(self):
        """Initialize all processors."""
        self.gemini_processor = GeminiInvoiceProcessor()
        self.donut_processor = DonutOCRProcessor()
        self.full_validator = InvoiceValidator()
        self.quick_validator = QuickValidator()

    async def process_invoice(self, pdf_bytes: bytes, mode: str = "fast") -> Tuple[Invoice, Dict[str, Any]]:
        """
        Process invoice using specified mode.

        Args:
            pdf_bytes: Raw PDF file bytes
            mode: Processing mode ('lightning', 'fast', 'enhanced')

        Returns:
            Tuple of (Invoice object, processing results with metrics)
        """
        start_time = time.perf_counter()
        logger.info(f"Processing invoice in {mode} mode")

        try:
            if mode == "lightning":
                result = await self._process_lightning(pdf_bytes)
            elif mode == "fast":
                result = await self._process_fast(pdf_bytes)
            elif mode == "enhanced":
                result = await self._process_enhanced(pdf_bytes)
            else:
                raise ValueError(f"Unknown processing mode: {mode}")

            # Add timing information
            total_time = time.perf_counter() - start_time
            result[1]["total_processing_time"] = total_time
            result[1]["mode_used"] = mode

            logger.info(f"Invoice processed successfully in {total_time:.2f}s using {mode} mode")
            return result

        except Exception as e:
            logger.error(f"Invoice processing failed in {mode} mode: {e}")
            raise

    async def _process_lightning(self, pdf_bytes: bytes) -> Tuple[Invoice, Dict[str, Any]]:
        """Lightning mode: Ultra-fast Gemini processing with minimal validation."""
        # Extract with Gemini in lightning mode
        invoice, gemini_metadata = await self.gemini_processor.extract_invoice_data(pdf_bytes, "lightning")

        # Quick validation only
        validation_result = self.quick_validator.validate_invoice(invoice)

        return invoice, {
            **gemini_metadata,
            "validation": validation_result.to_dict(),
            "processing_method": "lightning_gemini"
        }

    async def _process_fast(self, pdf_bytes: bytes) -> Tuple[Invoice, Dict[str, Any]]:
        """Fast mode: DONUT OCR first, Gemini fallback if needed."""
        # Try DONUT first
        donut_invoice, donut_metadata = await self.donut_processor.extract_invoice_data(pdf_bytes)

        if donut_metadata["success"] and donut_invoice:
            # DONUT succeeded, use quick validation
            validation_result = self.quick_validator.validate_invoice(donut_invoice)

            return donut_invoice, {
                **donut_metadata,
                "validation": validation_result.to_dict(),
                "processing_method": "donut_primary"
            }
        else:
            # DONUT failed, fallback to Gemini
            logger.info("DONUT failed, falling back to Gemini")
            invoice, gemini_metadata = await self.gemini_processor.extract_invoice_data(pdf_bytes, "fast")
            validation_result = self.quick_validator.validate_invoice(invoice)

            return invoice, {
                **gemini_metadata,
                "validation": validation_result.to_dict(),
                "processing_method": "gemini_fallback",
                "donut_attempted": True,
                "donut_error": donut_metadata.get("error")
            }

    async def _process_enhanced(self, pdf_bytes: bytes) -> Tuple[Invoice, Dict[str, Any]]:
        """Enhanced mode: Full Gemini processing with complete validation."""
        # Extract with Gemini in enhanced mode
        invoice, gemini_metadata = await self.gemini_processor.extract_invoice_data(pdf_bytes, "enhanced")

        # Full validation
        validation_result = self.full_validator.validate_invoice(invoice)

        return invoice, {
            **gemini_metadata,
            "validation": validation_result.to_dict(),
            "processing_method": "enhanced_gemini"
        }