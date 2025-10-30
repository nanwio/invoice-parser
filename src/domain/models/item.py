from typing import Optional
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """Individual item entry in the invoice."""
    item_id: Optional[str] = Field(None, description="Item identifier")
    description: Optional[str] = Field(None, description="Item description")
    quantity: float = Field(..., description="Quantity (can be decimal)")
    unit_price: float = Field(ge=0, description="Price per unit")
    line_total: float = Field(ge=0, description="Total for this line")


class Metadata(BaseModel):
    """Invoice metadata."""
    invoice_number: Optional[str] = None
    issue_date: Optional[str] = Field(None, description="ISO format YYYY-MM-DD")
    due_date: Optional[str] = Field(None, description="ISO format YYYY-MM-DD")
    order_number: Optional[str] = None
