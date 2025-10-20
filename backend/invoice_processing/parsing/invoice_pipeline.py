"""
Optimized Invoice processor with Gemini Vision support
One responsibility: coordinate the invoice processing pipeline
"""

import time
import asyncio
from typing import Tuple, Dict, Any, List
from loguru import logger
import tempfile
import os
import io
from PIL import Image
from pdf2image import convert_from_bytes, convert_from_path

from invoice_processing.models.invoice_data import Invoice
from invoice_processing.ai_services.gemini_processor import GeminiInvoiceProcessor
from invoice_processing.ai_services.paddle_ocr import create_paddle_processor
from invoice_processing.validation.invoice_checker import InvoiceValidator
from invoice_processing.utilities.document_utils import document_utils


class InvoiceProcessor:
    """
    Invoice processing pipeline with Gemini Vision (multimodal):
    1. Convert PDF to images OR use image directly
    2. Structuring (Gemini Vision - sees document layout)
    3. Validation

    Vision mode provides superior accuracy for complex multi-page invoices
    because Gemini can SEE the visual structure, not just read text.
    """

    def __init__(self, use_vision: bool = True, use_ocr_fallback: bool = False):
        """
        Initialize processor with vision mode enabled by default.

        Args:
            use_vision: If True, use Gemini Vision (multimodal). If False, use text-only OCR mode.
            use_ocr_fallback: If True, keep PaddleOCR as fallback if vision fails.
        """
        self.use_vision = use_vision
        self.use_ocr_fallback = use_ocr_fallback

        self.gemini_processor = GeminiInvoiceProcessor(vision_mode=use_vision)
        self.validator = InvoiceValidator()

        # Initialize PaddleOCR only if needed as fallback
        if use_ocr_fallback:
            self.paddle_processor = create_paddle_processor()
            logger.info("PaddleOCR initialized as fallback")
        else:
            self.paddle_processor = None

        asyncio.create_task(self._warm_up_connections())

        mode = "VISION" if use_vision else "OCR+TEXT"
        logger.info(f"InvoiceProcessor initialized in {mode} mode")

    async def _warm_up_connections(self):
        """Pre-warm connections and models for faster processing."""
        try:
            # Warm up Gemini connection
            await self.gemini_processor._warm_up_connection()
            logger.debug("Gemini connection warmed up")
        except Exception as e:
            logger.warning(f"Connection warm-up failed: {e}")

    async def _parallel_preprocessing(self, pdf_bytes: bytes) -> Tuple[str, str]:
        """
        Run document hash calculation and temp file creation in parallel.
        
        Returns:
            Tuple of (document_hash, temp_file_path)
        """
        async def calculate_hash():
            return document_utils.calculate_file_hash(pdf_bytes)
        
        async def create_temp_file():
            temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_pdf.write(pdf_bytes)
            temp_pdf.close()
            return temp_pdf.name
        
        # Run both operations in parallel
        doc_hash, temp_path = await asyncio.gather(
            calculate_hash(),
            create_temp_file()
        )
        
        return doc_hash, temp_path

    async def process_invoice(self, document_bytes: bytes, content_type: str) -> tuple[Invoice, dict]:
        """
        Processes an invoice from bytes using Gemini Vision (multimodal).

        For PDFs: Converts pages to images and sends to Gemini Vision
        For Images: Sends directly to Gemini Vision

        Vision mode allows Gemini to SEE the document structure, providing
        superior accuracy for complex multi-page invoices with tables and sections.
        """
        start_time = time.perf_counter()
        logger.info(f"Starting invoice processing for content type: {content_type}")

        conversion_time = 0.0
        images = []

        try:
            # Step 1: Convert document to images
            logger.info("Step 1/3: Converting document to images for Vision mode")
            conversion_start = time.perf_counter()

            if content_type == "application/pdf":
                # Convert PDF to images using pdf2image
                logger.info("Converting PDF pages to images...")
                images = await asyncio.to_thread(
                    convert_from_bytes,
                    document_bytes,
                    dpi=150,  # Reduced from 300 for speed, still high quality
                    fmt='jpeg',
                    jpegopt={'quality': 85, 'optimize': True}
                )
                logger.info(f"Converted {len(images)} PDF pages to images")
            else:
                # For image files, load directly
                image = Image.open(io.BytesIO(document_bytes))
                images = [image]
                logger.info("Loaded image directly")

            conversion_time = time.perf_counter() - conversion_start
            logger.info(f"Image conversion completed in {conversion_time:.2f}s")

            # Step 2: Structure with Gemini Vision (multimodal)
            logger.info("Step 2/3: Structuring data with Gemini Vision (multimodal)")
            structuring_start = time.perf_counter()

            if self.use_vision:
                invoice, gemini_metadata = await self.gemini_processor.structure_invoice_data_from_images(images)
            else:
                # Fallback to OCR mode if vision disabled
                if not self.paddle_processor:
                    raise ValueError("OCR mode requested but PaddleOCR not initialized")
                # TODO: Implement OCR fallback path
                raise NotImplementedError("OCR fallback not yet implemented in this version")

            structuring_time = time.perf_counter() - structuring_start

            # Step 3: Fast validation
            logger.info("Step 3/3: Validating structured data")
            validation_start = time.perf_counter()
            validation_result = self.validator.validate_invoice(invoice)
            validation_time = time.perf_counter() - validation_start

        except Exception as e:
            logger.error(f"Invoice processing failed: {e}")
            raise e

        total_time = time.perf_counter() - start_time

        logger.info(
            f"Invoice processed in {total_time:.2f}s "
            f"(conversion: {conversion_time:.2f}s, "
            f"structure: {structuring_time:.2f}s, validation: {validation_time:.2f}s)"
        )

        processing_results = {
            **gemini_metadata,
            "validation": validation_result.to_dict(),
            "document_hash": "N/A for non-PDF files",
            "processing_method": "gemini_vision_multimodal",
            "total_processing_time": total_time,
            "performance_breakdown": {
                "image_conversion_time": conversion_time,
                "structuring_time": structuring_time,
                "validation_time": validation_time
            },
            "optimization_config": "vision_mode"
        }

        return invoice, processing_results

    def _format_ocr_results_for_llm(self, ocr_results: list[dict]) -> str:
        """
        Formats the structured OCR results into a single string with page delimiters.
        """
        formatted_parts = []
        for result in ocr_results:
            page_num = result.get("page_number", "N/A")
            text = result.get("text", "")
            formatted_parts.append(f"[INICIO PÁGINA {page_num}]\n{text}\n[FIN PÁGINA {page_num}]")
        
        return "\n\n".join(formatted_parts)

    async def _cleanup_temp_file(self, temp_path: str):
        """Clean up temporary file asynchronously."""
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")

# Factory functions are removed as there's only one mode now.
# The endpoint will instantiate InvoiceProcessor() directly.
