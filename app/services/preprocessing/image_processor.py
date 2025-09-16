# Copyright 2024 Artificial Intelligence Labs, SL

import io
import base64
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pdf2image import convert_from_bytes
from typing import Optional, Tuple, List
from loguru import logger


class ImageProcessor:
    """
    Professional-grade image preprocessing for OCR optimization.
    Handles PDF conversion, noise reduction, contrast enhancement, and orientation correction.
    """

    def __init__(self, dpi: int = 300, quality: int = 95):
        self.dpi = dpi
        self.quality = quality

    def preprocess_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """
        Convert PDF to optimized base64 image for enhanced OCR.

        Args:
            pdf_bytes: Raw PDF bytes

        Returns:
            Base64 encoded optimized image
        """
        try:
            # Convert PDF to high-resolution images
            images = convert_from_bytes(
                pdf_bytes,
                dpi=self.dpi,
                fmt='PNG',
                thread_count=2,
                use_pdftocairo=True  # Better quality than poppler
            )

            if not images:
                raise ValueError("Could not extract images from PDF")

            # Process first page (most invoices are single page)
            processed_image = self._enhance_image(images[0])

            # Convert to base64
            buffer = io.BytesIO()
            processed_image.save(buffer, format='PNG', quality=self.quality, optimize=True)
            buffer.seek(0)

            b64_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            logger.info(f"Preprocessed PDF to {processed_image.size} image")

            return f"data:image/png;base64,{b64_image}"

        except Exception as e:
            logger.error(f"Image preprocessing failed: {e}")
            # Fallback to original PDF
            b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            return f"data:application/pdf;base64,{b64_pdf}"

    def _enhance_image(self, image: Image.Image) -> Image.Image:
        """
        Apply professional image enhancement techniques.
        """
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Auto-orient the image
        image = ImageOps.exif_transpose(image)

        # Convert to grayscale for better OCR (optional, can be toggled)
        # image = ImageOps.grayscale(image)

        # Noise reduction with gentle blur
        image = image.filter(ImageFilter.MedianFilter(size=3))

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)  # 20% contrast boost

        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)  # 10% sharpness boost

        # Auto-level (normalize brightness)
        image = ImageOps.autocontrast(image, cutoff=1)

        return image

    def _detect_orientation(self, image: Image.Image) -> float:
        """
        Detect image orientation using simple heuristics.
        For production, could integrate with ML-based orientation detection.
        """
        # This is a simplified version - in production you might want
        # to use more sophisticated orientation detection
        width, height = image.size

        # If significantly wider than tall, might need rotation
        if width > height * 1.5:
            return 90.0

        return 0.0

    def _auto_crop_borders(self, image: Image.Image, threshold: int = 240) -> Image.Image:
        """
        Automatically crop white/light borders to focus on content.
        """
        # Convert to numpy array for easier processing
        img_array = np.array(image.convert('L'))  # Grayscale

        # Find content boundaries
        rows_with_content = np.where(np.min(img_array, axis=1) < threshold)[0]
        cols_with_content = np.where(np.min(img_array, axis=0) < threshold)[0]

        if len(rows_with_content) == 0 or len(cols_with_content) == 0:
            return image  # No content detected, return original

        # Get bounding box
        top, bottom = rows_with_content[0], rows_with_content[-1]
        left, right = cols_with_content[0], cols_with_content[-1]

        # Add small padding
        padding = 20
        top = max(0, top - padding)
        left = max(0, left - padding)
        bottom = min(img_array.shape[0], bottom + padding)
        right = min(img_array.shape[1], right + padding)

        return image.crop((left, top, right, bottom))


# Global instance
image_processor = ImageProcessor()