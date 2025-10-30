"""Recalculates subtotal as exact sum of line items."""
from loguru import logger
from src.domain.models import Invoice


class SubtotalFixer:
    """Always recalculates subtotal for 100% accuracy."""

    @classmethod
    def apply(cls, invoice: Invoice) -> Invoice:
        """Recalculate subtotal from items."""
        items_sum = round(sum(item.line_total for item in invoice.items), 2)
        current_subtotal = invoice.financial_details.subtotal
        difference = abs(current_subtotal - items_sum)

        if difference > 0.01:
            logger.warning(
                f"CORRECTION: Subtotal {current_subtotal}€ → {items_sum}€ "
                f"(diff: {difference:.2f}€, {len(invoice.items)} items)"
            )
            invoice.financial_details.subtotal = items_sum
        else:
            logger.debug(f"Subtotal verified: {items_sum}€")

        return invoice
