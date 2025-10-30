"""Validates unit prices to detect column misalignment."""
from loguru import logger
from src.domain.models import Invoice


class UnitPriceValidator:
    """Detects when unit prices are confused with tax rates."""

    COMMON_TAX_RATES = {0.0, 3.0, 7.0, 15.0, 21.0}

    @classmethod
    def apply(cls, invoice: Invoice) -> Invoice:
        """Validate unit prices (detection only, doesn't fix)."""
        if not invoice.items:
            logger.debug("No items to validate")
            return invoice

        suspicious_count = sum(
            1 for item in invoice.items
            if item.unit_price in cls.COMMON_TAX_RATES
        )

        total_items = len(invoice.items)
        suspicious_ratio = suspicious_count / total_items if total_items > 0 else 0

        if suspicious_ratio > 0.8:
            logger.error(
                f"CRITICAL: Unit price column misalignment detected! "
                f"{suspicious_count}/{total_items} items ({suspicious_ratio*100:.0f}%) "
                f"have unit_price matching tax rates {cls.COMMON_TAX_RATES}. "
                f"Gemini likely confused IGIC/IVA column with Price column. "
                f"INVOICE REQUIRES MANUAL REVIEW"
            )
            for i, item in enumerate(invoice.items[:5]):
                if item.unit_price in cls.COMMON_TAX_RATES:
                    logger.error(
                        f"  - Item {i+1}: '{item.description[:40]}...' → "
                        f"unit_price={item.unit_price} (suspicious!)"
                    )
        elif suspicious_ratio > 0.5:
            logger.warning(
                f"Possible unit price issues: {suspicious_count}/{total_items} "
                f"({suspicious_ratio*100:.0f}%) match tax rates"
            )

        return invoice
