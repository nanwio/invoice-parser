# Copyright 2024 Artificial Intelligence Labs, SL

"""
PDF to Image Converter - SIMPLE and FOCUSED
One responsibility: convert PDF pages to images for OCR
"""

import io
from typing import List
from PIL import Image
from loguru import logger


class PDFImageConverter:
    """
    Converts PDF pages to images for OCR processing.
    Under 100 lines, single responsibility.
    """

    @staticmethod
    def pdf_to_images(pdf_bytes: bytes) -> List[Image.Image]:
        """
        Convert PDF pages to PIL Images using PyMuPDF (faster).

        Args:
            pdf_bytes: PDF file content as bytes

        Returns:
            List of PIL Image objects, one per page
        """
        try:
            import fitz  # PyMuPDF

            # Open PDF from bytes
            pdf_document = fitz.open("pdf", pdf_bytes)
            images = []

            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]

                # Render page to pixmap (optimized for speed)
                mat = fitz.Matrix(1.5, 1.5)  # 1.5x zoom = ~150 DPI (optimal speed/quality)
                pix = page.get_pixmap(matrix=mat)

                # Convert to PIL Image
                img_data = pix.tobytes("ppm")
                img = Image.open(io.BytesIO(img_data))
                images.append(img)

            pdf_document.close()
            logger.info(f"Converted PDF to {len(images)} images with PyMuPDF")
            return images

        except ImportError:
            logger.error("PyMuPDF not installed. Install with: uv add PyMuPDF")
            return []
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return []

    @staticmethod
    def resize_for_donut(image: Image.Image, max_size: int = 1024) -> Image.Image:
        """
        Resize image for optimal DONUT processing.

        Args:
            image: PIL Image
            max_size: Maximum dimension size

        Returns:
            Resized PIL Image
        """
        try:
            # Calculate new size maintaining aspect ratio
            width, height = image.size

            if max(width, height) <= max_size:
                return image

            if width > height:
                new_width = max_size
                new_height = int(height * max_size / width)
            else:
                new_height = max_size
                new_width = int(width * max_size / height)

            resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.debug(f"Resized image from {width}x{height} to {new_width}x{new_height}")

            return resized

        except Exception as e:
            logger.error(f"Image resize failed: {e}")
            return image


# Convenience instance
pdf_converter = PDFImageConverter()