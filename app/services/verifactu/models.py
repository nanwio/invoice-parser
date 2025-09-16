# Copyright 2024 Artificial Intelligence Labs, SL

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class VerifactuComplianceLevel(str, Enum):
    COMPLIANT = "compliant"
    WARNING = "warning"
    NON_COMPLIANT = "non_compliant"


class QRValidationResult(BaseModel):
    """Result of QR code validation for VERIFACTU compliance."""

    qr_present: bool = Field(description="Whether a QR code was detected")
    qr_readable: bool = Field(default=False, description="Whether QR code could be read")
    qr_data: Optional[str] = Field(default=None, description="Decoded QR data")
    aeat_url_valid: bool = Field(default=False, description="Whether QR contains valid AEAT URL")
    invoice_data_match: bool = Field(default=False, description="Whether QR data matches invoice")
    errors: List[str] = Field(default_factory=list, description="List of QR validation errors")


class PhraseValidationResult(BaseModel):
    """Result of mandatory phrase validation for VERIFACTU."""

    phrase_present: bool = Field(description="Whether mandatory phrase was found")
    exact_match: bool = Field(default=False, description="Whether phrase matches exactly")
    found_phrase: Optional[str] = Field(default=None, description="Actual phrase found")
    suggested_correction: Optional[str] = Field(default=None, description="Suggested correction")
    confidence: float = Field(default=0.0, description="Confidence level of detection")


class VerifactuFormatResult(BaseModel):
    """Result of VERIFACTU format validation."""

    has_required_fields: bool = Field(description="All required fields present")
    valid_identifiers: bool = Field(default=False, description="Unique identifiers are valid")
    structure_valid: bool = Field(default=False, description="Data structure is valid")
    hash_valid: bool = Field(default=False, description="Cryptographic hash is valid")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required fields")
    invalid_fields: List[str] = Field(default_factory=list, description="List of invalid fields")


class AEATValidationResult(BaseModel):
    """Result of real-time AEAT system validation."""

    invoice_exists: bool = Field(description="Invoice exists in AEAT system")
    issuer_registered: bool = Field(default=False, description="Issuer is registered in VERIFACTU")
    issuer_active: bool = Field(default=False, description="Issuer is active in system")
    validation_timestamp: Optional[str] = Field(default=None, description="When validation occurred")
    aeat_response_code: Optional[str] = Field(default=None, description="AEAT system response code")
    cache_hit: bool = Field(default=False, description="Whether result came from cache")


class VerifactuAlert(BaseModel):
    """VERIFACTU compliance alert."""

    level: str = Field(description="Alert level: critical, medium, low")
    message: str = Field(description="Alert message")
    field: Optional[str] = Field(default=None, description="Related field if applicable")
    suggestion: Optional[str] = Field(default=None, description="Suggested action")
    auto_correctable: bool = Field(default=False, description="Whether can be auto-corrected")


class VerifactuValidationResult(BaseModel):
    """Complete VERIFACTU validation result."""

    compliance_level: VerifactuComplianceLevel = Field(description="Overall compliance level")
    compliance_score: float = Field(description="Compliance score 0-100")

    qr_validation: QRValidationResult = Field(description="QR code validation results")
    phrase_validation: PhraseValidationResult = Field(description="Phrase validation results")
    format_validation: VerifactuFormatResult = Field(description="Format validation results")
    aeat_validation: Optional[AEATValidationResult] = Field(default=None, description="AEAT validation results")

    alerts: List[VerifactuAlert] = Field(default_factory=list, description="Compliance alerts")

    # Compliance summary
    verifactu_ready: bool = Field(description="Ready for VERIFACTU compliance")
    critical_issues: int = Field(default=0, description="Number of critical issues")
    warnings: int = Field(default=0, description="Number of warnings")

    # Auto-correction capabilities
    can_auto_correct: bool = Field(default=False, description="Whether issues can be auto-corrected")
    correction_suggestions: List[str] = Field(default_factory=list, description="Auto-correction suggestions")


class VerifactuDashboardStats(BaseModel):
    """Dashboard statistics for VERIFACTU compliance."""

    total_invoices: int = Field(description="Total number of invoices processed")
    compliant_invoices: int = Field(description="Number of VERIFACTU-ready invoices")
    warning_invoices: int = Field(description="Number of invoices with warnings")
    non_compliant_invoices: int = Field(description="Number of non-compliant invoices")

    compliance_percentage: float = Field(description="Overall compliance percentage")

    # Critical actions needed
    invoices_failing_2026: int = Field(description="Invoices that will fail in 2026")
    unregistered_issuers: int = Field(description="Issuers not registered in VERIFACTU")

    # Alert distribution
    critical_alerts: int = Field(description="Number of critical alerts")
    medium_alerts: int = Field(description="Number of medium alerts")
    low_alerts: int = Field(description="Number of low alerts")


class VerifactuCorrection(BaseModel):
    """Automatic VERIFACTU correction suggestion."""

    field: str = Field(description="Field to correct")
    current_value: Optional[str] = Field(default=None, description="Current value")
    suggested_value: str = Field(description="Suggested correction")
    confidence: float = Field(description="Confidence in suggestion")
    correction_type: str = Field(description="Type of correction: qr_generation, phrase_insertion, format_fix")