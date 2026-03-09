"""Noise reduction strategy."""
import cv2
import numpy as np
from loguru import logger


class DenoiseStrategy:
    """Reduces image noise using Non-local Means Denoising."""

    @staticmethod
    def apply(image: np.ndarray) -> np.ndarray:
        """
        Reduce noise from image.

        Args:
            image: Input image

        Returns:
            Denoised image
        """
        logger.debug("Applying denoising")

        denoised = cv2.fastNlMeansDenoisingColored(
            image,
            None,
            h=10,
            hColor=10,
            templateWindowSize=7,
            searchWindowSize=21
        )

        return denoised
