"""Data quality validator."""
from src.domain.models import Invoice
from ..models import InvoiceValidationResult


class DataQualityValidator:
    """Validates data quality and completeness."""

    @staticmethod
    def validate(invoice: Invoice, result: InvoiceValidationResult):
        """
        Check data quality and completeness.

        Args:
            invoice: Invoice to validate
            result: Validation result to update
        """
        if not (invoice.metadata and invoice.metadata.issue_date):
            result.add_warning("Invoice date is missing")

        if not invoice.parties.vendor.tax_id:
            result.add_warning("Vendor tax ID is missing")

        if not invoice.financial_details.currency:
            result.add_warning("Currency is not specified")
