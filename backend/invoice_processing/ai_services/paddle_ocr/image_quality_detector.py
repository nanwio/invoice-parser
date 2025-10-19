"""
Image Quality Detector for intelligent preprocessing.

Analyzes image quality to determine if preprocessing is needed.
Designed for invoices: distinguishes between scanned documents (high quality)
and mobile phone photos (may need enhancement).
"""

import cv2
import numpy as np
from typing import Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class QualityAnalysis:
    """Results of image quality analysis."""
    overall_score: float  # 0-100, higher is better
    needs_preprocessing: bool
    sharpness_score: float
    contrast_score: float
    rotation_angle: float
    noise_level: float
    is_likely_scan: bool


class ImageQualityDetector:
    """
    Detects image quality and determines if preprocessing is needed.

    Optimized for speed: analysis completes in ~50ms.
    """

    # Quality thresholds
    PREPROCESSING_THRESHOLD = 70.0  # Score below this triggers preprocessing
    SHARPNESS_THRESHOLD = 100.0  # Laplacian variance threshold
    CONTRAST_THRESHOLD = 50.0  # Standard deviation threshold
    ROTATION_THRESHOLD = 2.0  # Degrees
    NOISE_THRESHOLD = 30.0  # Noise percentage

    def __init__(self):
        """Initialize the quality detector."""
        pass

    def analyze(self, image: np.ndarray) -> QualityAnalysis:
        """
        Analyze image quality and determine if preprocessing is needed.

        Args:
            image: BGR image as numpy array (from OpenCV)

        Returns:
            QualityAnalysis object with scores and recommendation
        """
        # Convert to grayscale for analysis
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Run all quality checks
        sharpness_score = self._measure_sharpness(gray)
        contrast_score = self._measure_contrast(gray)
        rotation_angle = self._estimate_rotation(gray)
        noise_level = self._estimate_noise(gray)

        # Determine if it's likely a scan vs photo
        is_likely_scan = self._is_scan(sharpness_score, contrast_score, noise_level)

        # Calculate overall quality score (0-100)
        overall_score = self._calculate_overall_score(
            sharpness_score,
            contrast_score,
            rotation_angle,
            noise_level,
            is_likely_scan
        )

        # Decide if preprocessing is needed
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

    def _measure_sharpness(self, gray: np.ndarray) -> float:
        """
        Measure image sharpness using Laplacian variance.
        Higher value = sharper image.

        Returns:
            Sharpness score (typically 0-300+)
        """
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()
        return float(variance)

    def _measure_contrast(self, gray: np.ndarray) -> float:
        """
        Measure image contrast using standard deviation.
        Higher value = better contrast.

        Returns:
            Contrast score (typically 0-100+)
        """
        std_dev = gray.std()
        return float(std_dev)

    def _estimate_rotation(self, gray: np.ndarray) -> float:
        """
        Estimate rotation angle using Hough Line Transform.

        Returns:
            Estimated rotation angle in degrees (positive = clockwise)
        """
        try:
            # Use Canny edge detection
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)

            # Detect lines using Hough Transform
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

            # Calculate angles of detected lines
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
                # Normalize to -90 to 90 range
                if angle > 90:
                    angle = angle - 180
                angles.append(angle)

            # Return median angle (robust to outliers)
            median_angle = float(np.median(angles))
            return median_angle

        except Exception as e:
            logger.debug(f"Rotation detection failed: {e}")
            return 0.0

    def _estimate_noise(self, gray: np.ndarray) -> float:
        """
        Estimate noise level using local variance.

        Returns:
            Noise percentage (0-100)
        """
        try:
            # Calculate local variance using a small kernel
            kernel_size = 5
            mean = cv2.blur(gray.astype(np.float64), (kernel_size, kernel_size))
            sqr_mean = cv2.blur(gray.astype(np.float64) ** 2, (kernel_size, kernel_size))
            variance = sqr_mean - mean ** 2

            # Normalize to 0-100 range
            noise_level = np.mean(variance) / 100.0
            return float(min(100.0, max(0.0, noise_level)))

        except Exception as e:
            logger.debug(f"Noise estimation failed: {e}")
            return 0.0

    def _is_scan(self, sharpness: float, contrast: float, noise: float) -> bool:
        """
        Determine if image is likely a scan vs a photo.
        Scans typically have high sharpness, good contrast, low noise.

        Returns:
            True if likely a scan, False if likely a photo
        """
        scan_indicators = 0

        if sharpness > 150.0:  # Very sharp
            scan_indicators += 1
        if contrast > 60.0:  # Good contrast
            scan_indicators += 1
        if noise < 15.0:  # Low noise
            scan_indicators += 1

        return scan_indicators >= 2

    def _calculate_overall_score(
        self,
        sharpness: float,
        contrast: float,
        rotation: float,
        noise: float,
        is_scan: bool
    ) -> float:
        """
        Calculate overall quality score (0-100).

        Scoring logic:
        - Start at 100
        - Deduct points for quality issues
        - Scans get a bonus (assumed to be good quality)
        """
        score = 100.0

        # Sharpness penalty
        if sharpness < self.SHARPNESS_THRESHOLD:
            score -= (self.SHARPNESS_THRESHOLD - sharpness) / 2

        # Contrast penalty
        if contrast < self.CONTRAST_THRESHOLD:
            score -= (self.CONTRAST_THRESHOLD - contrast) / 2

        # Rotation penalty
        if abs(rotation) > self.ROTATION_THRESHOLD:
            score -= abs(rotation) * 2

        # Noise penalty
        if noise > self.NOISE_THRESHOLD:
            score -= (noise - self.NOISE_THRESHOLD)

        # Scan bonus (scans are usually good)
        if is_scan:
            score += 10.0

        # Clamp to 0-100 range
        return float(max(0.0, min(100.0, score)))
