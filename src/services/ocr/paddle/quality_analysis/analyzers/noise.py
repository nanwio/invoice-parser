"""Noise level analyzer using local variance."""
import cv2
import numpy as np
from loguru import logger


class NoiseAnalyzer:
    """Estimates image noise level."""

    @staticmethod
    def estimate(gray: np.ndarray) -> float:
        """
        Estimate noise level using local variance.

        Args:
            gray: Grayscale image

        Returns:
            Noise percentage (0-100)
        """
        try:
            kernel_size = 5
            mean = cv2.blur(gray.astype(np.float64), (kernel_size, kernel_size))
            sqr_mean = cv2.blur(gray.astype(np.float64) ** 2, (kernel_size, kernel_size))
            variance = sqr_mean - mean ** 2

            noise_level = np.mean(variance) / 100.0
            return float(min(100.0, max(0.0, noise_level)))

        except Exception as e:
            logger.debug(f"Noise estimation failed: {e}")
            return 0.0
