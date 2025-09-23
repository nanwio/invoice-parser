from typing import List
from PIL import Image
from paddleocr import PaddleOCR
import asyncio
from concurrent.futures import ThreadPoolExecutor
from loguru import logger

from .image_handler import ImageHandler

class OcrExecutor:
    """
    Executes the PaddleOCR engine on a list of images in parallel.
    """

    def __init__(self, ocr_engine: PaddleOCR, image_handler: ImageHandler, config_type: str):
        """
        Initialize the OCR executor.
        
        Args:
            ocr_engine: An initialized PaddleOCR engine instance.
            image_handler: An instance of ImageHandler for image optimization.
            config_type: The configuration type ("ultra_fast", etc.).
        """
        self.ocr_engine = ocr_engine
        self.image_handler = image_handler
        self.config_type = config_type
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def _run_ocr_on_image_async(self, image: Image.Image) -> List[str]:
        """
        Run OCR on a single image asynchronously in a thread pool.
        """
        loop = asyncio.get_event_loop()
        
        def _ocr_sync(img):
            np_img = self.image_handler.optimize_image_for_ocr(img)
            # Pass cls=True unless in ultra_fast mode
            use_cls = self.config_type != "ultra_fast"
            result = self.ocr_engine.ocr(np_img, cls=use_cls)
            
            if result and result[0]:
                # Filter results by confidence score
                return [line[1][0] for line in result[0] if line[1][1] > 0.5]
            return []
        
        return await loop.run_in_executor(self.executor, _ocr_sync, image)

    async def run_ocr_on_images_parallel(self, images: List[Image.Image]) -> List[str]:
        """
        Run OCR on multiple images in parallel and combines the results.
        """
        logger.info(f"Processing {len(images)} pages with OCR in parallel...")
        
        tasks = [self._run_ocr_on_image_async(img) for img in images]
        results = await asyncio.gather(*tasks)
        
        all_text_lines = [line for page_lines in results for line in page_lines]
        
        return all_text_lines

    def shutdown(self):
        """Shuts down the thread pool executor."""
        self.executor.shutdown(wait=False)
