"""Invoice validation orchestrator."""
from src.domain.models import Invoice
from .models import InvoiceValidationResult
from .validators.required_fields import RequiredFieldsValidator
from .validators.math_validator import MathValidator
from .validators.data_quality import DataQualityValidator


class InvoiceValidator:
    """Validates invoice data for correctness and completeness."""

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

        RequiredFieldsValidator.validate(invoice, result)
        MathValidator.validate(invoice, result)
        DataQualityValidator.validate(invoice, result)

        return result


class QuickValidator(InvoiceValidator):
    """Fast validator for high-speed processing (only critical checks)."""

    def validate_invoice(self, invoice: Invoice) -> InvoiceValidationResult:
        """Quick validation - only critical checks."""
        result = InvoiceValidationResult()

        if not invoice:
            result.add_error("FATAL: Invoice object is None, indicating a catastrophic failure in parsing.")
            result.is_valid = False
            result.quality_score = 0
            return result

        RequiredFieldsValidator.validate(invoice, result)

        return result
