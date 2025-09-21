# Copyright 2024 Artificial Intelligence Labs, SL

from pydantic import BaseModel, Field


class DocumentClassification(BaseModel):
    """
    Document classification result.
    """
    is_invoice: bool = Field(
        ...,
        description="Whether the document is an invoice or not"
    )
    document_type: str = Field(
        ...,
        description="Type of document detected (e.g., invoice, receipt, contract, etc.)"
    )
    reason: str = Field(
        ...,
        description="Brief explanation of the classification"
    )