"""Orchestrates all invoice correction strategies."""
from typing import Optional
from loguru import logger
from src.domain.models import Invoice

from .strategies.unit_price_validator import UnitPriceValidator
from .strategies.tax_validator import TaxValidator
from .strategies.canary_tax_fixer import CanaryTaxFixer
from .strategies.discount_detector import DiscountDetector
from .strategies.subtotal_fixer import SubtotalFixer


class CorrectionOrchestrator:
    """Applies all corrections in sequence using Strategy Pattern."""

    @classmethod
    def apply_all_corrections(cls, invoice: Optional[Invoice]) -> Optional[Invoice]:
        """Apply all correction strategies to the invoice."""
        if invoice is None:
            logger.warning("Cannot apply corrections: invoice is None")
            return None

        logger.info("Applying financial corrections")

        # Apply strategies in order
        invoice = UnitPriceValidator.apply(invoice)
        invoice = TaxValidator.apply(invoice)
        invoice = CanaryTaxFixer.apply(invoice)
        invoice = DiscountDetector.apply(invoice)
        invoice = SubtotalFixer.apply(invoice)

        logger.success("Financial corrections applied successfully")
        return invoice
