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
            use_ocr_fallback: If True, initialize PaddleOCR (required for OCR mode or fallback).
        """
        self.use_vision = use_vision
        self.use_ocr_fallback = use_ocr_fallback

        self.gemini_processor = GeminiInvoiceProcessor(vision_mode=use_vision)
        self.validator = InvoiceValidator()

        # Initialize PaddleOCR when in OCR mode OR when requested as fallback
        if use_ocr_fallback or not use_vision:
            self.paddle_processor = create_paddle_processor()
            logger.info(f"PaddleOCR initialized ({'primary mode' if not use_vision else 'fallback'})")
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
        Processes an invoice from bytes using either Vision or OCR mode.

        Vision mode: Converts to images and sends to Gemini Vision (slower, more accurate)
        OCR mode: Uses PaddleOCR to extract text, then Gemini Text to structure (faster, cost-effective)

        Args:
            document_bytes: Raw document bytes
            content_type: MIME type (application/pdf or image/*)

        Returns:
            Tuple of (Invoice object, processing metadata dict)
        """
        start_time = time.perf_counter()
        mode = "VISION" if self.use_vision else "OCR"
        logger.info(f"Starting invoice processing in {mode} mode for content type: {content_type}")

        conversion_time = 0.0
        ocr_time = 0.0
        structuring_time = 0.0
        validation_time = 0.0

        try:
            if self.use_vision:
                # ============ VISION MODE ============
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

                invoice, gemini_metadata = await self.gemini_processor.structure_invoice_data_from_images(images)
                structuring_time = time.perf_counter() - structuring_start

            else:
                # ============ OCR MODE ============
                if not self.paddle_processor:
                    raise ValueError("OCR mode requested but PaddleOCR not initialized")

                logger.info("Step 1/3: Extracting text with PaddleOCR")
                ocr_start = time.perf_counter()

                # Create temporary file for PaddleOCR processing
                if content_type == "application/pdf":
                    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    temp_pdf.write(document_bytes)
                    temp_pdf.close()

                    try:
                        ocr_results = await self.paddle_processor.process_pdf_async(temp_pdf.name)
                    finally:
                        await self._cleanup_temp_file(temp_pdf.name)
                else:
                    # Process image directly from bytes
                    ocr_results = await self.paddle_processor.process_image_async(document_bytes)

                ocr_time = time.perf_counter() - ocr_start
                logger.info(f"OCR extraction completed in {ocr_time:.2f}s, {len(ocr_results)} page(s)")

                # Step 2: Format OCR text for Gemini
                logger.info("Step 2/3: Structuring data with Gemini Text (from OCR)")
                structuring_start = time.perf_counter()

                formatted_text = self._format_ocr_results_for_llm(ocr_results)
                invoice, gemini_metadata = await self.gemini_processor.structure_invoice_data_from_text(formatted_text)

                structuring_time = time.perf_counter() - structuring_start

            # Step 3: Fast validation (common for both modes)
            logger.info("Step 3/3: Validating structured data")
            validation_start = time.perf_counter()
            validation_result = self.validator.validate_invoice(invoice)
            validation_time = time.perf_counter() - validation_start

        except Exception as e:
            logger.error(f"Invoice processing failed in {mode} mode: {e}")
            raise e

        total_time = time.perf_counter() - start_time

        logger.info(
            f"Invoice processed in {total_time:.2f}s "
            f"({mode} mode: OCR={ocr_time:.2f}s, conversion={conversion_time:.2f}s, "
            f"structure={structuring_time:.2f}s, validation={validation_time:.2f}s)"
        )

        processing_results = {
            **gemini_metadata,
            "validation": validation_result.to_dict(),
            "document_hash": "N/A for non-PDF files",
            "processing_method": "gemini_vision_multimodal" if self.use_vision else "paddleocr_gemini_text",
            "total_processing_time": total_time,
            "performance_breakdown": {
                "ocr_time": ocr_time,
                "image_conversion_time": conversion_time,
                "structuring_time": structuring_time,
                "validation_time": validation_time
            },
            "optimization_config": "vision_mode" if self.use_vision else "ocr_mode"
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
