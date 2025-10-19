"""
Image Preprocessor for enhancing low-quality invoice photos.

Applies selective preprocessing operations based on quality analysis.
Optimized for speed while improving OCR accuracy on mobile phone photos.
"""

import cv2
import numpy as np
from typing import Tuple, Optional
from loguru import logger

from .image_quality_detector import QualityAnalysis


class ImagePreprocessor:
    """
    Applies preprocessing operations to improve image quality for OCR.

    Operations are applied selectively based on quality analysis to minimize
    processing time while maximizing OCR accuracy.
    """

    def __init__(self):
        """Initialize the preprocessor."""
        pass

    def preprocess(self, image: np.ndarray, analysis: QualityAnalysis) -> np.ndarray:
        """
        Apply preprocessing operations based on quality analysis.

        Args:
            image: BGR image as numpy array
            analysis: Quality analysis results

        Returns:
            Preprocessed image
        """
        logger.info(
            f"Applying preprocessing (score={analysis.overall_score:.1f})"
        )

        processed = image.copy()

        # Apply operations based on detected issues
        if abs(analysis.rotation_angle) > 2.0:
            processed = self.deskew(processed, analysis.rotation_angle)

        if analysis.noise_level > 30.0:
            processed = self.denoise(processed)

        if analysis.contrast_score < 50.0:
            processed = self.enhance_contrast(processed)

        # Always try to detect and crop borders for photos
        if not analysis.is_likely_scan:
            processed = self.detect_and_crop_borders(processed)

        return processed

    def deskew(self, image: np.ndarray, angle: float) -> np.ndarray:
        """
        Rotate image to correct skew.

        Args:
            image: Input image
            angle: Rotation angle in degrees

        Returns:
            Deskewed image
        """
        if abs(angle) < 0.5:  # Skip if angle is negligible
            return image

        logger.debug(f"Deskewing image by {angle:.2f} degrees")

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)

        # Calculate rotation matrix
        M = cv2.getRotationMatrix2D(center, angle, 1.0)

        # Perform rotation
        rotated = cv2.warpAffine(
            image,
            M,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )

        return rotated

    def denoise(self, image: np.ndarray) -> np.ndarray:
        """
        Reduce noise using Non-local Means Denoising.

        Args:
            image: Input image

        Returns:
            Denoised image
        """
        logger.debug("Applying denoising")

        # Use fastNlMeansDenoisingColored for color images
        denoised = cv2.fastNlMeansDenoisingColored(
            image,
            None,
            h=10,  # Filter strength for luminance
            hColor=10,  # Filter strength for color
            templateWindowSize=7,
            searchWindowSize=21
        )

        return denoised

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).

        Args:
            image: Input image

        Returns:
            Enhanced image
        """
        logger.debug("Enhancing contrast")

        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

        # Split channels
        l, a, b = cv2.split(lab)

        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)

        # Merge channels back
        lab_enhanced = cv2.merge([l_enhanced, a, b])

        # Convert back to BGR
        enhanced = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        return enhanced

    def detect_and_crop_borders(self, image: np.ndarray) -> np.ndarray:
        """
        Detect document borders and crop to document area.
        Uses contour detection to find the largest rectangular region.

        Args:
            image: Input image

        Returns:
            Cropped image (or original if detection fails)
        """
        logger.debug("Detecting and cropping borders")

        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)

            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)

            # Dilate edges to close gaps
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            dilated = cv2.dilate(edges, kernel, iterations=2)

            # Find contours
            contours, _ = cv2.findContours(
                dilated,
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            if not contours:
                return image

            # Find the largest contour
            largest_contour = max(contours, key=cv2.contourArea)
            contour_area = cv2.contourArea(largest_contour)
            image_area = image.shape[0] * image.shape[1]

            # Only crop if contour is significant (>30% of image area)
            # and not too large (>95% suggests no clear border)
            area_ratio = contour_area / image_area
            if area_ratio < 0.3 or area_ratio > 0.95:
                logger.debug(f"Border detection skipped (area ratio: {area_ratio:.2f})")
                return image

            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(largest_contour)

            # Add small padding
            padding = 10
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(image.shape[1] - x, w + 2 * padding)
            h = min(image.shape[0] - y, h + 2 * padding)

            # Crop to bounding rectangle
            cropped = image[y:y+h, x:x+w]

            logger.debug(f"Cropped from {image.shape[:2]} to {cropped.shape[:2]}")
            return cropped

        except Exception as e:
            logger.debug(f"Border detection failed: {e}")
            return image

    def sharpen(self, image: np.ndarray) -> np.ndarray:
        """
        Apply sharpening filter to enhance text edges.

        Args:
            image: Input image

        Returns:
            Sharpened image
        """
        logger.debug("Sharpening image")

        # Define sharpening kernel
        kernel = np.array([
            [-1, -1, -1],
            [-1,  9, -1],
            [-1, -1, -1]
        ])

        # Apply kernel
        sharpened = cv2.filter2D(image, -1, kernel)

        return sharpened

    def adaptive_threshold(self, image: np.ndarray) -> np.ndarray:
        """
        Apply adaptive thresholding for binarization.
        Useful for documents with varying illumination.

        Args:
            image: Input image

        Returns:
            Binarized image
        """
        logger.debug("Applying adaptive thresholding")

        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # Apply adaptive thresholding
        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2
        )

        # Convert back to BGR for consistency
        binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

        return binary_bgr
