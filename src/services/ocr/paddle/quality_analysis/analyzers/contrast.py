"""Contrast analyzer using standard deviation."""
import numpy as np


class ContrastAnalyzer:
    """Measures image contrast."""

    @staticmethod
    def measure(gray: np.ndarray) -> float:
        """
        Measure image contrast using standard deviation.

        Args:
            gray: Grayscale image

        Returns:
            Contrast score (typically 0-100+)
        """
        std_dev = gray.std()
        return float(std_dev)
