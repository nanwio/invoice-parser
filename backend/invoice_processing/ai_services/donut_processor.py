# Copyright 2024 Artificial Intelligence Labs, SL

"""
DONUT OCR processor - SIMPLE and FOCUSED
One responsibility: process invoices using DONUT model for OCR
"""

import asyncio
from typing import Tuple, Dict, Any, Optional
from loguru import logger

from invoice_processing.models.invoice_data import Invoice
from invoice_processing.ai_services.ocr_engines.donut_model import donut_model
from invoice_processing.ai_services.ocr_engines.pdf_converter import pdf_converter


class DonutOCRProcessor:
    """
    Processes invoices using DONUT OCR model.
    Fast alternative to Gemini for simple invoices.
    """

    def __init__(self):
        """Initialize DONUT processor."""
        pass

    async def extract_invoice_data(self, pdf_bytes: bytes) -> Tuple[Optional[Invoice], Dict[str, Any]]:
        """
        Extract invoice data using DONUT OCR.

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            Tuple of (Invoice object or None, processing metadata)
        """
        logger.info("Processing invoice with DONUT OCR")

        try:
            # Load model if needed
            if not await donut_model.load_model():
                return None, {"success": False, "method": "donut_ocr", "error": "Model loading failed"}

            # Process PDF with DONUT
            extracted_data = await self._process_with_donut(pdf_bytes)

            if extracted_data and extracted_data.get("confidence", 0) > 0.5:
                invoice = self._convert_to_invoice(extracted_data)
                metadata = {
                    "success": True,
                    "method": "donut_ocr",
                    "confidence": extracted_data.get("confidence", 0.8)
                }
                return invoice, metadata
            else:
                return None, {"success": False, "method": "donut_ocr", "error": "Low confidence extraction"}

        except Exception as e:
            logger.error(f"DONUT processing failed: {e}")
            return None, {"success": False, "method": "donut_ocr", "error": str(e)}

    async def _process_with_donut(self, pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Process PDF with DONUT model.
        Real implementation using OCR engines.
        """
        try:
            # Convert PDF to images
            images = pdf_converter.pdf_to_images(pdf_bytes)
            if not images:
                logger.warning("No images extracted from PDF")
                return None

            # Process first page (can be enhanced for multi-page)
            first_page = pdf_converter.resize_for_donut(images[0])

            # Extract text with DONUT
            extracted_data = await donut_model.extract_text(first_page)

            return extracted_data

        except Exception as e:
            logger.error(f"DONUT processing error: {e}")
            return None

    def _convert_to_invoice(self, donut_data: Dict[str, Any]) -> Invoice:
        """Convert DONUT extracted data to Invoice object."""
        from invoice_processing.utilities.invoice_builder import invoice_builder
        return invoice_builder.build_from_data(donut_data)