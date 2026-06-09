"""Orchestrates invoice validation strategies."""
from typing import Optional
from loguru import logger
from src.domain.models import Invoice

from .strategies.unit_price_validator import UnitPriceValidator
from .strategies.line_total_validator import LineTotalValidator


class CorrectionOrchestrator:
    """Applies validation strategies (detection and OCR-grounded corrections)."""

    @classmethod
    def apply_all_corrections(
        cls,
        invoice: Optional[Invoice],
        ocr_text: Optional[str] = None,
    ) -> Optional[Invoice]:
        """Apply validation/correction strategies to the invoice.

        Args:
            invoice: Structured invoice from the LLM (may be None on extraction failure).
            ocr_text: Raw OCR text. Required for LineTotalValidator to find substitutes.
        """
        if invoice is None:
            logger.warning("Cannot apply corrections: invoice is None")
            return None

        logger.info("Applying validation checks")

        invoice = UnitPriceValidator.apply(invoice)
        invoice = LineTotalValidator.apply(invoice, ocr_text)

        logger.success("Validation checks completed")
        return invoice
