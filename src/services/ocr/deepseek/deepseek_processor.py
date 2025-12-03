"""DeepSeek-OCR processor - Vision-Language Model for document understanding.

Replaces the multi-stage TATR+PaddleOCR pipeline with a single VLM approach.
"""

import asyncio
from typing import List, Dict, Any, Optional
from threading import Lock
import torch
from transformers import AutoModel, AutoTokenizer
from PIL import Image
from loguru import logger


class DeepSeekOCRProcessor:
    """Vision-Language Model for end-to-end OCR and table extraction.

    Single-pass processing: image → structured markdown with tables and text.
    Replaces: TATR (table detection) + PaddleOCR (text OCR) + Cell-Text Matcher.
    """

    MODEL_NAME = "deepseek-ai/DeepSeek-OCR"

    # Singleton pattern for model loading
    _model: Optional[AutoModel] = None
    _tokenizer: Optional[AutoTokenizer] = None
    _device: Optional[str] = None
    _lock: Lock = Lock()

    @classmethod
    def _initialize(cls):
        """Lazy initialization of DeepSeek-OCR model (GPU-accelerated)."""
        if cls._model is not None:
            return

        with cls._lock:
            # Double-check after acquiring lock
            if cls._model is not None:
                return

            cls._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Initializing DeepSeek-OCR on {cls._device}...")

            cls._tokenizer = AutoTokenizer.from_pretrained(
                cls.MODEL_NAME,
                trust_remote_code=True
            )

            cls._model = AutoModel.from_pretrained(
                cls.MODEL_NAME,
                _attn_implementation='flash_attention_2',
                trust_remote_code=True,
                use_safetensors=True
            )

            cls._model = cls._model.eval().to(cls._device).to(torch.bfloat16)
            logger.success(f"DeepSeek-OCR initialized on {cls._device}")

    def __init__(self):
        """Initialize processor with lazy model loading."""
        self._initialize()

    async def process_pdf_async(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Process PDF and return structured text per page.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of dicts with keys: page_number, text, markdown
        """
        from src.services.ocr.paddle.image_handler import ImageHandler

        # Convert PDF to images
        logger.debug(f"Converting PDF to images: {pdf_path}")
        images = list(ImageHandler.pdf_to_images(pdf_path))

        # Process all pages in parallel
        tasks = [self._process_image_async(img, idx + 1) for idx, img in enumerate(images)]
        results = await asyncio.gather(*tasks)

        total_chars = sum(len(r['text']) for r in results)
        logger.info(f"DeepSeek-OCR processed {len(results)} pages, {total_chars} chars total")

        return results

    async def _process_image_async(self, image: Image.Image, page_num: int) -> Dict[str, Any]:
        """Process single image with DeepSeek-OCR.

        Args:
            image: PIL Image
            page_num: Page number (1-indexed)

        Returns:
            Dict with page_number, text, markdown keys
        """
        return await asyncio.to_thread(self._process_image_sync, image, page_num)

    def _process_image_sync(self, image: Image.Image, page_num: int) -> Dict[str, Any]:
        """Synchronous image processing (runs in thread pool).

        Args:
            image: PIL Image (RGB)
            page_num: Page number

        Returns:
            Processing result with structured markdown
        """
        logger.debug(f"Processing page {page_num} with DeepSeek-OCR")

        # Ensure RGB mode
        if image.mode != 'RGB':
            image = image.convert('RGB')

        with self._lock:
            # DeepSeek-OCR inference
            # Prompt: Extract all text, tables, and structure as markdown
            result = self._model.process_image(
                image,
                prompt="Extract all text, tables, and document structure as markdown. "
                       "Preserve table layouts, numeric values, and text hierarchy."
            )

        markdown_output = result['markdown'] if isinstance(result, dict) else str(result)

        logger.debug(f"Page {page_num}: extracted {len(markdown_output)} chars")

        return {
            "page_number": page_num,
            "text": markdown_output,  # For Gemini compatibility
            "markdown": markdown_output,
        }
