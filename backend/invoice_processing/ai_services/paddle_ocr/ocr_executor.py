from typing import List, Generator
from PIL import Image
from paddleocr import PaddleOCR
import asyncio
from concurrent.futures import ThreadPoolExecutor
from loguru import logger
from threading import Lock

from .image_handler import ImageHandler

class OcrExecutor:
    """
    Executes the PaddleOCR engine on a stream of images in parallel.
    """

    def __init__(self, ocr_engine: PaddleOCR, engine_lock: Lock, image_handler: ImageHandler):
        """
        Initialize the OCR executor.
        
        Args:
            ocr_engine: An initialized PaddleOCR engine instance.
            engine_lock: A thread lock to serialize access to the engine.
            image_handler: An instance of ImageHandler for image optimization.
        """
        self.ocr_engine = ocr_engine
        self.engine_lock = engine_lock
        self.image_handler = image_handler
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def _run_ocr_on_image_async(self, image: Image.Image) -> List[str]:
        """
        Run OCR on a single image asynchronously in a thread pool,
        ensuring thread-safe access to the OCR engine.
        """
        loop = asyncio.get_event_loop()
        
        def _ocr_sync(img):
            np_img = self.image_handler.optimize_image_for_ocr(img)
            
            # This lock prevents concurrent access to the non-thread-safe
            # ocr_engine, which is critical under high load.
            with self.engine_lock:
                result = self.ocr_engine.ocr(np_img, cls=False)
            
            if result and result[0]:
                return [line[1][0] for line in result[0] if line[1][1] > 0.5]
            return []
        
        return await loop.run_in_executor(self.executor, _ocr_sync, image)

    async def run_ocr_on_images_parallel(self, image_generator: Generator[Image.Image, None, None]) -> List[str]:
        """
        Run OCR on a generator of images in parallel.
        """
        tasks = [self._run_ocr_on_image_async(image) for image in image_generator]
        
        page_results = await asyncio.gather(*tasks)
        
        # Flatten the list of lists into a single list of text lines
        all_text_lines = [line for page in page_results for line in page]
        return all_text_lines

    def shutdown(self):
        """Shutdown the thread pool executor."""
        self.executor.shutdown(wait=True)
