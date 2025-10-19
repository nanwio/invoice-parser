from typing import Generator
from pdf2image import convert_from_path
from PIL import Image
import numpy as np
import cv2
import io
from loguru import logger

from .image_quality_detector import ImageQualityDetector
from .image_preprocessor import ImagePreprocessor


class ImageHandler:
    """
    Handles PDF/image conversion and optimization for OCR.
    Uses a generator for memory-efficient PDF processing.

    Features smart preprocessing: only applies enhancement operations
    when image quality analysis indicates they're needed.
    """

    def __init__(self):
        """Initialize quality detector and preprocessor."""
        self.quality_detector = ImageQualityDetector()
        self.preprocessor = ImagePreprocessor()

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

        Applies intelligent preprocessing based on quality analysis:
        - High quality images: minimal processing (~50ms)
        - Low quality images: full preprocessing pipeline (~850ms)
        """
        # Ensure image is in RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Smart resize: balance speed and quality for invoices
        # Only resize very large images (>2000px) to avoid quality loss
        max_dimension = 2000
        if max(image.size) > max_dimension:
            ratio = max_dimension / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        # Convert to BGR for OpenCV/Paddle
        bgr_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Analyze quality and apply preprocessing if needed
        analysis = self.quality_detector.analyze(bgr_image)

        if analysis.needs_preprocessing:
            logger.info(
                f"Image quality score: {analysis.overall_score:.1f} - "
                f"Applying preprocessing to improve OCR accuracy"
            )
            bgr_image = self.preprocessor.preprocess(bgr_image, analysis)
        else:
            logger.debug(
                f"Image quality score: {analysis.overall_score:.1f} - "
                f"Skipping preprocessing (good quality)"
            )

        return bgr_image
