from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from .party import InvoiceParties
from .financial import FinancialDetails
from .item import LineItem, Metadata


class Invoice(BaseModel):
    """Complete invoice structure following EN16931/UBL extensibility pattern."""
    metadata: Optional[Metadata] = Field(None, description="Invoice metadata")
    notes: Optional[str] = Field(None, description="Additional notes")
    parties: InvoiceParties = Field(..., description="Vendor and customer")
    financial_details: FinancialDetails = Field(..., description="Financial information")
    items: list[LineItem] = Field(..., description="Invoice items")
    extensions: Optional[dict[str, Any]] = Field(None, description="Domain-specific extensions")

    model_config = ConfigDict(extra="allow")


class InvoiceParseResponse(BaseModel):
    """API response model for invoice parsing."""
    invoice: Invoice
    processing_results: dict
    user: str
    job_id: str
