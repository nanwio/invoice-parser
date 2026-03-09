"""Sharpness analyzer using Laplacian variance."""
import cv2
import numpy as np


class SharpnessAnalyzer:
    """Measures image sharpness."""

    @staticmethod
    def measure(gray: np.ndarray) -> float:
        """
        Measure image sharpness using Laplacian variance.

        Args:
            gray: Grayscale image

        Returns:
            Sharpness score (typically 0-300+)
        """
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return float(variance)
