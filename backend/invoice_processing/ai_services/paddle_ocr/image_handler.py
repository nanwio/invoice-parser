from typing import Generator
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import cv2
import io

class ImageHandler:
    """
    Handles PDF/image conversion and optimization for OCR.
    Uses a generator for memory-efficient PDF processing.
    """

    def convert_pdf_to_images(self, pdf_path: str) -> Generator[Image.Image, None, None]:
        """
        Convert PDF to a generator of PIL Images, one for each page.
        This is highly memory-efficient for large PDFs.
        
        Args:
            pdf_path: Path to the PDF file.
            
        Yields:
            A PIL Image for each page in the PDF.
        """
        optimal_dpi = 150
        
        images_from_pdf = convert_from_path(
            pdf_path, 
            dpi=optimal_dpi,
            fmt='RGB',
            thread_count=4
        )
        
        for image in images_from_pdf:
            yield image

    def convert_bytes_to_image(self, image_bytes: bytes) -> Image.Image:
        """
        Converts raw image bytes into a single PIL Image object.

        Args:
            image_bytes: The byte content of the image file (e.g., JPEG, PNG).

        Returns:
            A PIL Image object.
        """
        return Image.open(io.BytesIO(image_bytes))

    def optimize_image_for_ocr(self, image: Image.Image) -> np.ndarray:
        """
        Convert a PIL Image to a BGR NumPy array suitable for PaddleOCR.
        """
        # Ensure image is in RGB, then convert to BGR for OpenCV/Paddle
        if image.mode != 'RGB':
            image = image.convert('RGB')
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
