"""
Post-processor for automatic invoice financial corrections.

This module applies heuristic rules to fix common extraction errors,
particularly for Canary Islands invoices with IGIC tax.
"""
from typing import Optional
from loguru import logger
from invoice_processing.models.invoice_data import Invoice, TaxRateType, Discount


class InvoiceFinancialCorrector:
    """
    Applies intelligent corrections to invoice financial data.

    Key corrections:
    1. Auto-detect and fix IGIC/IVA tax type based on location
    2. Detect missing discounts from financial inconsistencies
    3. Recalculate subtotals when they don't match item sums
    """

    # Canary Islands location keywords
    CANARY_ISLANDS_KEYWORDS = [
        'canarias', 'canary', 'las palmas', 'tenerife', 'la palma',
        'gran canaria', 'fuerteventura', 'lanzarote', 'la laguna',
        'santa cruz', 'la gomera', 'el hierro'
    ]

    @classmethod
    def apply_all_corrections(cls, invoice: Invoice) -> Invoice:
        """
        Apply all correction rules to the invoice.

        Args:
            invoice: The invoice object to correct

        Returns:
            Corrected invoice object
        """
        logger.info("Applying financial corrections to invoice")

        # 1. Fix IGIC/IVA tax type
        invoice = cls.fix_canary_islands_tax_type(invoice)

        # 2. Detect and add missing discounts
        invoice = cls.detect_missing_discount(invoice)

        # 3. Recalculate subtotal if inconsistent
        invoice = cls.verify_and_fix_subtotal(invoice)

        return invoice

    @classmethod
    def fix_canary_islands_tax_type(cls, invoice: Invoice) -> Invoice:
        """
        Auto-correct IVA to IGIC if invoice is from/to Canary Islands.

        Detection logic:
        1. Check vendor location
        2. Check customer location
        3. Check for explicit IGIC mentions in notes
        4. Check tax rates (3%, 7%, 15% are typical IGIC rates)
        """
        # Check if tax is already IGIC
        if invoice.financial_details.tax.type == TaxRateType.IGIC:
            logger.debug("Tax already set to IGIC, no correction needed")
            return invoice

        is_canary_islands = False
        reason = None

        # Check vendor location
        if invoice.parties.vendor.address:
            vendor_location = (
                f"{invoice.parties.vendor.address.city or ''} "
                f"{invoice.parties.vendor.address.state or ''}"
            ).lower()

            if any(keyword in vendor_location for keyword in cls.CANARY_ISLANDS_KEYWORDS):
                is_canary_islands = True
                reason = f"vendor location: {vendor_location}"

        # Check customer location
        if not is_canary_islands and invoice.parties.customer.address:
            customer_location = (
                f"{invoice.parties.customer.address.city or ''} "
                f"{invoice.parties.customer.address.state or ''}"
            ).lower()

            if any(keyword in customer_location for keyword in cls.CANARY_ISLANDS_KEYWORDS):
                is_canary_islands = True
                reason = f"customer location: {customer_location}"

        # Check notes for explicit IGIC mention
        if not is_canary_islands and invoice.notes:
            notes_lower = invoice.notes.lower()
            if 'igic' in notes_lower or 'i.g.i.c' in notes_lower:
                is_canary_islands = True
                reason = "explicit IGIC mention in notes"

        # Check typical IGIC rates
        if not is_canary_islands:
            tax_rate = invoice.financial_details.tax.rate
            if tax_rate in [3.0, 7.0, 15.0]:
                # These are typical IGIC rates, check if other indicators support this
                if invoice.parties.vendor.address and invoice.parties.vendor.address.country:
                    country = invoice.parties.vendor.address.country.lower()
                    if 'esp' in country or 'spain' in country or country == 'es':
                        is_canary_islands = True
                        reason = f"typical IGIC rate ({tax_rate}%) in Spanish context"

        # Apply correction
        if is_canary_islands and invoice.financial_details.tax.type == TaxRateType.IVA:
            logger.warning(
                f"🔧 CORRECTION: Changed tax type from IVA to IGIC (detected: {reason})"
            )
            invoice.financial_details.tax.type = TaxRateType.IGIC

            # Also check additional_taxes
            if invoice.financial_details.additional_taxes:
                for tax in invoice.financial_details.additional_taxes:
                    if tax.type == TaxRateType.IVA:
                        logger.warning(
                            f"🔧 CORRECTION: Changed additional tax from IVA to IGIC"
                        )
                        tax.type = TaxRateType.IGIC

        return invoice

    @classmethod
    def detect_missing_discount(cls, invoice: Invoice) -> Invoice:
        """
        Detect if a discount is missing by comparing item sum vs subtotal.

        If items sum to more than subtotal, there's likely a discount.
        """
        if invoice.financial_details.discount is not None:
            logger.debug("Discount already present, no correction needed")
            return invoice

        # Calculate sum of all line items
        items_sum = sum(item.line_total for item in invoice.items)
        subtotal = invoice.financial_details.subtotal

        # Allow 0.10€ tolerance for rounding
        difference = items_sum - subtotal

        if difference > 0.10:
            # There's a missing discount
            discount_amount = round(difference, 2)
            discount_rate = round((discount_amount / items_sum) * 100, 2) if items_sum > 0 else 0

            logger.warning(
                f"🔧 CORRECTION: Detected missing discount: {discount_amount}€ "
                f"({discount_rate}% of {items_sum}€)"
            )

            invoice.financial_details.discount = Discount(
                description=f"Auto-detected ({discount_rate}% discount)",
                rate=discount_rate,
                amount=discount_amount
            )

        return invoice

    @classmethod
    def verify_and_fix_subtotal(cls, invoice: Invoice) -> Invoice:
        """
        Verify subtotal matches sum of items (considering discounts).

        If not, recalculate from items sum.
        """
        items_sum = sum(item.line_total for item in invoice.items)
        current_subtotal = invoice.financial_details.subtotal

        # Expected subtotal after discount
        discount = invoice.financial_details.discount
        expected_subtotal = items_sum
        if discount:
            expected_subtotal = items_sum - discount.amount

        # Allow 0.10€ tolerance
        difference = abs(current_subtotal - expected_subtotal)

        if difference > 0.10:
            logger.warning(
                f"🔧 CORRECTION: Subtotal mismatch - current: {current_subtotal}€, "
                f"expected: {expected_subtotal}€ (items: {items_sum}€, "
                f"discount: {discount.amount if discount else 0}€)"
            )

            # Fix: If current subtotal matches items_sum, it's probably the GROSS subtotal
            # In that case, don't change it - it's correct as the pre-discount value
            if abs(current_subtotal - items_sum) < 0.10:
                logger.info(
                    "✓ Subtotal appears to be gross (before discount), keeping as-is"
                )
            else:
                # Otherwise, recalculate
                invoice.financial_details.subtotal = round(expected_subtotal, 2)
                logger.info(f"✓ Recalculated subtotal to {invoice.financial_details.subtotal}€")

        return invoice

    @classmethod
    def validate_financial_math(cls, invoice: Invoice) -> dict:
        """
        Validate the financial calculations.

        Returns:
            dict with validation results and errors
        """
        errors = []
        warnings = []

        # Calculate expected total
        subtotal = invoice.financial_details.subtotal
        discount = invoice.financial_details.discount.amount if invoice.financial_details.discount else 0
        tax_amount = invoice.financial_details.tax.amount
        additional_taxes = sum(
            t.amount for t in (invoice.financial_details.additional_taxes or [])
        )
        surcharges = sum(
            s.amount for s in (invoice.financial_details.surcharges or [])
        )
        withholding = invoice.financial_details.withholding.amount if invoice.financial_details.withholding else 0

        expected_total = subtotal - discount + tax_amount + additional_taxes + surcharges - withholding
        actual_total = invoice.financial_details.total_amount

        difference = abs(expected_total - actual_total)

        if difference > 0.10:
            errors.append(
                f"Math error: expected {expected_total:.2f}€ ≠ actual {actual_total:.2f}€ "
                f"(difference: {difference:.2f}€)"
            )

        # Check items sum
        items_sum = sum(item.line_total for item in invoice.items)
        if abs(items_sum - subtotal) > 0.10 and discount == 0:
            warnings.append(
                f"Items sum ({items_sum:.2f}€) ≠ subtotal ({subtotal:.2f}€) - "
                f"possible missing discount"
            )

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "expected_total": round(expected_total, 2),
            "actual_total": actual_total,
            "difference": round(difference, 2)
        }
