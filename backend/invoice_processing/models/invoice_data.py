import enum

from typing import Optional
from pydantic import BaseModel, Field


class TaxRateType(enum.StrEnum):
    """
    Tax rate type applied
    """
    IGIC = "IGIC"
    IVA = "IVA"
    OTHER = "OTHER"
    EXEMPT = "EXEMPT"


class BankPaymentMethod(enum.StrEnum):
    """
    Payment method used in the transaction that generated the invoice / ticket
    """
    BANK_TRANSFER = "BANK_TRANSFER"
    BANK_DEPOSIT = "BANK_DEPOSIT"
    CARD = "CARD"
    CASH = "CASH"
    OTHER = "OTHER"


class Address(BaseModel):
    """
    Physical address details.
    """
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class Contact(BaseModel):
    """
    Contact information.
    """
    email: Optional[str] = Field(
        None,
        description="Contact email provided in the invoice."
    )
    phone: Optional[str] = None
    fax: Optional[str] = None


class Party(BaseModel):
    """
    Entity details for either vendor or customer.
    """
    name: str = Field(
        ...,
        description="Person or company name. If found in the document, it might contain the full legal name."
    )
    tax_id: Optional[str] = Field(
        None,
        description="National or international tax id for this party"
    )
    contact: Optional[Contact] = Field(
        None,
        description="Contact point for this party"
    )
    address: Optional[Address] = Field(
        None,
        description="Known address for this party"
    )


class Tax(BaseModel):
    """
    Tax calculation details.
    """
    type: TaxRateType = Field(
        ...,
        description="Type of tax applied (IVA, IGIC, VAT, GST, etc.)"
    )
    rate: float = Field(
        ...,
        description="Tax rate as percentage (e.g., 21.0 for 21%)"
    )
    amount: float = Field(
        ...,
        description="Total tax amount in the invoice currency"
    )


class Withholding(BaseModel):
    """
    Tax withholding/retention details (e.g., IRPF, Income Tax Withholding).
    """
    type: str = Field(
        ...,
        description="Type of withholding (e.g., 'IRPF', 'Income Tax', 'WHT')"
    )
    rate: float = Field(
        ...,
        description="Withholding rate as percentage"
    )
    amount: float = Field(
        ...,
        description="Withholding amount (typically negative or to be subtracted)"
    )


class Discount(BaseModel):
    """
    Discount applied to the invoice.
    """
    description: Optional[str] = Field(
        None,
        description="Description of the discount"
    )
    rate: Optional[float] = Field(
        None,
        description="Discount rate as percentage if applicable"
    )
    amount: float = Field(
        ...,
        description="Discount amount"
    )


class Surcharge(BaseModel):
    """
    Additional charges or surcharges.
    """
    description: str = Field(
        ...,
        description="Description of the surcharge"
    )
    amount: float = Field(
        ...,
        description="Surcharge amount"
    )


class Payment(BaseModel):
    """
    Payment method information.
    """
    method: BankPaymentMethod
    number: Optional[str] = None


class FinancialDetails(BaseModel):
    """
    Complete financial information for the invoice.
    Supports international invoice formats with taxes, withholdings, discounts, and surcharges.
    """
    currency: Optional[str] = Field(
        None,
        description="ISO 4217 currency code (e.g., 'USD', 'EUR', 'GBP')",
        pattern="^[A-Z]{3}$"  # Validates 3-letter currency codes
    )
    subtotal: float = Field(
        ...,
        description="Sum of all line items before any taxes, discounts, or adjustments"
    )
    discount: Optional[Discount] = Field(
        None,
        description="Discount applied to the subtotal, if any"
    )
    tax: Tax = Field(
        ...,
        description="Primary tax applied (IVA, IGIC, VAT, GST, etc.)"
    )
    additional_taxes: Optional[list[Tax]] = Field(
        default_factory=list,
        description="Additional taxes if multiple tax types apply"
    )
    withholding: Optional[Withholding] = Field(
        None,
        description="Tax withholding/retention (e.g., IRPF, Income Tax) - amount to subtract from total"
    )
    surcharges: Optional[list[Surcharge]] = Field(
        default_factory=list,
        description="Additional surcharges or fees"
    )
    total_amount: float = Field(
        ...,
        description="Final amount to pay after all adjustments: subtotal - discount + taxes - withholding + surcharges"
    )
    payment: Optional[Payment] = Field(
        None,
        description="Information about the payment method used in this transaction"
    )


class LineItem(BaseModel):
    """
    Individual item entry in the invoice.
    """
    item_id: Optional[str] = Field(
        None,
        description="Unique identifier for this line item."
    )
    description: Optional[str] = Field(
        None,
        description="If present, a description of this item."
    )
    quantity: int
    unit_price: float = Field(ge=0)
    line_total: float = Field(ge=0)


class Metadata(BaseModel):
    """
    Invoice metadata information.
    """
    invoice_number: Optional[str] = None
    issue_date: Optional[str] = Field(None, description="Issue date in ISO format (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Due date in ISO format (YYYY-MM-DD)")
    order_number: Optional[str] = None


class InvoiceParties(BaseModel):
    """
    Parties involved in the operation that generated the invoice
    """
    vendor: Party
    customer: Party


class Invoice(BaseModel):
    """
    Complete invoice structure.
    """
    metadata: Optional[Metadata] = Field(
        None,
        description="Metadata associated with this invoice"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional information that is not an integral part of the invoice itself but might be important."
    )
    parties: InvoiceParties = Field(
        ...,
        description="Parties associated with this invoice (seller and buyer)"
    )
    financial_details: FinancialDetails = Field(
        ...,
        description="Information about the amount billed and the payment method used in the transaction."
    )
    items: list[LineItem] = Field(
        ...,
        description="Every detected invoice item."
    )


class InvoiceParseResponse(BaseModel):
    """
    Response model for invoice parsing API endpoint.
    """
    invoice: Invoice
    processing_results: dict
    user: str
    job_id: str