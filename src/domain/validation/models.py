"""Validation result models."""
from typing import Dict, List, Any


class InvoiceValidationResult:
    """Result of invoice validation."""

    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.quality_score: float = 100.0

    def add_error(self, message: str):
        """Add a validation error."""
        self.errors.append(message)
        self.is_valid = False
        self.quality_score -= 20

    def add_warning(self, message: str):
        """Add a validation warning."""
        self.warnings.append(message)
        self.quality_score -= 5

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "quality_score": max(0, self.quality_score)
        }
