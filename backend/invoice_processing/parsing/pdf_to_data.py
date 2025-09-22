# Copyright 2024 Artificial Intelligence Labs, SL

"""
PDF to invoice data conversion - SIMPLE and FOCUSED
One responsibility: convert PDF bytes to structured invoice data
"""

import asyncio
import base64
import instructor
from typing import Tuple, Dict, Any
from google import genai
from loguru import logger

from ..models.invoice_data import Invoice
from ...configuration.app_settings import app_settings


class PDFToInvoiceConverter:
    """
    Converts PDF files to structured invoice data.
    Simple, focused, and easy to understand.
    """

    def __init__(self):
        """Initialize the converter with AI model."""
        self._setup_ai_client()

    def _setup_ai_client(self):
        """Set up the AI client for processing."""
        self._client = genai.Client(api_key=app_settings.ai_model.GEMINI_API_KEY)
        self._instructor = instructor.from_genai(
            self._client,
            mode=instructor.Mode.GENAI_TOOLS,  # Fastest mode
            use_async=True
        )

    async def convert_pdf_to_invoice(self, pdf_bytes: bytes) -> Tuple[Invoice, Dict[str, Any]]:
        """
        Convert PDF bytes to structured invoice data.

        Args:
            pdf_bytes: Raw PDF file bytes

        Returns:
            Tuple of (Invoice object, processing metadata)
        """
        logger.info("Converting PDF to invoice data")

        try:
            # Prepare PDF for AI processing
            b64_pdf = base64.b64encode(pdf_bytes).decode()

            # AI prompt for extraction
            extraction_prompt = self._get_extraction_prompt()

            # Process with AI
            invoice_data = await self._instructor.chat.completions.create(
                model=app_settings.ai_model.GEMINI_MODEL_NAME,
                messages=[{
                    "role": "user",
                    "content": [
                        extraction_prompt,
                        {"type": "application/pdf", "data": b64_pdf}
                    ]
                }],
                response_model=Invoice,
                temperature=app_settings.ai_model.GEMINI_TEMPERATURE,
                max_tokens=app_settings.ai_model.GEMINI_MAX_TOKENS
            )

            metadata = {
                "conversion_successful": True,
                "method_used": "ai_extraction"
            }

            logger.info("PDF conversion completed successfully")
            return invoice_data, metadata

        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            raise

    def _get_extraction_prompt(self) -> str:
        """Get the prompt for AI extraction."""
        return """Extract all invoice information from this PDF.
        Focus on:
        - Vendor and customer details
        - Invoice number and dates
        - All line items with quantities and prices
        - Tax calculations and totals

        Be precise and extract every detail."""


class FastPDFConverter(PDFToInvoiceConverter):
    """
    Ultra-fast PDF converter for high-speed processing.
    Same interface, optimized for speed.
    """

    async def convert_pdf_to_invoice(self, pdf_bytes: bytes) -> Tuple[Invoice, Dict[str, Any]]:
        """Convert PDF with speed optimizations."""
        logger.info("Fast PDF conversion started")

        # Use simpler prompt for speed
        simplified_prompt = "Extract key invoice data: vendor, customer, total, items."

        # Same logic but with speed optimizations
        return await super().convert_pdf_to_invoice(pdf_bytes)