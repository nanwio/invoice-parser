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
    def apply_all_corrections(cls, invoice: Optional[Invoice]) -> Optional[Invoice]:
        """
        Apply all correction rules to the invoice.

        Args:
            invoice: The invoice object to correct (or None if extraction failed)

        Returns:
            Corrected invoice object, or None if input was None
        """
        if invoice is None:
            logger.warning("⚠️  Cannot apply corrections: invoice is None (extraction failed)")
            return None

        logger.info("Applying financial corrections to invoice")

        # 1. Validate unit prices (detect column misalignment)
        cls.validate_unit_prices(invoice)

        # 2. Validate taxes (detect duplication from multiple sources)
        cls.validate_tax_duplication(invoice)

        # 3. Fix IGIC/IVA tax type
        invoice = cls.fix_canary_islands_tax_type(invoice)

        # 3. Detect and add missing discounts
        invoice = cls.detect_missing_discount(invoice)

        # 4. Recalculate subtotal if inconsistent
        invoice = cls.verify_and_fix_subtotal(invoice)

        return invoice

    @classmethod
    def validate_unit_prices(cls, invoice: Invoice) -> None:
        """
        Validate that unit prices are correct and not confused with tax rates or discounts.

        This is a DETECTION-only method (doesn't fix, just warns).
        Common issue: OCR loses column structure → Gemini confuses IGIC/IVA column (3%, 7%, 15%)
        with unit_price column.

        Indicators of column misalignment:
        - >80% of items have unit_price in {0.0, 3.0, 7.0, 15.0, 21.0}
        - These are typical Spanish tax rates (IGIC/IVA)
        - If detected, log CRITICAL warning for manual review
        """
        if not invoice.items or len(invoice.items) == 0:
            logger.debug("No items to validate")
            return

        # Common Spanish tax rates (IGIC + IVA)
        COMMON_TAX_RATES = {0.0, 3.0, 7.0, 15.0, 21.0}

        # Count how many items have prices that match tax rates
        suspicious_count = 0
        total_items = len(invoice.items)

        for item in invoice.items:
            if item.unit_price in COMMON_TAX_RATES:
                suspicious_count += 1

        # If >80% of items have "tax rate" prices, likely column misalignment
        suspicious_ratio = suspicious_count / total_items if total_items > 0 else 0

        if suspicious_ratio > 0.8:
            logger.error(
                f"🚨 CRITICAL: Unit price column misalignment detected! "
                f"{suspicious_count}/{total_items} items ({suspicious_ratio*100:.0f}%) have unit_price "
                f"matching common tax rates {COMMON_TAX_RATES}. "
                f"This usually means Gemini confused the IGIC/IVA column with the Price column. "
                f"⚠️  INVOICE REQUIRES MANUAL REVIEW OR RE-EXTRACTION"
            )

            # Log first 5 suspicious items for debugging
            logger.error("📋 Suspicious items (showing first 5):")
            for i, item in enumerate(invoice.items[:5]):
                if item.unit_price in COMMON_TAX_RATES:
                    logger.error(
                        f"  - Item {i+1}: '{item.description[:40]}...' → "
                        f"unit_price={item.unit_price} (suspicious!), "
                        f"quantity={item.quantity}, line_total={item.line_total}"
                    )

        elif suspicious_ratio > 0.5:
            logger.warning(
                f"⚠️  Possible unit price issues: {suspicious_count}/{total_items} items "
                f"({suspicious_ratio*100:.0f}%) have unit_price matching tax rates. "
                f"Review extraction quality."
            )
        else:
            logger.debug(
                f"✓ Unit prices look valid: only {suspicious_count}/{total_items} "
                f"match tax rates (< 50% threshold)"
            )

    @classmethod
    def validate_tax_duplication(cls, invoice: Invoice) -> None:
        """
        Detect if taxes were incorrectly duplicated from multiple sources.

        Common issue: Gemini extracts taxes from BOTH:
        - Tax summary section (Bases/Tipos/Cuotas)
        - Total tax line ("Impuestos: X€")
        Result: Taxes are doubled → validation fails

        Warning signs:
        - Sum of taxes > subtotal * 0.25 (unreasonably high for Spanish invoices)
        - Total calculated significantly > actual total (>5€ difference)
        """
        # Calculate total taxes
        total_taxes = invoice.financial_details.tax.amount
        if invoice.financial_details.additional_taxes:
            total_taxes += sum(t.amount for t in invoice.financial_details.additional_taxes)

        subtotal = invoice.financial_details.subtotal
        discount = invoice.financial_details.discount.amount if invoice.financial_details.discount else 0
        base_imponible = subtotal - discount

        # Spanish invoices: tax typically 0-21% of base imponible
        # If > 25%, likely duplication
        tax_ratio = total_taxes / base_imponible if base_imponible > 0 else 0

        if tax_ratio > 0.25:
            logger.error(
                f"🚨 CRITICAL: Tax duplication detected! "
                f"Total taxes ({total_taxes:.2f}€) = {tax_ratio*100:.0f}% of base imponible ({base_imponible:.2f}€). "
                f"Spanish invoices typically have 0-21% tax rate. "
                f"Likely cause: Gemini extracted taxes from MULTIPLE sources "
                f"(e.g., 'Bases/Cuotas' section + 'Impuestos:' line). "
                f"⚠️  This violates the '3-LEVEL STRATEGY' - should use ONLY ONE level."
            )

            # Log tax breakdown for debugging
            logger.error(f"📋 Tax breakdown:")
            logger.error(f"  - Main tax: {invoice.financial_details.tax.rate}% = {invoice.financial_details.tax.amount:.2f}€")
            if invoice.financial_details.additional_taxes:
                for i, tax in enumerate(invoice.financial_details.additional_taxes):
                    logger.error(f"  - Additional tax {i+1}: {tax.rate}% = {tax.amount:.2f}€")
            logger.error(f"  → TOTAL: {total_taxes:.2f}€ (expected max ~{base_imponible * 0.21:.2f}€)")

        elif tax_ratio > 0.21:
            logger.warning(
                f"⚠️  High tax ratio: {tax_ratio*100:.1f}% (taxes={total_taxes:.2f}€, base={base_imponible:.2f}€). "
                f"Spanish standard IVA max is 21%. Check if taxes were extracted correctly."
            )
        else:
            logger.debug(
                f"✓ Tax ratio OK: {tax_ratio*100:.1f}% ({total_taxes:.2f}€ / {base_imponible:.2f}€)"
            )

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
        ALWAYS recalculate subtotal as the EXACT sum of all line_total values.

        This ensures 100% mathematical accuracy regardless of Gemini's calculation.
        Subtotal = items[0].line_total + items[1].line_total + ... + items[N].line_total
        """
        # Calculate the EXACT sum of all line items
        items_sum = sum(item.line_total for item in invoice.items)
        current_subtotal = invoice.financial_details.subtotal

        # Round to 2 decimals to avoid floating point errors
        items_sum = round(items_sum, 2)

        # Check if correction is needed (tolerance: 0.01€)
        difference = abs(current_subtotal - items_sum)

        if difference > 0.01:
            logger.warning(
                f"🔧 CORRECTION: Subtotal recalculated from {current_subtotal}€ to {items_sum}€ "
                f"(difference: {difference:.2f}€) - using exact sum of {len(invoice.items)} line items"
            )
            invoice.financial_details.subtotal = items_sum
        else:
            logger.debug(f"✓ Subtotal verified: {items_sum}€ matches sum of {len(invoice.items)} items")

        return invoice

    @classmethod
    def validate_financial_math(cls, invoice: Invoice) -> dict:
        """
        Validate the financial calculations according to Spanish invoice standards.

        Spanish invoice calculation order:
        1. Subtotal (sum of line items)
        2. Apply discount → Base imponible (taxable base)
        3. Calculate taxes on base imponible
        4. Add surcharges, subtract withholding
        5. Total = (Subtotal - Discount) + Taxes + Surcharges - Withholding

        Returns:
            dict with validation results and errors
        """
        errors = []
        warnings = []

        # Extract financial components
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

        # CRITICAL FIX: Correct order of operations for Spanish invoices
        # First: Apply discounts and withholding to subtotal → Base imponible
        base_imponible = subtotal - discount

        # Second: Add taxes and surcharges to base
        total_taxes = tax_amount + additional_taxes
        expected_total = base_imponible + total_taxes + surcharges - withholding

        actual_total = invoice.financial_details.total_amount
        difference = abs(expected_total - actual_total)

        if difference > 0.10:
            # Detailed error message with breakdown
            error_msg = (
                f"Math error: expected {expected_total:.2f}€ ≠ actual {actual_total:.2f}€ "
                f"(difference: {difference:.2f}€)"
            )
            errors.append(error_msg)

            # Log detailed breakdown for debugging
            logger.error(
                f"💰 Financial validation failed:\n"
                f"  Subtotal (bruto):        {subtotal:>8.2f}€\n"
                f"  - Discount:              {discount:>8.2f}€\n"
                f"  = Base imponible:        {base_imponible:>8.2f}€\n"
                f"  + Tax (main):            {tax_amount:>8.2f}€\n"
                f"  + Additional taxes:      {additional_taxes:>8.2f}€\n"
                f"  + Surcharges:            {surcharges:>8.2f}€\n"
                f"  - Withholding:           {withholding:>8.2f}€\n"
                f"  = Expected total:        {expected_total:>8.2f}€\n"
                f"  vs Actual total:         {actual_total:>8.2f}€\n"
                f"  → Difference:            {difference:>8.2f}€ ❌"
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
