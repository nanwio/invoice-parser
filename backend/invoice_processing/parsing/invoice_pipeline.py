"""
Optimized Invoice processor - FAST and EFFICIENT
One responsibility: coordinate the invoice processing pipeline
"""

import time
import asyncio
from typing import Tuple, Dict, Any
from loguru import logger
import tempfile
import os

from invoice_processing.models.invoice_data import Invoice
from invoice_processing.ai_services.gemini_processor import GeminiInvoiceProcessor
from invoice_processing.ai_services.paddle_ocr import create_paddle_processor
from invoice_processing.validation.invoice_checker import InvoiceValidator
from invoice_processing.utilities.document_utils import document_utils


class InvoiceProcessor:
    """
    Invoice processing pipeline with parallel execution:
    1. OCR (Optimized PaddleOCR)
    2. Structuring (Gemini)
    3. Validation
    """

    def __init__(self):
        """
        Initialize all required processors with a single, ultra-fast configuration.
        """
        self.gemini_processor = GeminiInvoiceProcessor()
        # Hardcoding "ultra_fast" as it's now the only mode
        self.paddle_processor = create_paddle_processor("ultra_fast")
        self.validator = InvoiceValidator()
        
        asyncio.create_task(self._warm_up_connections())
        
        logger.info("InvoiceProcessor initialized in single-mode (ultra_fast)")

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
        Processes an invoice from bytes, handling either PDF or image content.
        """
        start_time = time.perf_counter()
        logger.info(f"Starting invoice processing for content type: {content_type}")

        ocr_text = ""
        preprocessing_time = 0.0
        temp_pdf_path = None

        try:
            # Step 1: OCR (handles PDF or Image)
            logger.info("Step 1/3: Running optimized OCR")
            ocr_start = time.perf_counter()

            if content_type == "application/pdf":
                # For PDFs, we still use the temp file approach for pdf2image compatibility
                preprocessing_start = time.perf_counter()
                _, temp_pdf_path = await self._parallel_preprocessing(document_bytes)
                preprocessing_time = time.perf_counter() - preprocessing_start
                
                ocr_text = await self.paddle_processor.process_pdf_async(temp_pdf_path)
            else:
                # For images, process bytes directly
                ocr_text = await self.paddle_processor.process_image_async(document_bytes)
            
            ocr_time = time.perf_counter() - ocr_start
            logger.info(f"OCR completed in {ocr_time:.2f}s, extracted {len(ocr_text)} characters")

            # Step 2: Structure text with Gemini (parallel with PDF cleanup if it exists)
            logger.info("Step 2/3: Structuring data with Gemini")
            structuring_start = time.perf_counter()
            
            gemini_task = asyncio.create_task(
                self.gemini_processor.structure_invoice_data_from_text(ocr_text)
            )
            
            if temp_pdf_path:
                cleanup_task = asyncio.create_task(self._cleanup_temp_file(temp_pdf_path))
                invoice, gemini_metadata = await gemini_task
                await cleanup_task
            else:
                invoice, gemini_metadata = await gemini_task
            
            structuring_time = time.perf_counter() - structuring_start

            # Step 3: Fast validation
            logger.info("Step 3/3: Validating structured data")
            validation_start = time.perf_counter()
            validation_result = self.validator.validate_invoice(invoice)
            validation_time = time.perf_counter() - validation_start

        except Exception as e:
            # Ensure cleanup even on error
            await self._cleanup_temp_file(temp_pdf_path)
            raise e

        total_time = time.perf_counter() - start_time
        
        logger.info(
            f"Invoice processed in {total_time:.2f}s "
            f"(prep: {preprocessing_time:.2f}s, "
            f"ocr: {ocr_time:.2f}s, structure: {structuring_time:.2f}s, validation: {validation_time:.2f}s)"
        )
        
        processing_results = {
            **gemini_metadata,
            "validation": validation_result.to_dict(),
            "document_hash": "N/A for non-PDF files", # Hash is calculated on PDF bytes
            "processing_method": "optimized_paddle_gemini_ultra_fast",
            "total_processing_time": total_time,
            "performance_breakdown": {
                "preprocessing_time": preprocessing_time,
                "ocr_time": ocr_time,
                "structuring_time": structuring_time,
                "validation_time": validation_time
            },
            "optimization_config": "ultra_fast"
        }

        return invoice, processing_results

    async def _cleanup_temp_file(self, temp_path: str):
        """Clean up temporary file asynchronously."""
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")

# Factory functions are removed as there's only one mode now.
# The endpoint will instantiate InvoiceProcessor() directly.
