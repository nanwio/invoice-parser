"""PaddleOCR text detection and recognition (no table structure).

Simplified processor that only extracts text boxes with coordinates.
Table structure detection is delegated to TATR.
"""

import asyncio
from typing import List, Dict, Any, Optional
from threading import Lock
import numpy as np
import cv2
from PIL import Image
from loguru import logger
from paddleocr import PaddleOCR
import paddle

from src.services.table_detection.cell_text_matcher import TextBox


class PaddleOCRTextProvider:
    """Singleton provider for PaddleOCR text-only engine."""

    _ocr_engine: Optional[PaddleOCR] = None
    _gpu_lock: Optional[Lock] = None
    _is_gpu_available: bool = False

    @classmethod
    def _initialize(cls):
        """Initialize PaddleOCR text-only engine if not already initialized."""
        if cls._ocr_engine is not None:
            return

        logger.info("Initializing PaddleOCR text-only engine...")

        # Auto-detect GPU
        cls._is_gpu_available = paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0

        if cls._is_gpu_available:
            logger.info(f"GPU detected for PaddleOCR: {paddle.device.cuda.device_count()} device(s)")
        else:
            logger.info("No GPU detected - PaddleOCR running in CPU mode")

        # Initialize PaddleOCR (text detection + recognition only, no table structure)
        cls._ocr_engine = PaddleOCR(
            use_angle_cls=False,  # Skip angle classification for speed
            lang='en',
            use_gpu=cls._is_gpu_available,
            show_log=False,
            enable_mkldnn=False,
            cpu_threads=1,
            # Detection model parameters for better small text detection
            det_db_thresh=0.3,  # Lower threshold for text detection (default: 0.3)
            det_db_box_thresh=0.5,  # Lower threshold for bounding box filtering (default: 0.6)
            det_db_unclip_ratio=1.6,  # Expand detected boxes slightly (default: 1.5)
            # Recognition parameters
            rec_batch_num=6,  # Batch size for recognition (default: 6)
        )

        cls._gpu_lock = Lock()
        logger.success(f"PaddleOCR text engine initialized ({'GPU' if cls._is_gpu_available else 'CPU'} mode)")

    @classmethod
    def get_ocr(cls) -> PaddleOCR:
        """Get singleton PaddleOCR instance."""
        cls._initialize()
        return cls._ocr_engine

    @classmethod
    def get_lock(cls) -> Lock:
        """Get singleton GPU lock."""
        cls._initialize()
        return cls._gpu_lock

    @classmethod
    def is_gpu_available(cls) -> bool:
        """Check if GPU is available."""
        cls._initialize()
        return cls._is_gpu_available


class TextRegion:
    """Detected text region from PaddleOCR."""

    def __init__(self, text: str, bbox: List[float], confidence: float):
        self.text = text
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.confidence = confidence


class PaddleTextDetector:
    """PaddleOCR for text detection/recognition only (no table structure)."""

    def __init__(self, ocr_engine=None, gpu_lock=None):
        """Initialize with optional dependency injection.

        Args:
            ocr_engine: PaddleOCR engine (default: from provider)
            gpu_lock: GPU lock (default: from provider)
        """
        self.ocr_engine = ocr_engine if ocr_engine is not None else PaddleOCRTextProvider.get_ocr()
        self.gpu_lock = gpu_lock if gpu_lock is not None else PaddleOCRTextProvider.get_lock()
        self._is_gpu_available = PaddleOCRTextProvider.is_gpu_available()

        logger.info(
            f"PaddleTextDetector initialized "
            f"({'GPU mode with lock' if self._is_gpu_available else 'CPU mode'})"
        )

    async def detect_text_async(self, image: Image.Image) -> List[TextBox]:
        """Detect and recognize text in image (async).

        Args:
            image: PIL Image (RGB)

        Returns:
            List of TextBox objects with text and bounding boxes
        """
        return await asyncio.to_thread(self._detect_text_sync, image)

    def _detect_text_sync(self, image: Image.Image) -> List[TextBox]:
        """Synchronous text detection (runs in thread pool)."""

        # Convert PIL to OpenCV format (BGR)
        # Ensure image is in RGB mode (defensive - should already be RGB from caller)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        img_array = np.array(image)
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # Run OCR with GPU lock
        with self.gpu_lock:
            ocr_result = self.ocr_engine.ocr(img_array, cls=True)

        # Parse results
        text_boxes = []

        if ocr_result and ocr_result[0]:
            for line in ocr_result[0]:
                if len(line) < 2:
                    continue

                # Extract bbox and text info
                points = line[0]  # [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                text_info = line[1]  # (text, confidence)

                if not text_info or not text_info[0]:
                    continue

                text = text_info[0]
                confidence = float(text_info[1])

                # Convert polygon to axis-aligned bounding box
                x_coords = [p[0] for p in points]
                y_coords = [p[1] for p in points]
                bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]

                text_boxes.append(TextBox(text, bbox, confidence))

        logger.debug(f"Detected {len(text_boxes)} text regions")

        return text_boxes

    async def detect_text_from_pdf_async(self, pdf_path: str) -> List[List[TextBox]]:
        """Detect text from all pages of a PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of text boxes per page
        """
        from src.services.ocr.paddle.image_handler import ImageHandler

        # Convert PDF to images
        images = await asyncio.to_thread(ImageHandler.pdf_to_images, pdf_path)

        # Process pages in parallel
        tasks = [self.detect_text_async(img) for img in images]
        results = await asyncio.gather(*tasks)

        total_texts = sum(len(page_texts) for page_texts in results)
        logger.info(f"Extracted {total_texts} text regions from {len(results)} pages")

        return results
