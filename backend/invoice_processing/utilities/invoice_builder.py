# Copyright 2024 Artificial Intelligence Labs, SL

"""
Invoice Builder - SIMPLE and FOCUSED
One responsibility: build Invoice objects from extracted data
"""

from typing import Dict, Any
from invoice_processing.models.invoice_data import Invoice, InvoiceParty, InvoiceFinancials, InvoiceTax


class InvoiceBuilder:
    """
    Builds Invoice objects from extracted data.
    Eliminates code duplication across processors.
    """

    @staticmethod
    def build_from_data(data: Dict[str, Any]) -> Invoice:
        """
        Build Invoice object from extracted data dictionary.

        Args:
            data: Dictionary with extracted invoice fields

        Returns:
            Invoice object
        """
        # Create vendor and customer
        vendor = InvoiceParty(
            name=data.get("vendor_name", "Unknown Vendor"),
            tax_id=data.get("vendor_tax_id"),
            email=data.get("vendor_email"),
            address=data.get("vendor_address")
        )

        customer = InvoiceParty(
            name=data.get("customer_name", "Unknown Customer"),
            tax_id=data.get("customer_tax_id"),
            email=data.get("customer_email"),
            address=data.get("customer_address")
        )

        # Create tax information
        tax = InvoiceTax(
            type=data.get("tax_type", "IVA"),
            rate=data.get("tax_rate", 21.0),
            amount=data.get("tax_amount", 0.0)
        )

        # Create financial information
        financials = InvoiceFinancials(
            currency=data.get("currency"),
            subtotal=data.get("subtotal", 0.0),
            tax=tax,
            total_amount=data.get("total_amount", 0.0)
        )

        # Build complete invoice
        return Invoice(
            vendor=vendor,
            customer=customer,
            financials=financials,
            items=data.get("items", [])  # Line items if available
        )


# Convenience instance
invoice_builder = InvoiceBuilder()