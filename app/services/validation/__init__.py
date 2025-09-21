# Copyright 2024 Artificial Intelligence Labs, SL

from .spain_validators import SpanishTaxValidator
from .file_validator import validate_uploaded_file

# Lazy import to avoid circular imports
def get_invoice_validator():
    from .invoice_validator import InvoiceValidator
    return InvoiceValidator

__all__ = ['SpanishTaxValidator', 'validate_uploaded_file', 'get_invoice_validator']