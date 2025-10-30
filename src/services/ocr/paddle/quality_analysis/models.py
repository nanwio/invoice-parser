"""Quality analysis data models."""
from dataclasses import dataclass


@dataclass
class QualityAnalysis:
    """Results of image quality analysis."""
    overall_score: float
    needs_preprocessing: bool
    sharpness_score: float
    contrast_score: float
    rotation_angle: float
    noise_level: float
    is_likely_scan: bool
