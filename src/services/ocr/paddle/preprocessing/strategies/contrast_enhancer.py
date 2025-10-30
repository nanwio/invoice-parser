"""Contrast enhancement strategy."""
import cv2
import numpy as np
from loguru import logger


class ContrastEnhancer:
    """Enhances contrast using CLAHE."""

    @staticmethod
    def apply(image: np.ndarray) -> np.ndarray:
        """
        Enhance image contrast.

        Args:
            image: Input image

        Returns:
            Enhanced image
        """
        logger.debug("Enhancing contrast")

        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)

        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        return enhanced
