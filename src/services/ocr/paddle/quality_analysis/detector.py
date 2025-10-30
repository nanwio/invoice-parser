"""Image quality detector orchestrator."""
import cv2
import numpy as np
from loguru import logger

from .models import QualityAnalysis
from .analyzers.sharpness import SharpnessAnalyzer
from .analyzers.contrast import ContrastAnalyzer
from .analyzers.rotation import RotationAnalyzer
from .analyzers.noise import NoiseAnalyzer
from .analyzers.scan_detector import ScanDetector
from .analyzers.scorer import QualityScorer


class ImageQualityDetector:
    """Detects image quality and determines if preprocessing is needed."""

    PREPROCESSING_THRESHOLD = 70.0

    def __init__(self):
        """Initialize the quality detector."""
        pass

    def analyze(self, image: np.ndarray) -> QualityAnalysis:
        """
        Analyze image quality.

        Args:
            image: BGR image as numpy array

        Returns:
            QualityAnalysis object with scores and recommendation
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        sharpness_score = SharpnessAnalyzer.measure(gray)
        contrast_score = ContrastAnalyzer.measure(gray)
        rotation_angle = RotationAnalyzer.estimate(gray)
        noise_level = NoiseAnalyzer.estimate(gray)

        is_likely_scan = ScanDetector.is_scan(sharpness_score, contrast_score, noise_level)

        overall_score = QualityScorer.calculate_score(
            sharpness_score,
            contrast_score,
            rotation_angle,
            noise_level,
            is_likely_scan
        )

        needs_preprocessing = overall_score < self.PREPROCESSING_THRESHOLD

        analysis = QualityAnalysis(
            overall_score=overall_score,
            needs_preprocessing=needs_preprocessing,
            sharpness_score=sharpness_score,
            contrast_score=contrast_score,
            rotation_angle=rotation_angle,
            noise_level=noise_level,
            is_likely_scan=is_likely_scan
        )

        logger.debug(
            f"Quality analysis: score={overall_score:.1f}, "
            f"needs_prep={needs_preprocessing}, scan={is_likely_scan}"
        )

        return analysis
