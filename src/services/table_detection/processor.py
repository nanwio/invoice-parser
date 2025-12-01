"""Adapter for HybridTableProcessor to match PaddleProcessor interface.

This adapter allows drop-in replacement of the old PaddleProcessor
with the new TATR + PaddleOCR hybrid pipeline.
"""

import asyncio
import gc
from typing import List, Dict, Any
from loguru import logger
from PIL import Image

from src.services.table_detection.hybrid_processor import HybridTableProcessor
from src.services.ocr.paddle.image_handler import ImageHandler


class HybridProcessorAdapter:
    """Adapter that wraps HybridTableProcessor to match PaddleProcessor interface."""

    def __init__(self, device: str = None, confidence_threshold: float = 0.7):
        """Initialize hybrid processor adapter.

        Args:
            device: 'cuda' or 'cpu' (auto-detect if None)
            confidence_threshold: Min confidence for TATR cell detection
        """
        self.hybrid_processor = HybridTableProcessor(
            device=device,
            confidence_threshold=confidence_threshold
        )
        self.image_handler = ImageHandler()

        logger.info("HybridProcessorAdapter initialized (TATR + PaddleOCR pipeline)")

    async def process_pdf_async(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Process PDF using hybrid TATR + PaddleOCR pipeline.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of page results (same format as old PaddleProcessor)
        """
        logger.info(f"Starting hybrid table recognition for PDF: {pdf_path}")

        try:
            # Convert PDF to images
            images = list(self.image_handler.convert_pdf_to_images(pdf_path))

            # Process with hybrid pipeline
            results = await self.hybrid_processor.process_images_parallel(images)

            return results
        finally:
            gc.collect()

    async def process_image_async(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """Process single image using hybrid TATR + PaddleOCR pipeline.

        Args:
            image_bytes: Raw image bytes

        Returns:
            List with single page result (same format as old PaddleProcessor)
        """
        logger.info("Starting hybrid table recognition for single image")

        try:
            # Convert bytes to PIL Image
            image = self.image_handler.convert_bytes_to_image(image_bytes)

            # Process with hybrid pipeline
            results = await self.hybrid_processor.process_images_parallel([image])

            return results
        finally:
            gc.collect()


def create_hybrid_processor(device: str = None, confidence_threshold: float = 0.7) -> HybridProcessorAdapter:
    """Factory function to create hybrid processor.

    Args:
        device: 'cuda' or 'cpu' (auto-detect if None)
        confidence_threshold: Min confidence for TATR cell detection

    Returns:
        HybridProcessorAdapter instance
    """
    return HybridProcessorAdapter(device=device, confidence_threshold=confidence_threshold)
