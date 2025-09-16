# Copyright 2024 Artificial Intelligence Labs, SL

from uuid import UUID

from datetime import timedelta, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.services.parser.models import Invoice


class DocumentPageSize(BaseModel):
    height: int = Field(..., gt=0)
    width: int = Field(..., gt=0)

    @staticmethod
    def from_mediabox(mediabox: Any) -> 'DocumentPageSize':
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


class ValidationInfo(BaseModel):
    """Validation results for enhanced parsing."""
    is_valid: bool = Field(
        ...,
        description="Whether the invoice passed all validation checks"
    )
    quality_score: float = Field(
        ...,
        description="Quality score from 0-100 based on completeness and accuracy"
    )
    errors: list[dict] = Field(
        default_factory=list,
        description="List of validation errors found"
    )
    warnings: list[dict] = Field(
        default_factory=list,
        description="List of validation warnings found"
    )
    validation_summary: str = Field(
        ...,
        description="Human-readable validation summary"
    )


class PerformanceMetrics(BaseModel):
    """Performance metrics for parsing operations."""
    total_time: float = Field(
        ...,
        description="Total processing time in seconds"
    )
    method_used: str = Field(
        ...,
        description="Parsing method used (donut, gemini_fallback, etc.)"
    )
    donut_time: Optional[float] = Field(
        None,
        description="Time spent in DONUT processing"
    )
    gemini_time: Optional[float] = Field(
        None,
        description="Time spent in Gemini processing"
    )
    validation_time: Optional[float] = Field(
        None,
        description="Time spent in validation"
    )
    donut_success: bool = Field(
        default=False,
        description="Whether DONUT processing succeeded"
    )
    gemini_fallback: bool = Field(
        default=False,
        description="Whether Gemini fallback was used"
    )


class EnhancedParsingResult(BaseModel):
    """Enhanced parsing result with validation and quality metrics."""
    document: DocumentInfo
    job: ParsingJobInfo
    result: Invoice
    validation: ValidationInfo
    preprocessing_used: bool = Field(
        ...,
        description="Whether advanced image preprocessing was applied"
    )


class FastParsingResult(BaseModel):
    """Ultra-fast parsing result with performance metrics."""
    document: DocumentInfo
    job: ParsingJobInfo
    result: Invoice
    validation: ValidationInfo
    performance: PerformanceMetrics = Field(
        ...,
        description="Detailed performance metrics"
    )