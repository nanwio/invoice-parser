# Copyright 2024 Artificial Intelligence Labs, SL

"""
Invoice validation - SIMPLE and CLEAR
One responsibility: check if invoice data is valid and complete
"""

from typing import Dict, List, Any, Optional
from invoice_processing.models.invoice_data import Invoice


class InvoiceValidationResult:
    """Result of invoice validation."""

    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.quality_score: float = 100.0

    def add_error(self, message: str):
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False
        self.quality_score -= 20

    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)
        self.quality_score -= 5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "quality_score": max(0, self.quality_score)
        }


class InvoiceValidator:
    """
    Validates invoice data for correctness and completeness.
    Simple, focused validation logic.
    """

    def validate_invoice(self, invoice: Invoice) -> InvoiceValidationResult:
        """
        Validate an invoice and return validation results.

        Args:
            invoice: Invoice to validate

        Returns:
            Validation result with errors and quality score
        """
        result = InvoiceValidationResult()

        if not invoice:
            result.add_error("FATAL: Invoice object is None, indicating a catastrophic failure in parsing.")
            result.is_valid = False
            result.quality_score = 0
            return result

        # Check required fields
        self._check_required_fields(invoice, result)

        # Check mathematical consistency
        self._check_math(invoice, result)

        # Check data quality
        self._check_data_quality(invoice, result)

        return result

    def _check_required_fields(self, invoice: Invoice, result: InvoiceValidationResult):
        """Check that required fields are present."""
        if not invoice.parties.vendor or not invoice.parties.vendor.name:
            result.add_error("Vendor name is missing.")

        if not invoice.parties.customer.name:
            result.add_error("Customer name is required")

        if invoice.financial_details.total_amount <= 0:
            result.add_error("Total amount must be greater than zero")

        if not invoice.items:
            result.add_error("At least one line item is required")

    def _check_math(self, invoice: Invoice, result: InvoiceValidationResult):
        """Check mathematical consistency with support for multi-period invoices, discounts, taxes, withholdings, and surcharges."""
        try:
            fd = invoice.financial_details

            # Calculate expected total: subtotal - discount + taxes - withholding + surcharges
            expected_total = fd.subtotal

            # Subtract discount if present
            if fd.discount:
                expected_total -= fd.discount.amount

            # Add primary tax
            expected_total += fd.tax.amount

            # Add additional taxes if present
            if fd.additional_taxes:
                for tax in fd.additional_taxes:
                    expected_total += tax.amount

            # Subtract withholding if present (e.g., IRPF)
            if fd.withholding:
                expected_total -= abs(fd.withholding.amount)  # Ensure we subtract positive value

            # Add surcharges if present
            if fd.surcharges:
                for surcharge in fd.surcharges:
                    expected_total += surcharge.amount

            actual_total = fd.total_amount

            # Check for multi-period invoice indicator
            is_multi_period = (
                invoice.extensions and
                isinstance(invoice.extensions, dict) and
                "multi_period_invoice" in invoice.extensions
            )

            # Standard tolerance for rounding differences
            tolerance = 0.02

            # For multi-period invoices with significant discrepancy, issue warning instead of error
            # because subtotal may not reflect all consolidated periods
            if is_multi_period and abs(expected_total - actual_total) > 0.50:
                result.add_warning(
                    f"Multi-period invoice: calculated {expected_total:.2f} ≠ total {actual_total:.2f}. "
                    "This may be normal for consolidated bills with regularizations. Verify summary section was used."
                )
            elif abs(expected_total - actual_total) > tolerance:
                result.add_error(f"Math error: expected {expected_total:.2f} ≠ actual {actual_total:.2f}")

        except Exception as e:
            result.add_warning(f"Could not verify mathematical consistency: {str(e)}")

    def _check_data_quality(self, invoice: Invoice, result: InvoiceValidationResult):
        """Check data quality and completeness."""
        # Check if dates are present
        if not (invoice.metadata and invoice.metadata.issue_date):
            result.add_warning("Invoice date is missing")

        # Check if tax ID is present
        if not invoice.parties.vendor.tax_id:
            result.add_warning("Vendor tax ID is missing")

        # Check currency
        if not invoice.financial_details.currency:
            result.add_warning("Currency is not specified")


class QuickValidator(InvoiceValidator):
    """
    Fast validator for high-speed processing.
    Only checks critical errors, skips warnings.
    """

    def validate_invoice(self, invoice: Invoice) -> InvoiceValidationResult:
        """Quick validation - only critical checks."""
        result = InvoiceValidationResult()

        if not invoice:
            result.add_error("FATAL: Invoice object is None, indicating a catastrophic failure in parsing.")
            result.is_valid = False
            result.quality_score = 0
            return result

        # Only check critical fields
        if not invoice.parties.vendor.name:
            result.add_error("Missing vendor")
        if not invoice.parties.customer.name:
            result.add_error("Missing customer")
        if invoice.financial_details.total_amount <= 0:
            result.add_error("Invalid total")

        return result