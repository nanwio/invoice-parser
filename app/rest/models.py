# Copyright 2024 Artificial Intelligence Labs, SL

from uuid import UUID

from datetime import timedelta, datetime
from PyPDF2.generic import RectangleObject
from pydantic import BaseModel, Field

from app.services.parser.models import Invoice


class DocumentPageSize(BaseModel):
    height: int = Field(..., gt=0)
    width: int = Field(..., gt=0)

    @staticmethod
    def from_mediabox(mediabox: RectangleObject) -> 'DocumentPageSize':
        return DocumentPageSize(
            width=int(mediabox.width),
            height=int(mediabox.height)
        )


class DocumentInfo(BaseModel):
    hash: str = Field(
        ...,
        description="SHA256 hash of the provided document"
    )
    num_pages: int = Field(
        ...,
        description="Number of pages of the provided document"
    )
    page_size: DocumentPageSize = Field(
        ...,
        description="Page size of the provided document"
    )


class ParsingJobInfo(BaseModel):
    job_id: UUID = Field(
        ...,
        description="Unique identifier for this specific invoice parsing job."
    )
    job_time: timedelta = Field(
        ...,
        description="Time required to process this document. Uses the ISO 8601 time delta format"
    )
    requested_by: str = Field(
        ...,
        description="User who made the request"
    )
    requested_at: datetime = Field(
        ...,
        description="ISO8601 datetime string for the moment the job was requested"
    )


class ParsingResult(BaseModel):
    document: DocumentInfo
    job: ParsingJobInfo
    result: Invoice
