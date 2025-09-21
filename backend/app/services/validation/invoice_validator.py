# Copyright 2024 Artificial Intelligence Labs, SL

import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from loguru import logger

from app.services.parser.models import Invoice, FinancialDetails, LineItem
from .spain_validators import SpanishTaxValidator


class ValidationError:
    """Represents a validation error with severity and details."""

    def __init__(self, field: str, message: str, severity: str = 'error'):
        self.field = field
        self.message = message
        self.severity = severity  # 'error', 'warning', 'info'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'field': self.field,
            'message': self.message,
            'severity': self.severity
        }


class InvoiceValidator:
    """
    Professional-grade invoice validation and quality assessment.
    Validates mathematical consistency, field formats, and business logic.
    """

    def __init__(self):
        self.spain_validator = SpanishTaxValidator()
        self.errors: List[ValidationError] = []
        self.warnings: List[ValidationError] = []

    def validate_invoice(self, invoice: Invoice) -> Dict[str, Any]:
        """
        Comprehensive invoice validation.

        Returns:
            Dict with validation results, errors, warnings, and quality score
        """
        self.errors = []
        self.warnings = []

        # Core validations
        self._validate_financial_consistency(invoice.financial_details, invoice.items)
        self._validate_dates(invoice.metadata)
        self._validate_tax_ids(invoice.parties)
        self._validate_line_items(invoice.items)
        self._validate_currency(invoice.financial_details)
        self._validate_tax_rates(invoice.financial_details)

        # Calculate quality score
        quality_score = self._calculate_quality_score(invoice)

        return {
            'is_valid': len(self.errors) == 0,
            'quality_score': quality_score,
            'errors': [e.to_dict() for e in self.errors],
            'warnings': [w.to_dict() for w in self.warnings],
            'validation_summary': self._generate_summary()
        }

    def _validate_financial_consistency(self, financial: FinancialDetails, items: List[LineItem]):
        """Validate mathematical consistency of financial calculations."""

        # Check if line items sum to subtotal
        calculated_subtotal = sum(item.line_total for item in items)
        tolerance = 0.02  # Allow for rounding differences

        if abs(calculated_subtotal - financial.subtotal) > tolerance:
            self.errors.append(ValidationError(
                'financial_details.subtotal',
                f'Subtotal mismatch: calculated {calculated_subtotal}, reported {financial.subtotal}'
            ))

        # Check tax calculation
        expected_tax_amount = financial.subtotal * (financial.tax.rate / 100)
        if abs(expected_tax_amount - financial.tax.amount) > tolerance:
            self.warnings.append(ValidationError(
                'financial_details.tax.amount',
                f'Tax amount may be incorrect: expected ~{expected_tax_amount:.2f}, got {financial.tax.amount}',
                'warning'
            ))

        # Check total calculation
        expected_total = financial.subtotal + financial.tax.amount
        if abs(expected_total - financial.total_amount) > tolerance:
            self.errors.append(ValidationError(
                'financial_details.total_amount',
                f'Total mismatch: expected {expected_total:.2f}, got {financial.total_amount}'
            ))

    def _validate_dates(self, metadata):
        """Validate date formats and logical consistency."""
        if not metadata:
            self.warnings.append(ValidationError(
                'metadata',
                'No metadata found - missing invoice number or dates',
                'warning'
            ))
            return

        # Validate date formats (ISO 8601)
        date_pattern = r'^\d{4}-\d{2}-\d{2}$'

        if metadata.issue_date:
            if not re.match(date_pattern, metadata.issue_date):
                self.errors.append(ValidationError(
                    'metadata.issue_date',
                    f'Invalid date format: {metadata.issue_date}. Expected YYYY-MM-DD'
                ))
            else:
                try:
                    issue_date = datetime.strptime(metadata.issue_date, '%Y-%m-%d')
                    # Check if date is reasonable (not too far in past/future)
                    if issue_date.year < 2000 or issue_date.year > datetime.now().year + 1:
                        self.warnings.append(ValidationError(
                            'metadata.issue_date',
                            f'Unusual invoice year: {issue_date.year}',
                            'warning'
                        ))
                except ValueError:
                    self.errors.append(ValidationError(
                        'metadata.issue_date',
                        f'Invalid date value: {metadata.issue_date}'
                    ))

        if metadata.due_date:
            if not re.match(date_pattern, metadata.due_date):
                self.errors.append(ValidationError(
                    'metadata.due_date',
                    f'Invalid date format: {metadata.due_date}. Expected YYYY-MM-DD'
                ))
            elif metadata.issue_date:
                try:
                    issue_date = datetime.strptime(metadata.issue_date, '%Y-%m-%d')
                    due_date = datetime.strptime(metadata.due_date, '%Y-%m-%d')
                    if due_date < issue_date:
                        self.errors.append(ValidationError(
                            'metadata.due_date',
                            'Due date cannot be before issue date'
                        ))
                except ValueError:
                    pass  # Date format error already caught above

    def _validate_tax_ids(self, parties):
        """Validate tax identification numbers."""
        if parties.vendor.tax_id:
            if not self.spain_validator.validate_cif_nif(parties.vendor.tax_id):
                self.warnings.append(ValidationError(
                    'parties.vendor.tax_id',
                    f'Invalid Spanish tax ID format: {parties.vendor.tax_id}',
                    'warning'
                ))

        if parties.customer.tax_id:
            if not self.spain_validator.validate_cif_nif(parties.customer.tax_id):
                self.warnings.append(ValidationError(
                    'parties.customer.tax_id',
                    f'Invalid Spanish tax ID format: {parties.customer.tax_id}',
                    'warning'
                ))

    def _validate_line_items(self, items: List[LineItem]):
        """Validate line items for completeness and consistency."""
        if not items:
            self.errors.append(ValidationError(
                'items',
                'No line items found in invoice'
            ))
            return

        for i, item in enumerate(items):
            # Check mathematical consistency
            expected_total = item.quantity * item.unit_price
            if abs(expected_total - item.line_total) > 0.01:
                self.warnings.append(ValidationError(
                    f'items[{i}].line_total',
                    f'Line total mismatch: {item.quantity} × {item.unit_price} ≠ {item.line_total}',
                    'warning'
                ))

            # Check for negative values
            if item.quantity < 0 or item.unit_price < 0 or item.line_total < 0:
                self.warnings.append(ValidationError(
                    f'items[{i}]',
                    'Negative values found - may indicate returns or discounts',
                    'info'
                ))

    def _validate_currency(self, financial: FinancialDetails):
        """Validate currency code format."""
        if financial.currency:
            # Check if it's a valid 3-letter currency code
            if not re.match(r'^[A-Z]{3}$', financial.currency):
                self.warnings.append(ValidationError(
                    'financial_details.currency',
                    f'Invalid currency format: {financial.currency}. Expected 3-letter ISO code',
                    'warning'
                ))

    def _validate_tax_rates(self, financial: FinancialDetails):
        """Validate tax rates against known standards."""
        rate = financial.tax.rate
        tax_type = financial.tax.type

        # Spanish tax rate validation
        if tax_type == 'IVA':
            valid_iva_rates = [0, 4, 10, 21]
            if rate not in valid_iva_rates:
                self.warnings.append(ValidationError(
                    'financial_details.tax.rate',
                    f'Unusual IVA rate: {rate}%. Standard rates: {valid_iva_rates}',
                    'warning'
                ))
        elif tax_type == 'IGIC':
            valid_igic_rates = [0, 3, 7, 9.5, 13.5, 20]
            if rate not in valid_igic_rates:
                self.warnings.append(ValidationError(
                    'financial_details.tax.rate',
                    f'Unusual IGIC rate: {rate}%. Standard rates: {valid_igic_rates}',
                    'warning'
                ))

    def _calculate_quality_score(self, invoice: Invoice) -> float:
        """
        Calculate a quality score from 0-100 based on completeness and accuracy.
        """
        score = 100.0

        # Deduct points for errors and warnings
        score -= len(self.errors) * 20  # Major penalty for errors
        score -= len(self.warnings) * 5  # Minor penalty for warnings

        # Bonus points for completeness
        if invoice.metadata and invoice.metadata.invoice_number:
            score += 5
        if invoice.metadata and invoice.metadata.issue_date:
            score += 5
        if invoice.parties.vendor.tax_id:
            score += 5
        if invoice.parties.customer.tax_id:
            score += 5
        if invoice.financial_details.currency:
            score += 3
        if len(invoice.items) > 0:
            score += 10

        return max(0.0, min(100.0, score))

    def _generate_summary(self) -> str:
        """Generate a human-readable validation summary."""
        if len(self.errors) == 0 and len(self.warnings) == 0:
            return "Invoice validation passed with no issues"

        summary = []
        if self.errors:
            summary.append(f"{len(self.errors)} error(s)")
        if self.warnings:
            summary.append(f"{len(self.warnings)} warning(s)")

        return f"Validation completed with {', '.join(summary)}"


# Global instance
invoice_validator = InvoiceValidator()