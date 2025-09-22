# Copyright 2024 Artificial Intelligence Labs, SL

"""
Invoice validation - SIMPLE and CLEAR
One responsibility: check if invoice data is valid and complete
"""

from typing import Dict, List, Any
from ..models.invoice_data import Invoice


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

        # Check required fields
        self._check_required_fields(invoice, result)

        # Check mathematical consistency
        self._check_math(invoice, result)

        # Check data quality
        self._check_data_quality(invoice, result)

        return result

    def _check_required_fields(self, invoice: Invoice, result: InvoiceValidationResult):
        """Check that required fields are present."""
        if not invoice.vendor.name:
            result.add_error("Vendor name is required")

        if not invoice.customer.name:
            result.add_error("Customer name is required")

        if invoice.financials.total_amount <= 0:
            result.add_error("Total amount must be greater than zero")

        if not invoice.items:
            result.add_error("At least one line item is required")

    def _check_math(self, invoice: Invoice, result: InvoiceValidationResult):
        """Check mathematical consistency."""
        try:
            # Check if subtotal + tax = total (with small tolerance)
            expected_total = invoice.financials.subtotal + invoice.financials.tax.amount
            actual_total = invoice.financials.total_amount

            if abs(expected_total - actual_total) > 0.02:
                result.add_error(f"Math error: {expected_total} ≠ {actual_total}")

        except Exception:
            result.add_warning("Could not verify mathematical consistency")

    def _check_data_quality(self, invoice: Invoice, result: InvoiceValidationResult):
        """Check data quality and completeness."""
        # Check if dates are present
        if not (invoice.metadata and invoice.metadata.issue_date):
            result.add_warning("Invoice date is missing")

        # Check if tax ID is present
        if not invoice.vendor.tax_id:
            result.add_warning("Vendor tax ID is missing")

        # Check currency
        if not invoice.financials.currency:
            result.add_warning("Currency is not specified")


class QuickValidator(InvoiceValidator):
    """
    Fast validator for high-speed processing.
    Only checks critical errors, skips warnings.
    """

    def validate_invoice(self, invoice: Invoice) -> InvoiceValidationResult:
        """Quick validation - only critical checks."""
        result = InvoiceValidationResult()

        # Only check critical fields
        if not invoice.vendor.name:
            result.add_error("Missing vendor")
        if not invoice.customer.name:
            result.add_error("Missing customer")
        if invoice.financials.total_amount <= 0:
            result.add_error("Invalid total")

        return result