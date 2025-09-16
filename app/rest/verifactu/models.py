# Copyright 2024 Artificial Intelligence Labs, SL

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.services.verifactu.models import (
    VerifactuValidationResult,
    VerifactuDashboardStats,
    VerifactuCorrection
)
from app.rest.models import DocumentInfo, ParsingJobInfo


class VerifactuValidationRequest(BaseModel):
    """Request model for VERIFACTU validation."""

    enable_aeat_validation: bool = Field(
        default=True,
        description="Whether to perform real-time AEAT validation"
    )
    enable_auto_correction: bool = Field(
        default=True,
        description="Whether to generate automatic corrections"
    )


class VerifactuValidationResponse(BaseModel):
    """Response model for VERIFACTU validation."""

    document: DocumentInfo = Field(description="Document information")
    job: ParsingJobInfo = Field(description="Processing job information")

    # VERIFACTU validation results
    verifactu_validation: VerifactuValidationResult = Field(description="Complete VERIFACTU validation results")

    # Auto-correction results (if enabled)
    auto_corrections: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Automatic correction results"
    )

    # Compliance summary
    compliance_summary: Dict[str, Any] = Field(description="Compliance summary")


class VerifactuDashboardResponse(BaseModel):
    """Response model for VERIFACTU dashboard."""

    dashboard_stats: VerifactuDashboardStats = Field(description="Dashboard statistics")
    dashboard_data: Dict[str, Any] = Field(description="Complete dashboard data")
    generated_at: str = Field(description="When dashboard was generated")


class VerifactuCorrectionRequest(BaseModel):
    """Request model for applying VERIFACTU corrections."""

    apply_qr_generation: bool = Field(default=True, description="Generate missing QR codes")
    apply_phrase_insertion: bool = Field(default=True, description="Insert mandatory phrases")
    apply_format_corrections: bool = Field(default=True, description="Apply format corrections")


class VerifactuCorrectionResponse(BaseModel):
    """Response model for VERIFACTU corrections."""

    corrections_applied: int = Field(description="Number of corrections applied")
    corrections: List[Dict[str, Any]] = Field(description="List of corrections made")
    generated_assets: Dict[str, Any] = Field(description="Generated assets (QR codes, etc.)")
    success: bool = Field(description="Whether corrections were successful")
    summary: str = Field(description="Human-readable summary")


class IssuerStatusResponse(BaseModel):
    """Response model for issuer VERIFACTU status."""

    nif: str = Field(description="Issuer NIF/CIF")
    registered_in_verifactu: bool = Field(description="Whether registered in VERIFACTU")
    active_in_verifactu: bool = Field(description="Whether active in VERIFACTU")
    compliance_level: str = Field(description="Compliance level")
    requires_action: bool = Field(description="Whether action is required")
    action_needed: Optional[str] = Field(default=None, description="Required action")
    last_checked: str = Field(description="When status was last checked")