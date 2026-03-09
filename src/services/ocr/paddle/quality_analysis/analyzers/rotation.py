"""Rotation analyzer using Hough Line Transform."""
import cv2
import numpy as np
from loguru import logger


class RotationAnalyzer:
    """Estimates image rotation angle."""

    @staticmethod
    def estimate(gray: np.ndarray) -> float:
        """
        Estimate rotation angle using Hough Line Transform.

        Args:
            gray: Grayscale image

        Returns:
            Estimated rotation angle in degrees
        """
        try:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=np.pi / 180,
                threshold=100,
                minLineLength=100,
                maxLineGap=10
            )

            if lines is None or len(lines) < 5:
                return 0.0

            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                if angle > 90:
                    angle = angle - 180
                angles.append(angle)

            median_angle = float(np.median(angles))
            return median_angle

        except Exception as e:
            logger.debug(f"Rotation detection failed: {e}")
            return 0.0
