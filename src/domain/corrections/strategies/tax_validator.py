"""Validates tax calculations to detect duplication."""
from loguru import logger
from src.domain.models import Invoice


class TaxValidator:
    """Detects when taxes are duplicated from multiple sources."""

    @classmethod
    def apply(cls, invoice: Invoice) -> Invoice:
        """Validate taxes for duplication."""
        total_taxes = invoice.financial_details.tax.amount
        if invoice.financial_details.additional_taxes:
            total_taxes += sum(t.amount for t in invoice.financial_details.additional_taxes)

        subtotal = invoice.financial_details.subtotal
        discount = invoice.financial_details.discount.amount if invoice.financial_details.discount else 0
        base_imponible = subtotal - discount

        tax_ratio = total_taxes / base_imponible if base_imponible > 0 else 0

        if tax_ratio > 0.25:
            logger.error(
                f"CRITICAL: Tax duplication detected! "
                f"Total taxes ({total_taxes:.2f}€) = {tax_ratio*100:.0f}% of base ({base_imponible:.2f}€). "
                f"Spanish invoices typically 0-21%. "
                f"Gemini likely extracted from MULTIPLE sources."
            )
            logger.error(f"Tax breakdown:")
            logger.error(f"  - Main: {invoice.financial_details.tax.rate}% = {invoice.financial_details.tax.amount:.2f}€")
            if invoice.financial_details.additional_taxes:
                for i, tax in enumerate(invoice.financial_details.additional_taxes):
                    logger.error(f"  - Additional {i+1}: {tax.rate}% = {tax.amount:.2f}€")
        elif tax_ratio > 0.21:
            logger.warning(
                f"High tax ratio: {tax_ratio*100:.1f}% (max Spanish IVA is 21%)"
            )

        return invoice
