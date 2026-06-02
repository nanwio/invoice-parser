"""Tests for invoice validators (mathematical and semantic)."""
from src.domain.validation.orchestrator import InvoiceValidator
from src.domain.validation.models import InvoiceValidationResult
from src.domain.validation.validators.mathematical_validator import MathematicalValidator
from src.domain.validation.validators.required_fields import RequiredFieldsValidator


# -------------------------------------------------------------------
# MathematicalValidator: subtotal sum + auto-correction
# -------------------------------------------------------------------

def test_mathematical_validator_accepts_consistent_invoice(valid_invoice):
    """RUF-28: A consistent invoice generates no subtotal mismatch."""
    result = MathematicalValidator.validate(valid_invoice, auto_correct=False)

    subtotal_issues = [i for i in result.issues if i.issue_type == "subtotal_mismatch"]
    assert subtotal_issues == []


def test_mathematical_validator_detects_subtotal_mismatch(invoice_with_subtotal_mismatch):
    """RUF-28: Subtotal that does not match sum of items is flagged."""
    result = MathematicalValidator.validate(invoice_with_subtotal_mismatch, auto_correct=False)

    subtotal_issues = [i for i in result.issues if i.issue_type == "subtotal_mismatch"]
    assert len(subtotal_issues) == 1
    assert subtotal_issues[0].severity == "error"


def test_mathematical_validator_auto_corrects_subtotal(invoice_with_subtotal_mismatch):
    """RUF-29: When auto_correct is enabled, subtotal is rewritten to match items."""
    MathematicalValidator.validate(invoice_with_subtotal_mismatch, auto_correct=True)

    assert invoice_with_subtotal_mismatch.financial_details.subtotal == 200.0


def test_mathematical_validator_reports_corrections_applied(invoice_with_subtotal_mismatch):
    """RUF-29: The number of corrections applied is reported in the result."""
    result = MathematicalValidator.validate(invoice_with_subtotal_mismatch, auto_correct=True)

    assert result.corrections_applied == 1


# -------------------------------------------------------------------
# MathematicalValidator: total verification
# -------------------------------------------------------------------

def test_mathematical_validator_detects_total_mismatch(invoice_with_total_mismatch):
    """RUF-30/RUF-31: Inconsistent total is reported as a warning, not error."""
    result = MathematicalValidator.validate(invoice_with_total_mismatch, auto_correct=False)

    total_issues = [i for i in result.issues if i.issue_type == "total_mismatch"]
    assert len(total_issues) == 1
    assert total_issues[0].severity == "warning"


def test_mathematical_validator_tolerates_small_rounding(valid_invoice):
    """RUF-28: Differences below 0.02 should not be flagged."""
    valid_invoice.financial_details.subtotal = 200.01  # 0.01 difference vs items
    result = MathematicalValidator.validate(valid_invoice, auto_correct=False)

    subtotal_issues = [i for i in result.issues if i.issue_type == "subtotal_mismatch"]
    assert subtotal_issues == []


# -------------------------------------------------------------------
# RequiredFieldsValidator
# -------------------------------------------------------------------

def test_required_fields_passes_for_complete_invoice(valid_invoice):
    """RUF-32: A complete invoice passes required-fields validation."""
    result = InvoiceValidationResult()
    RequiredFieldsValidator.validate(valid_invoice, result)

    assert result.errors == []
    assert result.is_valid is True


def test_required_fields_flags_missing_vendor_name(invoice_missing_vendor_name):
    """RUF-32.1: Empty vendor name produces an error."""
    result = InvoiceValidationResult()
    RequiredFieldsValidator.validate(invoice_missing_vendor_name, result)

    assert any("Vendor name" in err for err in result.errors)
    assert result.is_valid is False


def test_required_fields_flags_zero_total(invoice_zero_total):
    """RUF-32.3: total_amount = 0 produces an error."""
    result = InvoiceValidationResult()
    RequiredFieldsValidator.validate(invoice_zero_total, result)

    assert any("Total amount" in err for err in result.errors)


def test_required_fields_flags_missing_items(valid_invoice):
    """RUF-32.4: An invoice with no items produces an error."""
    valid_invoice.items = []
    result = InvoiceValidationResult()
    RequiredFieldsValidator.validate(valid_invoice, result)

    assert any("line item" in err.lower() for err in result.errors)


# -------------------------------------------------------------------
# Quality score formula (RUF-33)
# -------------------------------------------------------------------

def test_quality_score_starts_at_100():
    """RUF-33.1: Initial quality score is 100."""
    result = InvoiceValidationResult()
    assert result.quality_score == 100.0


def test_quality_score_deducts_20_per_error():
    """RUF-33.2: Each error deducts 20 points."""
    result = InvoiceValidationResult()
    result.add_error("err 1")
    result.add_error("err 2")

    assert result.quality_score == 60.0


def test_quality_score_deducts_5_per_warning():
    """RUF-33.3: Each warning deducts 5 points."""
    result = InvoiceValidationResult()
    result.add_warning("w 1")
    result.add_warning("w 2")
    result.add_warning("w 3")

    assert result.quality_score == 85.0


def test_quality_score_clamps_at_zero():
    """RUF-33.4: Minimum score is 0 even after many errors."""
    result = InvoiceValidationResult()
    for _ in range(10):
        result.add_error("err")

    assert result.to_dict()["quality_score"] == 0


# -------------------------------------------------------------------
# Orchestrator integration
# -------------------------------------------------------------------

def test_orchestrator_returns_valid_for_complete_invoice(valid_invoice):
    """Orchestrator marks a consistent invoice as valid."""
    validator = InvoiceValidator()
    result = validator.validate_invoice(valid_invoice)

    assert result.is_valid is True
    assert result.errors == []


def test_orchestrator_aggregates_errors_from_validators(invoice_missing_vendor_name):
    """Orchestrator collects errors from each underlying validator."""
    validator = InvoiceValidator()
    result = validator.validate_invoice(invoice_missing_vendor_name)

    assert result.is_valid is False
    assert len(result.errors) >= 1
