"""Orchestrates image preprocessing strategies."""
import numpy as np
from loguru import logger

from ..quality_analysis.models import QualityAnalysis
from .strategies.deskew import DeskewStrategy
from .strategies.denoise import DenoiseStrategy
from .strategies.contrast_enhancer import ContrastEnhancer
from .strategies.border_detector import BorderDetector


class PreprocessingOrchestrator:
    """Applies preprocessing strategies based on quality analysis."""

    @staticmethod
    def preprocess(image: np.ndarray, analysis: QualityAnalysis) -> np.ndarray:
        """
        Apply preprocessing operations based on quality analysis.

        Args:
            image: BGR image as numpy array
            analysis: Quality analysis results

        Returns:
            Preprocessed image
        """
        logger.info(f"Applying preprocessing (score={analysis.overall_score:.1f})")

        processed = image.copy()

        if abs(analysis.rotation_angle) > 2.0:
            processed = DeskewStrategy.apply(processed, analysis.rotation_angle)

        if analysis.noise_level > 30.0:
            processed = DenoiseStrategy.apply(processed)

        if analysis.contrast_score < 50.0:
            processed = ContrastEnhancer.apply(processed)

        if not analysis.is_likely_scan:
            processed = BorderDetector.apply(processed)

        return processed
