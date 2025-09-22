# Copyright 2024 Artificial Intelligence Labs, SL

"""
Gemini AI processor - SIMPLE and FOCUSED
One responsibility: communicate with Gemini AI for invoice extraction
"""

import base64
import instructor
from typing import Tuple, Dict, Any
from google import genai
from loguru import logger

from invoice_processing.models.invoice_data import Invoice
from configuration.app_settings import app_settings


class GeminiInvoiceProcessor:
    """
    Processes invoices using Google Gemini AI.
    Simple wrapper around Gemini API with instructor.
    """

    def __init__(self):
        """Initialize Gemini client with optimal settings."""
        self._setup_client()

    def _setup_client(self):
        """Set up Gemini client with instructor."""
        self._client = genai.Client(api_key=app_settings.ai_model.GEMINI_API_KEY)
        self._instructor = instructor.from_genai(
            self._client,
            mode=instructor.Mode.GENAI_TOOLS,
            use_async=True
        )

    async def extract_invoice_data(self, pdf_bytes: bytes, mode: str = "standard") -> Tuple[Invoice, Dict[str, Any]]:
        """
        Extract structured invoice data from PDF using Gemini.

        Args:
            pdf_bytes: Raw PDF file bytes
            mode: Processing mode ('lightning', 'fast', 'enhanced')

        Returns:
            Tuple of (Invoice object, processing metadata)
        """
        logger.info(f"Processing invoice with Gemini in {mode} mode")

        try:
            # Prepare PDF for Gemini
            b64_pdf = base64.b64encode(pdf_bytes).decode()

            # Select prompt based on mode
            prompt = self._get_prompt_for_mode(mode)

            # Process with Gemini
            invoice = await self._instructor.chat.completions.create(
                model=app_settings.ai_model.GEMINI_MODEL_NAME,
                messages=[{
                    "role": "user",
                    "content": [
                        prompt,
                        {"type": "application/pdf", "data": b64_pdf}
                    ]
                }],
                response_model=Invoice,
                temperature=app_settings.ai_model.GEMINI_TEMPERATURE,
                max_tokens=app_settings.ai_model.GEMINI_MAX_TOKENS
            )

            metadata = {
                "success": True,
                "mode_used": mode,
                "model": app_settings.ai_model.GEMINI_MODEL_NAME
            }

            return invoice, metadata

        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
            raise

    def _get_prompt_for_mode(self, mode: str) -> str:
        """Get extraction prompt based on processing mode."""
        if mode == "lightning":
            return """FAST: Extract key invoice data quickly:
            - Vendor and customer names
            - Invoice number, date, total amount
            - Main line items
            Speed is priority."""

        elif mode == "enhanced":
            return """DETAILED: Extract ALL invoice information with maximum precision:
            - Complete vendor/customer details with addresses
            - All line items with descriptions, quantities, prices
            - Tax calculations and payment methods
            - Dates, references, and notes
            Accuracy is priority."""

        else:  # fast/standard
            return """Extract complete invoice information:
            - Vendor and customer details
            - Invoice metadata (number, dates)
            - All line items and financial totals
            - Tax information
            Balance of speed and accuracy."""