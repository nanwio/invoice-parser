from typing import Optional
from pydantic import BaseModel, Field


class Address(BaseModel):
    """Physical address details."""
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class Contact(BaseModel):
    """Contact information."""
    email: Optional[str] = Field(None, description="Contact email")
    phone: Optional[str] = None
    fax: Optional[str] = None


class Party(BaseModel):
    """Entity details for vendor or customer."""
    name: str = Field(..., description="Person or company name")
    tax_id: Optional[str] = Field(None, description="Tax ID")
    contact: Optional[Contact] = Field(None, description="Contact info")
    address: Optional[Address] = Field(None, description="Address")


class InvoiceParties(BaseModel):
    """Parties involved in the invoice."""
    vendor: Party
    customer: Party
