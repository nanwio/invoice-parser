"""Border detection and cropping strategy."""
import cv2
import numpy as np
from loguru import logger


class BorderDetector:
    """Detects document borders and crops to document area."""

    @staticmethod
    def apply(image: np.ndarray) -> np.ndarray:
        """
        Detect and crop document borders.

        Args:
            image: Input image

        Returns:
            Cropped image (or original if detection fails)
        """
        logger.debug("Detecting and cropping borders")

        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            dilated = cv2.dilate(edges, kernel, iterations=2)

            contours, _ = cv2.findContours(
                dilated,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return image

            largest_contour = max(contours, key=cv2.contourArea)
            contour_area = cv2.contourArea(largest_contour)
            image_area = image.shape[0] * image.shape[1]

            area_ratio = contour_area / image_area
            if area_ratio < 0.3 or area_ratio > 0.95:
                logger.debug(f"Border detection skipped (area ratio: {area_ratio:.2f})")
                return image

            x, y, w, h = cv2.boundingRect(largest_contour)

            padding = 10
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(image.shape[1] - x, w + 2 * padding)
            h = min(image.shape[0] - y, h + 2 * padding)

            cropped = image[y:y+h, x:x+w]

            logger.debug(f"Cropped from {image.shape[:2]} to {cropped.shape[:2]}")
            return cropped

        except Exception as e:
            logger.debug(f"Border detection failed: {e}")
            return image
