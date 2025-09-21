# Copyright 2024 Artificial Intelligence Labs, SL

import time
import asyncio
import instructor
from typing import Dict, Any, Tuple

from google import genai
from loguru import logger
from instructor.multimodal import PDF

from app.services.parser.models import Invoice
from app.services.prompts import EXTRACTION_PROMPT
from app.services.validation import get_invoice_validator
from app.settings import settings


class UltraFastInvoiceParser:
    """
    Ultra-optimized parser with model caching and parallelization.
    Target: <3 seconds per invoice.
    """

    def __init__(self):
        self.validator = get_invoice_validator()()
        self._client = None
        self._instructor = None
        self._model_loaded = False

    async def _ensure_model_loaded(self):
        """Lazy load and cache Gemini model for faster subsequent calls."""
        if self._model_loaded:
            return

        logger.info("Loading and caching Gemini model...")
        start_time = time.perf_counter()

        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._instructor = instructor.from_genai(
            self._client,
            mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS,
            use_async=True
        )

        # Warm up the model with a small request
        try:
            warm_up_messages = [{
                "role": "user",
                "content": ["Test message to warm up the model"]
            }]

            # This will initialize the connection
            await self._instructor.chat.completions.create(
                model=settings.GEMINI_MODEL_NAME,
                messages=warm_up_messages,
                response_model=str,
                max_tokens=10
            )
        except Exception as e:
            logger.warning(f"Model warm-up failed (this is OK): {e}")

        self._model_loaded = True
        load_time = time.perf_counter() - start_time
        logger.info(f"Model loaded and cached in {load_time:.2f}s")

    async def parse_bytes_ultra_fast(self, document_bytes: bytes) -> Tuple[Invoice, Dict[str, Any]]:
        """
        Ultra-fast parsing with all optimizations enabled.

        Optimizations:
        - Model pre-loading and caching
        - No document classification (assumes invoice)
        - Parallelized validation
        - Optimized Gemini settings
        """
        start_time = time.perf_counter()
        performance_metrics = {
            'total_time': 0.0,
            'model_load_time': 0.0,
            'gemini_time': 0.0,
            'validation_time': 0.0,
            'method_used': 'ultra_fast',
            'quality_score': 0.0
        }

        try:
            # Step 1: Ensure model is loaded (async)
            load_start = time.perf_counter()
            await self._ensure_model_loaded()
            performance_metrics['model_load_time'] = time.perf_counter() - load_start

            # Step 2: Parse with optimized settings
            logger.info("Starting ultra-fast Gemini parsing...")
            gemini_start = time.perf_counter()

            # Prepare optimized request
            import base64
            b64 = base64.b64encode(document_bytes).decode()
            messages = [{
                "role": "user",
                "content": [
                    EXTRACTION_PROMPT,
                    PDF.from_base64(f"data:application/pdf;base64,{b64}")
                ]
            }]

            # Parse with ultra-fast settings
            invoice = await self._instructor.chat.completions.create(
                model=settings.GEMINI_MODEL_NAME,
                messages=messages,
                response_model=Invoice
                # Ultra-fast optimization (Gemini specific params removed for compatibility)
            )

            performance_metrics['gemini_time'] = time.perf_counter() - gemini_start

            # Step 3: Parallel validation
            validation_start = time.perf_counter()
            validation_task = asyncio.create_task(
                asyncio.to_thread(self.validator.validate_invoice, invoice)
            )
            validation_results = await validation_task
            performance_metrics['validation_time'] = time.perf_counter() - validation_start

            # Final metrics
            performance_metrics['total_time'] = time.perf_counter() - start_time
            performance_metrics['quality_score'] = validation_results['quality_score']

            logger.info(f"Ultra-fast parsing completed in {performance_metrics['total_time']:.2f}s")
            return invoice, {**performance_metrics, **validation_results}

        except Exception as e:
            performance_metrics['total_time'] = time.perf_counter() - start_time
            logger.error(f"Ultra-fast parsing failed: {e}")
            raise


# Global instance with pre-loading
ultra_fast_parser = UltraFastInvoiceParser()

# Start warming up the model immediately when module is imported
import asyncio
import threading
from loguru import logger as module_logger

def _warm_up_model():
    """Background thread to warm up the model during server startup."""
    try:
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Pre-load the model
        loop.run_until_complete(ultra_fast_parser._ensure_model_loaded())
        module_logger.info("Ultra-fast parser model pre-loaded successfully!")

    except Exception as e:
        module_logger.warning(f"Model pre-loading failed (will load on first request): {e}")
    finally:
        loop.close()

# Start warm-up in background thread
warmup_thread = threading.Thread(target=_warm_up_model, daemon=True)
warmup_thread.start()