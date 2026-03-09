"""Orchestrates invoice validation strategies."""
from typing import Optional
from loguru import logger
from src.domain.models import Invoice

from .strategies.unit_price_validator import UnitPriceValidator


class CorrectionOrchestrator:
    """Applies validation strategies (detection only, no data modification)."""

    @classmethod
    def apply_all_corrections(cls, invoice: Optional[Invoice]) -> Optional[Invoice]:
        """Apply validation strategies to the invoice."""
        if invoice is None:
            logger.warning("Cannot apply corrections: invoice is None")
            return None

        logger.info("Applying validation checks")

        # Only detection/logging, no data modification
        # Actual corrections handled by MathematicalValidator in Step 4
        invoice = UnitPriceValidator.apply(invoice)

        logger.success("Validation checks completed")
        return invoice
