"""
Mathematical validator for invoice data.

Validates invoice data using deterministic mathematical rules,
without requiring LLM calls. Fast, reliable, and cost-effective.
"""
from typing import List, Optional
from dataclasses import dataclass
from loguru import logger

from src.domain.models import Invoice


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    field: str
    issue_type: str
    message: str
    severity: str  # "error", "warning"
    expected: Optional[float] = None
    actual: Optional[float] = None


@dataclass
class MathematicalValidationResult:
    """Result of mathematical validation."""
    is_valid: bool
    issues: List[ValidationIssue]
    corrections_applied: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "issues": [
                {
                    "field": issue.field,
                    "type": issue.issue_type,
                    "message": issue.message,
                    "severity": issue.severity,
                    "expected": issue.expected,
                    "actual": issue.actual
                }
                for issue in self.issues
            ],
            "corrections_applied": self.corrections_applied
        }


class MathematicalValidator:
    """
    Validates invoice data using mathematical rules.

    Checks:
    - Subtotal = sum of line items
    - Total = subtotal + taxes - discounts + surcharges - withholding
    - No negative amounts (except discounts/withholding)
    - Item quantities and prices are non-negative
    """

    TOLERANCE = 0.02  # €0.02 tolerance for rounding differences

    @classmethod
    def validate(cls, invoice: Invoice, auto_correct: bool = True) -> MathematicalValidationResult:
        """
        Validate invoice using mathematical rules.

        Args:
            invoice: Invoice to validate
            auto_correct: If True, apply corrections automatically

        Returns:
            Validation result with issues and corrections
        """
        issues: List[ValidationIssue] = []
        corrections = 0

        # Validation 1: Subtotal = sum(items.line_total)
        subtotal_issue = cls._validate_subtotal(invoice)
        if subtotal_issue:
            issues.append(subtotal_issue)
            if auto_correct:
                cls._correct_subtotal(invoice)
                corrections += 1
                logger.info(f"Auto-corrected subtotal to {invoice.financial_details.subtotal}")

        # Validation 2: No negative line items
        negative_items = cls._validate_item_amounts(invoice)
        if negative_items:
            issues.extend(negative_items)

        # Validation 3: Total calculation
        total_issue = cls._validate_total(invoice)
        if total_issue:
            issues.append(total_issue)

        # Validation 4: Tax and discount reasonableness
        reasonableness_issues = cls._validate_reasonableness(invoice)
        if reasonableness_issues:
            issues.extend(reasonableness_issues)

        is_valid = all(issue.severity != "error" for issue in issues)

        return MathematicalValidationResult(
            is_valid=is_valid,
            issues=issues,
            corrections_applied=corrections
        )

    @classmethod
    def _validate_subtotal(cls, invoice: Invoice) -> Optional[ValidationIssue]:
        """
        Validate that subtotal equals sum of line items.

        Args:
            invoice: Invoice to validate

        Returns:
            ValidationIssue if invalid, None otherwise
        """
        if not invoice.items:
            return None

        calculated_subtotal = sum(item.line_total for item in invoice.items)
        stated_subtotal = invoice.financial_details.subtotal

        diff = abs(calculated_subtotal - stated_subtotal)

        if diff > cls.TOLERANCE:
            return ValidationIssue(
                field="financial_details.subtotal",
                issue_type="subtotal_mismatch",
                message=f"Subtotal mismatch: sum of items is {calculated_subtotal:.2f}, but subtotal is {stated_subtotal:.2f}",
                severity="error",
                expected=calculated_subtotal,
                actual=stated_subtotal
            )

        return None

    @classmethod
    def _correct_subtotal(cls, invoice: Invoice) -> None:
        """
        Auto-correct subtotal to match sum of items.

        Args:
            invoice: Invoice to correct (modified in-place)
        """
        if invoice.items:
            correct_subtotal = sum(item.line_total for item in invoice.items)
            invoice.financial_details.subtotal = correct_subtotal

    @classmethod
    def _validate_item_amounts(cls, invoice: Invoice) -> List[ValidationIssue]:
        """
        Validate that item amounts are non-negative.

        Args:
            invoice: Invoice to validate

        Returns:
            List of validation issues
        """
        issues = []

        for idx, item in enumerate(invoice.items):
            if item.line_total < 0:
                issues.append(
                    ValidationIssue(
                        field=f"items[{idx}].line_total",
                        issue_type="negative_amount",
                        message=f"Item '{item.description}' has negative line_total: {item.line_total}",
                        severity="error",
                        actual=item.line_total
                    )
                )

            if item.unit_price < 0:
                issues.append(
                    ValidationIssue(
                        field=f"items[{idx}].unit_price",
                        issue_type="negative_price",
                        message=f"Item '{item.description}' has negative unit_price: {item.unit_price}",
                        severity="error",
                        actual=item.unit_price
                    )
                )

            if item.quantity < 0:
                issues.append(
                    ValidationIssue(
                        field=f"items[{idx}].quantity",
                        issue_type="negative_quantity",
                        message=f"Item '{item.description}' has negative quantity: {item.quantity}",
                        severity="error",
                        actual=item.quantity
                    )
                )

        return issues

    @classmethod
    def _validate_total(cls, invoice: Invoice) -> Optional[ValidationIssue]:
        """
        Validate that total matches calculation.

        Formula: total = subtotal + tax - discount + surcharges - withholding

        Args:
            invoice: Invoice to validate

        Returns:
            ValidationIssue if invalid, None otherwise
        """
        fd = invoice.financial_details

        # Calculate expected total
        calculated_total = fd.subtotal

        # Add primary tax
        if fd.tax:
            calculated_total += fd.tax.amount

        # Add additional taxes
        if fd.additional_taxes:
            calculated_total += sum(tax.amount for tax in fd.additional_taxes)

        # Subtract discount
        if fd.discount:
            calculated_total -= fd.discount.amount

        # Add surcharges
        if fd.surcharges:
            calculated_total += sum(s.amount for s in fd.surcharges)

        # Subtract withholding
        if fd.withholding:
            calculated_total -= fd.withholding.amount

        stated_total = fd.total_amount
        diff = abs(calculated_total - stated_total)

        if diff > cls.TOLERANCE:
            return ValidationIssue(
                field="financial_details.total_amount",
                issue_type="total_mismatch",
                message=f"Total mismatch: calculated {calculated_total:.2f}, stated {stated_total:.2f} (diff: {diff:.2f})",
                severity="warning",  # Warning not error, as this might be intentional
                expected=calculated_total,
                actual=stated_total
            )

        return None

    @classmethod
    def _validate_reasonableness(cls, invoice: Invoice) -> List[ValidationIssue]:
        """
        Validate reasonableness of tax and discount.

        Args:
            invoice: Invoice to validate

        Returns:
            List of validation issues
        """
        issues = []
        fd = invoice.financial_details

        # Check if tax rate is reasonable (0% to 100%)
        if fd.tax and fd.tax.rate:
            if fd.tax.rate < 0 or fd.tax.rate > 100:
                issues.append(
                    ValidationIssue(
                        field="financial_details.tax.rate",
                        issue_type="unreasonable_tax_rate",
                        message=f"Tax rate {fd.tax.rate}% is outside reasonable range (0-100%)",
                        severity="warning",
                        actual=fd.tax.rate
                    )
                )

        # Check if discount is reasonable (not more than subtotal)
        if fd.discount and fd.discount.amount > fd.subtotal:
            issues.append(
                ValidationIssue(
                    field="financial_details.discount.amount",
                    issue_type="excessive_discount",
                    message=f"Discount {fd.discount.amount} exceeds subtotal {fd.subtotal}",
                    severity="error",
                    expected=fd.subtotal,
                    actual=fd.discount.amount
                )
            )

        # Check if total is positive
        if fd.total_amount < 0:
            issues.append(
                ValidationIssue(
                    field="financial_details.total_amount",
                    issue_type="negative_total",
                    message=f"Total amount is negative: {fd.total_amount}",
                    severity="error",
                    actual=fd.total_amount
                )
            )

        return issues
