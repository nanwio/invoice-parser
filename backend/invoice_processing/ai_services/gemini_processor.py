# Copyright 2024 Artificial Intelligence Labs, SL

"""
Gemini AI processor - SIMPLE and FOCUSED
One responsibility: communicate with Gemini AI for invoice extraction
"""

from typing import Tuple, Dict, Any, Optional
from loguru import logger

from invoice_processing.models.invoice_data import Invoice
from invoice_processing.ai_services.gemini_engines.gemini_client import GeminiClient
from invoice_processing.ai_services.gemini_engines.invoice_parser import invoice_parser
from configuration.app_settings import app_settings


class GeminiInvoiceProcessor:
    """
    Processes invoices using Google Gemini AI.
    Simple, reliable implementation.
    """

    def __init__(self):
        """Initialize Gemini processor."""
        self._client = GeminiClient(
            api_key=app_settings.ai_model.GEMINI_API_KEY,
            model_name=app_settings.ai_model.GEMINI_MODEL_NAME
        )

    async def extract_invoice_data(self, pdf_bytes: bytes, mode: str = "standard") -> Tuple[Optional[Invoice], Dict[str, Any]]:
        """
        Extract structured invoice data from PDF using Gemini.

        Args:
            pdf_bytes: Raw PDF file bytes
            mode: Processing mode ('lightning', 'fast', 'enhanced')

        Returns:
            Tuple of (Invoice object or None, processing metadata)
        """
        logger.info(f"Processing invoice with Gemini in {mode} mode")

        try:
            # Configure client if needed
            if not self._client.configure():
                return None, {"success": False, "error": "Gemini client configuration failed"}

            # Get prompt for mode
            prompt = self._get_prompt_for_mode(mode)

            # Extract text with Gemini
            extracted_text = await self._client.extract_from_pdf(pdf_bytes, prompt)
            if not extracted_text:
                return None, {"success": False, "error": "No text extracted from PDF"}

            # Parse text to structured data
            parsed_data = invoice_parser.parse_to_invoice_data(extracted_text)
            if not parsed_data:
                return None, {"success": False, "error": "Failed to parse extracted text"}

            # Convert to Invoice object
            invoice = self._convert_to_invoice(parsed_data)

            metadata = {
                "success": True,
                "mode_used": mode,
                "model": app_settings.ai_model.GEMINI_MODEL_NAME,
                "confidence": parsed_data.get("confidence", 0.8)
            }

            return invoice, metadata

        except Exception as e:
            logger.error(f"Gemini processing failed: {e}")
            return None, {"success": False, "error": str(e)}

    async def structure_invoice_data_from_text(self, ocr_text: str) -> Tuple[Optional[Invoice], Dict[str, Any]]:
        """
        Structures invoice data from OCR text using Gemini.

        Args:
            ocr_text: The text extracted from the invoice by an OCR engine.

        Returns:
            A tuple of (Invoice object or None, processing metadata)
        """
        logger.info("Structuring invoice data from OCR text with Gemini")

        try:
            if not self._client.configure():
                return None, {"success": False, "error": "Gemini client configuration failed"}

            prompt = self._get_structuring_prompt()

            structured_text = await self._client.extract_from_text(ocr_text, prompt)
            if not structured_text:
                return None, {"success": False, "error": "Gemini could not structure the text"}

            parsed_data = invoice_parser.parse_to_invoice_data(structured_text)
            if not parsed_data:
                return None, {"success": False, "error": "Failed to parse structured text"}

            invoice = self._convert_to_invoice(parsed_data)

            metadata = {
                "success": True,
                "mode_used": "surya_gemini",
                "model": app_settings.ai_model.GEMINI_MODEL_NAME,
                "confidence": parsed_data.get("confidence", 0.9) # Higher confidence as it's structured
            }

            return invoice, metadata

        except Exception as e:
            logger.error(f"Gemini structuring failed: {e}")
            return None, {"success": False, "error": str(e)}

    def _get_structuring_prompt(self) -> str:
        """Get the prompt for structuring OCR text."""
        return """STRUCTURE: The following text was extracted from an invoice.
        Your task is to analyze it and structure it into a valid JSON format.
        Identify and extract all relevant fields:
        - Vendor and customer details (name, tax id, address)
        - Invoice metadata (invoice number, date, due date)
        - All line items with description, quantity, unit price, and total
        - Financial totals (subtotal, tax amount, total amount)
        - Currency
        Focus on accuracy and completeness."""

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

    def _convert_to_invoice(self, parsed_data: Dict[str, Any]) -> Invoice:
        """Convert parsed data to Invoice object."""
        from invoice_processing.utilities.invoice_builder import invoice_builder
        return invoice_builder.build_from_data(parsed_data)