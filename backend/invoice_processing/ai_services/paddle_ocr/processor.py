import asyncio
import gc
from loguru import logger
from paddleocr import PaddleOCR
from threading import Lock
from typing import Optional, Any, List, Dict

from .config import PaddleConfig
from .image_handler import ImageHandler
from .ocr_executor import OcrExecutor
from .table_processor import InvoiceTableProcessor


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
    Orchestrates the invoice processing pipeline using PaddleOCR with table recognition.
    """

    def __init__(self, use_table_recognition: bool = True):
        """
        Initializes the PaddleProcessor.

        Args:
            use_table_recognition: If True, use specialized table modules (recommended for invoices)
        """
        self.use_table_recognition = use_table_recognition
        self.image_handler = ImageHandler()

        if use_table_recognition:
            # Use specialized table processor for invoices
            try:
                self.table_processor = InvoiceTableProcessor()
                logger.info("Using table recognition mode for invoice processing")
            except (ImportError, SystemExit, Exception) as e:
                logger.warning(f"Table recognition unavailable: {e}. Falling back to standard OCR")
                self.use_table_recognition = False

        if not self.use_table_recognition:
            # Fallback to standard OCR
            self.ocr_engine = PaddleOCRProvider.get_engine()
            self.engine_lock = PaddleOCRProvider.get_lock()
            self.ocr_executor = OcrExecutor(self.ocr_engine, self.engine_lock, self.image_handler)

    async def process_pdf_async(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Processes a PDF and returns structured text page by page.

        Uses table recognition if enabled, otherwise falls back to standard OCR.
        """
        logger.info(f"Starting async {'table recognition' if self.use_table_recognition else 'OCR'} for PDF: {pdf_path}")

        try:
            if self.use_table_recognition:
                # Use table processor for better structure preservation
                images = list(self.image_handler.convert_pdf_to_images(pdf_path))
                results = await self.table_processor.process_images_parallel(images)
                return results
            else:
                # Fallback to standard OCR
                image_generator = self.image_handler.convert_pdf_to_images(pdf_path)
                return await self.ocr_executor.run_ocr_on_images_parallel(image_generator)
        finally:
            gc.collect()

    async def process_image_async(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Processes a single image and returns structured text.

        Uses table recognition if enabled, otherwise falls back to standard OCR.
        """
        logger.info(f"Starting async {'table recognition' if self.use_table_recognition else 'OCR'} for single image")

        try:
            image = self.image_handler.convert_bytes_to_image(image_bytes)

            if self.use_table_recognition:
                # Use table processor for better structure preservation
                results = await self.table_processor.process_images_parallel([image])
                return results
            else:
                # Fallback to standard OCR
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
