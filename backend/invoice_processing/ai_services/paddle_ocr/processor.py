import asyncio
import gc
from loguru import logger
from paddleocr import PaddleOCR

from .config import PaddleConfig
from .image_handler import ImageHandler
from .ocr_executor import OcrExecutor

class PaddleProcessor:
    """
    Orchestrates the invoice processing pipeline using PaddleOCR.
    
    This class coordinates the configuration, image handling, and OCR execution
    components to process a PDF invoice and extract its text content.
    """

    def __init__(self, config_type: str = "balanced"):
        """
        Initializes the PaddleProcessor and its components.
        
        Args:
            config_type: "ultra_fast", "balanced", or "high_quality".
        """
        self.config_type = config_type
        
        config = PaddleConfig.get_config(config_type)
        self.ocr_engine = PaddleOCR(**config)
        
        self.image_handler = ImageHandler(config_type)
        self.ocr_executor = OcrExecutor(self.ocr_engine, self.image_handler, config_type)

    async def process_invoice_async(self, pdf_path: str) -> str:
        """
        Asynchronously processes a PDF invoice to extract text.
        
        Args:
            pdf_path: The file path to the PDF invoice.
            
        Returns:
            A string containing all extracted text from the invoice.
        """
        start_time = asyncio.get_event_loop().time()
        
        logger.info("Step 1: Converting PDF to images...")
        images = self.image_handler.convert_pdf_to_images(pdf_path)
        conversion_time = asyncio.get_event_loop().time() - start_time
        
        logger.info("Step 2: Running parallel OCR on images...")
        ocr_start = asyncio.get_event_loop().time()
        text_lines = await self.ocr_executor.run_ocr_on_images_parallel(images)
        ocr_time = asyncio.get_event_loop().time() - ocr_start
        
        # Clean up memory-intensive image objects
        del images
        gc.collect()
        
        total_time = asyncio.get_event_loop().time() - start_time
        logger.info(
            f"PaddleOCR processing complete in {total_time:.2f}s "
            f"(PDF conversion: {conversion_time:.2f}s, Parallel OCR: {ocr_time:.2f}s)"
        )
        
        return "\n".join(text_lines)

    def process_invoice(self, pdf_path: str) -> str:
        """
        Synchronous wrapper for the asynchronous processing pipeline.
        """
        return asyncio.run(self.process_invoice_async(pdf_path))

    def __del__(self):
        """Ensures the thread pool is shut down when the object is destroyed."""
        if hasattr(self, 'ocr_executor'):
            self.ocr_executor.shutdown()


def create_paddle_processor(speed_priority: str = "balanced") -> PaddleProcessor:
    """
    Factory function to easily create and configure a PaddleProcessor.
    
    Args:
        speed_priority: "ultra_fast", "balanced", or "high_quality".
    
    Returns:
        An initialized PaddleProcessor instance.
    """
    return PaddleProcessor(config_type=speed_priority)
