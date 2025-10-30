"""Detects missing discounts from financial inconsistencies."""
from loguru import logger
from src.domain.models import Invoice, Discount


class DiscountDetector:
    """Detects missing discounts by comparing items sum vs subtotal."""

    @classmethod
    def apply(cls, invoice: Invoice) -> Invoice:
        """Detect and add missing discount if found."""
        if invoice.financial_details.discount is not None:
            return invoice

        items_sum = sum(item.line_total for item in invoice.items)
        subtotal = invoice.financial_details.subtotal
        difference = items_sum - subtotal

        if difference > 0.10:
            discount_amount = round(difference, 2)
            discount_rate = round((discount_amount / items_sum) * 100, 2) if items_sum > 0 else 0

            logger.warning(
                f"CORRECTION: Detected missing discount: {discount_amount}€ "
                f"({discount_rate}% of {items_sum}€)"
            )

            invoice.financial_details.discount = Discount(
                description=f"Auto-detected ({discount_rate}% discount)",
                rate=discount_rate,
                amount=discount_amount
            )

        return invoice
