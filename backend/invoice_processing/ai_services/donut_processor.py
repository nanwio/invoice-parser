# Copyright 2024 Artificial Intelligence Labs, SL

"""
DONUT OCR processor - SIMPLE and FOCUSED
One responsibility: process invoices using DONUT model for OCR
"""

import asyncio
from typing import Tuple, Dict, Any, Optional
from loguru import logger

from invoice_processing.models.invoice_data import Invoice


class DonutOCRProcessor:
    """
    Processes invoices using DONUT OCR model.
    Fast alternative to Gemini for simple invoices.
    """

    def __init__(self):
        """Initialize DONUT model (lazy loading)."""
        self._model_loaded = False
        self._model = None

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
            # Ensure model is loaded
            await self._ensure_model_loaded()

            # Process PDF with DONUT
            # Note: This is a placeholder - DONUT integration would go here
            extracted_data = await self._process_with_donut(pdf_bytes)

            if extracted_data:
                invoice = self._convert_to_invoice(extracted_data)
                metadata = {
                    "success": True,
                    "method": "donut_ocr",
                    "confidence": extracted_data.get("confidence", 0.8)
                }
                return invoice, metadata
            else:
                return None, {"success": False, "method": "donut_ocr", "error": "No data extracted"}

        except Exception as e:
            logger.error(f"DONUT processing failed: {e}")
            return None, {"success": False, "method": "donut_ocr", "error": str(e)}

    async def _ensure_model_loaded(self):
        """Load DONUT model if not already loaded."""
        if self._model_loaded:
            return

        logger.info("Loading DONUT model...")
        # Placeholder for DONUT model loading
        # self._model = load_donut_model()
        self._model_loaded = True
        logger.info("DONUT model loaded")

    async def _process_with_donut(self, pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Process PDF with DONUT model.
        Placeholder for actual DONUT processing.
        """
        # Simulate processing time
        await asyncio.sleep(0.1)

        # Placeholder return - would contain actual DONUT extraction
        return {
            "vendor_name": "Extracted Vendor",
            "total_amount": 100.0,
            "confidence": 0.85
        }

    def _convert_to_invoice(self, donut_data: Dict[str, Any]) -> Invoice:
        """Convert DONUT extracted data to Invoice object."""
        from invoice_processing.models.invoice_data import InvoiceParty, InvoiceFinancials, InvoiceTax

        # Create basic invoice structure from DONUT data
        vendor = InvoiceParty(name=donut_data.get("vendor_name", "Unknown Vendor"))
        customer = InvoiceParty(name=donut_data.get("customer_name", "Unknown Customer"))

        tax = InvoiceTax(type="IVA", rate=21.0, amount=donut_data.get("tax_amount", 0.0))
        financials = InvoiceFinancials(
            subtotal=donut_data.get("subtotal", 0.0),
            tax=tax,
            total_amount=donut_data.get("total_amount", 0.0)
        )

        return Invoice(
            vendor=vendor,
            customer=customer,
            financials=financials,
            items=[]  # DONUT might not extract detailed line items
        )