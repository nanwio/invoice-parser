import enum
from typing import Optional
from pydantic import BaseModel, Field


class TaxRateType(enum.StrEnum):
    """Tax rate type applied."""
    IGIC = "IGIC"
    IVA = "IVA"
    OTHER = "OTHER"
    EXEMPT = "EXEMPT"


class BankPaymentMethod(enum.StrEnum):
    """Payment method used."""
    BANK_TRANSFER = "BANK_TRANSFER"
    BANK_DEPOSIT = "BANK_DEPOSIT"
    CARD = "CARD"
    CASH = "CASH"
    OTHER = "OTHER"


class Tax(BaseModel):
    """Tax calculation details."""
    type: TaxRateType = Field(..., description="Tax type (IVA, IGIC, etc.)")
    rate: float = Field(..., description="Tax rate as percentage")
    amount: float = Field(..., description="Tax amount")
    taxable_base: Optional[float] = Field(None, description="Taxable base")


class Withholding(BaseModel):
    """Tax withholding/retention details."""
    type: str = Field(..., description="Withholding type (IRPF, etc.)")
    rate: float = Field(..., description="Withholding rate")
    amount: float = Field(..., description="Withholding amount")


class Discount(BaseModel):
    """Discount applied."""
    description: Optional[str] = Field(None, description="Discount description")
    rate: Optional[float] = Field(None, description="Discount rate %")
    amount: float = Field(..., description="Discount amount")


class Surcharge(BaseModel):
    """Additional charges."""
    description: str = Field(..., description="Surcharge description")
    amount: float = Field(..., description="Surcharge amount")


class Payment(BaseModel):
    """Payment method information."""
    method: Optional[BankPaymentMethod] = None
    number: Optional[str] = None


class FinancialDetails(BaseModel):
    """Complete financial information."""
    currency: Optional[str] = Field(None, description="ISO 4217 currency code", pattern="^[A-Z]{3}$")
    subtotal: float = Field(..., description="Sum of line items before adjustments")
    discount: Optional[Discount] = Field(None, description="Applied discount")
    tax: Tax = Field(..., description="Primary tax")
    additional_taxes: Optional[list[Tax]] = Field(default_factory=list, description="Additional taxes")
    withholding: Optional[Withholding] = Field(None, description="Tax withholding")
    surcharges: Optional[list[Surcharge]] = Field(default_factory=list, description="Surcharges")
    total_amount: float = Field(..., description="Final amount to pay")
    payment: Optional[Payment] = Field(None, description="Payment method")
