# Copyright 2024 Artificial Intelligence Labs, SL

"""
Invoice data models - SIMPLE and CLEAR
Each class represents one concept only
"""

import enum
from typing import Optional
from pydantic import BaseModel, Field


class TaxType(enum.StrEnum):
    """Types of taxes that can be applied."""
    IVA = "IVA"      # Spanish VAT
    IGIC = "IGIC"    # Canary Islands tax
    OTHER = "OTHER"  # Other tax types
    EXEMPT = "EXEMPT"  # Tax exempt


class PaymentMethod(enum.StrEnum):
    """Payment methods for invoices."""
    BANK_TRANSFER = "BANK_TRANSFER"
    CARD = "CARD"
    CASH = "CASH"
    OTHER = "OTHER"


class InvoiceParty(BaseModel):
    """A party in an invoice (vendor or customer)."""
    name: str = Field(..., description="Company or person name")
    tax_id: Optional[str] = Field(None, description="Tax identification number")
    email: Optional[str] = Field(None, description="Contact email")
    address: Optional[str] = Field(None, description="Full address")


class InvoiceLineItem(BaseModel):
    """A single line item in an invoice."""
    description: Optional[str] = Field(None, description="Item description")
    quantity: int = Field(..., description="Quantity of items")
    unit_price: float = Field(..., ge=0, description="Price per unit")
    line_total: float = Field(..., ge=0, description="Total for this line")


class InvoiceTax(BaseModel):
    """Tax information for an invoice."""
    type: TaxType = Field(..., description="Type of tax applied")
    rate: float = Field(..., ge=0, description="Tax rate percentage")
    amount: float = Field(..., ge=0, description="Tax amount in currency")


class InvoiceFinancials(BaseModel):
    """Financial totals for an invoice."""
    currency: Optional[str] = Field(None, description="Currency code (EUR, USD, etc.)")
    subtotal: float = Field(..., ge=0, description="Subtotal before tax")
    tax: InvoiceTax = Field(..., description="Tax details")
    total_amount: float = Field(..., ge=0, description="Final total amount")


class InvoiceMetadata(BaseModel):
    """Metadata information for an invoice."""
    invoice_number: Optional[str] = Field(None, description="Invoice number")
    issue_date: Optional[str] = Field(None, description="Issue date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Due date (YYYY-MM-DD)")


class Invoice(BaseModel):
    """Complete invoice data structure."""

    # Core invoice data
    vendor: InvoiceParty = Field(..., description="Vendor/seller information")
    customer: InvoiceParty = Field(..., description="Customer/buyer information")

    # Financial information
    financials: InvoiceFinancials = Field(..., description="Financial totals")

    # Line items
    items: list[InvoiceLineItem] = Field(..., description="All invoice line items")

    # Metadata
    metadata: Optional[InvoiceMetadata] = Field(None, description="Invoice metadata")

    # Additional notes
    notes: Optional[str] = Field(None, description="Additional notes or comments")