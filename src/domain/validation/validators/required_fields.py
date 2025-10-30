"""Required fields validator."""
from src.domain.models import Invoice
from ..models import InvoiceValidationResult


class RequiredFieldsValidator:
    """Validates presence of required invoice fields."""

    @staticmethod
    def validate(invoice: Invoice, result: InvoiceValidationResult):
        """
        Check that required fields are present.

        Args:
            invoice: Invoice to validate
            result: Validation result to update
        """
        if not invoice.parties.vendor or not invoice.parties.vendor.name:
            result.add_error("Vendor name is missing.")

        if not invoice.parties.customer.name:
            result.add_error("Customer name is required")

        if invoice.financial_details.total_amount <= 0:
            result.add_error("Total amount must be greater than zero")

        if not invoice.items:
            result.add_error("At least one line item is required")
