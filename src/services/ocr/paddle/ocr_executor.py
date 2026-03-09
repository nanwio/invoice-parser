from typing import Generator, Any
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
        # OPTIMIZATION: Reduced from 4 to 1 worker
        # GPU operations are serialized by engine_lock anyway,
        # so multiple workers just add context switching overhead
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def _run_ocr_on_image_async(self, page_index: int, image: Image.Image) -> tuple[int, list[str]]:
        """
        Run OCR on a single image, returning the page index and extracted text lines.
        """
        loop = asyncio.get_event_loop()
        
        def _ocr_sync(img):
            np_img = self.image_handler.optimize_image_for_ocr(img)
            with self.engine_lock:
                result = self.ocr_engine.ocr(np_img, cls=False)

            if result and result[0]:
                text_lines = []
                for line in result[0]:
                    if isinstance(line, (list, tuple)) and len(line) >= 2:
                        text_data = line[1]
                        if isinstance(text_data, (list, tuple)) and len(text_data) >= 2:
                            text, confidence = text_data[0], text_data[1]
                            if confidence > 0.5:
                                text_lines.append(text)
                return text_lines
            return []
        
        text_lines = await loop.run_in_executor(self.executor, _ocr_sync, image)
        return (page_index, text_lines)

    async def run_ocr_on_images_parallel(self, image_generator: Generator[Image.Image, None, None]) -> list[dict[str, Any]]:
        """
        Run OCR on a generator of images, returning structured page-by-page results.
        """
        tasks = [
            self._run_ocr_on_image_async(i, image) 
            for i, image in enumerate(image_generator, start=1)
        ]
        
        # Results will be a list of tuples: [(page_index, text_lines), ...]
        page_results_tuples = await asyncio.gather(*tasks)
        
        # Sort results by page index to ensure correct order
        page_results_tuples.sort(key=lambda x: x[0])
        
        # Format into the final structured list
        structured_results = [
            {"page_number": page_index, "text": " ".join(text_lines)}
            for page_index, text_lines in page_results_tuples
        ]
        
        return structured_results

    def shutdown(self):
        """Shutdown the thread pool executor."""
        self.executor.shutdown(wait=True)
