"""Rotation correction strategy."""
import cv2
import numpy as np
from loguru import logger


class DeskewStrategy:
    """Corrects image rotation/skew."""

    @staticmethod
    def apply(image: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotate image to correct skew.

        Args:
            image: Input image
            angle: Rotation angle in degrees

        Returns:
            Deskewed image
        """
        if abs(angle) < 0.5:
            return image

        logger.debug(f"Deskewing image by {angle:.2f} degrees")

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)

        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        rotated = cv2.warpAffine(
            image,
            M,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

        return rotated
