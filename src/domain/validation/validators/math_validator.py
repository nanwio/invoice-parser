"""Mathematical consistency validator."""
from src.domain.models import Invoice
from ..models import InvoiceValidationResult


class MathValidator:
    """Validates mathematical consistency of invoice calculations."""

    @staticmethod
    def validate(invoice: Invoice, result: InvoiceValidationResult):
        """
        Check mathematical consistency with smart validation.

        Args:
            invoice: Invoice to validate
            result: Validation result to update
        """
        try:
            fd = invoice.financial_details
            expected_total = MathValidator._calculate_expected_total(fd)
            actual_total = fd.total_amount
            difference = abs(expected_total - actual_total)

            tolerance = 0.10

            if difference > tolerance:
                items_sum = sum(item.line_total for item in invoice.items)
                subtotal_matches_items = abs(items_sum - fd.subtotal) <= 0.10
                relative_diff = (difference / actual_total) * 100 if actual_total > 0 else 0

                is_multi_period_with_regularizations = (
                    invoice.extensions and
                    isinstance(invoice.extensions, dict) and
                    invoice.extensions.get('multi_period_invoice', {}).get('has_regularizations', False)
                )

                is_legitimate_adjustment = (
                    is_multi_period_with_regularizations or
                    (subtotal_matches_items and relative_diff < 30)
                )

                if not is_legitimate_adjustment:
                    result.add_error(
                        f"Math error: expected {expected_total:.2f} ≠ actual {actual_total:.2f} "
                        f"(difference: {difference:.2f}, {relative_diff:.1f}%)"
                    )

        except Exception as e:
            result.add_warning(f"Could not verify mathematical consistency: {str(e)}")

    @staticmethod
    def _calculate_expected_total(fd):
        """Calculate expected total from financial details."""
        expected_total = fd.subtotal

        if fd.discount:
            expected_total -= fd.discount.amount

        expected_total += fd.tax.amount

        if fd.additional_taxes:
            for tax in fd.additional_taxes:
                expected_total += tax.amount

        if fd.withholding:
            expected_total -= abs(fd.withholding.amount)

        if fd.surcharges:
            for surcharge in fd.surcharges:
                expected_total += surcharge.amount

        return expected_total
