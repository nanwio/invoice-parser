from typing import List
from pdf2image import convert_from_path
from PIL import Image
import numpy as np

class ImageHandler:
    """
    Handles PDF to image conversion and image optimization for OCR.
    """

    def __init__(self, config_type: str = "balanced"):
        """
        Initialize the image handler with a specific configuration type.
        
        Args:
            config_type: "ultra_fast", "balanced", or "high_quality".
        """
        self.config_type = config_type

    def convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """
        Convert PDF to a list of PIL Images with optimized settings.
        
        Args:
            pdf_path: Path to the PDF file.
            
        Returns:
            A list of PIL Images.
        """
        dpi_map = {
            "ultra_fast": 150,
            "balanced": 200,
            "high_quality": 250
        }
        optimal_dpi = dpi_map.get(self.config_type, 200)
        
        return convert_from_path(
            pdf_path, 
            dpi=optimal_dpi,
            fmt='RGB',
            thread_count=4
        )

    def optimize_image_for_ocr(self, image: Image.Image) -> np.ndarray:
        """
        Optimize a single image for OCR processing (resize, convert to numpy).
        
        Args:
            image: PIL Image to optimize.
            
        Returns:
            An optimized numpy array of the image.
        """
        np_img = np.array(image)
        
        height, width = np_img.shape[:2]
        max_dimension = 2000
        
        if max(height, width) > max_dimension:
            scale_factor = max_dimension / max(height, width)
            new_height = int(height * scale_factor)
            new_width = int(width * scale_factor)
            
            image_resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            np_img = np.array(image_resized)
            
        return np_img
