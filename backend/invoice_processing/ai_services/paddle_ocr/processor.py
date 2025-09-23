import asyncio
import gc
from loguru import logger
from paddleocr import PaddleOCR
from threading import Lock
from typing import Optional, Any, List, Dict

from .config import PaddleConfig
from .image_handler import ImageHandler
from .ocr_executor import OcrExecutor


class PaddleOCRProvider:
    """
    Manages the lifecycle of the PaddleOCR engine as a singleton.
    This ensures the engine is initialized only once (lazy initialization).
    """
    _ocr_engine: Optional[Any] = None
    _engine_lock: Optional[Lock] = None

    @classmethod
    def _initialize(cls):
        if cls._ocr_engine is None:
            logger.info("Lazy-initializing PaddleOCR engine on first request...")
            try:
                config = PaddleConfig.get_config()
                cls._ocr_engine = PaddleOCR(**config)
                cls._engine_lock = Lock()
                logger.success("PaddleOCR engine and lock initialized successfully.")
            except Exception as e:
                logger.critical(f"Failed to initialize PaddleOCR engine: {e}")
                raise RuntimeError(f"Could not initialize OCR Engine: {e}") from e

    @classmethod
    def get_engine(cls) -> Any:
        cls._initialize()
        return cls._ocr_engine

    @classmethod
    def get_lock(cls) -> Lock:
        cls._initialize()
        if cls._engine_lock is None:
            raise RuntimeError("Engine lock was not initialized.")
        return cls._engine_lock


class PaddleProcessor:
    """
    Orchestrates the invoice processing pipeline using PaddleOCR.
    """

    def __init__(self):
        """
        Initializes the PaddleProcessor, getting dependencies from the provider.
        """
        self.ocr_engine = PaddleOCRProvider.get_engine()
        self.engine_lock = PaddleOCRProvider.get_lock()
        self.image_handler = ImageHandler()
        self.ocr_executor = OcrExecutor(self.ocr_engine, self.engine_lock, self.image_handler)

    async def process_pdf_async(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Processes a PDF and returns structured text page by page.
        """
        logger.info(f"Starting async OCR for PDF: {pdf_path}")
        try:
            image_generator = self.image_handler.convert_pdf_to_images(pdf_path)
            return await self.ocr_executor.run_ocr_on_images_parallel(image_generator)
        finally:
            gc.collect()

    async def process_image_async(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Processes a single image and returns structured text.
        """
        logger.info("Starting async OCR for single image")
        try:
            image = self.image_handler.convert_bytes_to_image(image_bytes)
            image_generator = (img for img in [image])
            return await self.ocr_executor.run_ocr_on_images_parallel(image_generator)
        finally:
            gc.collect()

    def __del__(self):
        """Destructor to clean up resources."""
        if hasattr(self, 'ocr_executor'):
            self.ocr_executor.shutdown()


def create_paddle_processor() -> PaddleProcessor:
    """
    Factory function to easily create the single-mode PaddleProcessor.
    """
    return PaddleProcessor()
