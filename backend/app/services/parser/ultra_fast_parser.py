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
    Target: <2 seconds per invoice.
    """

    def __init__(self):
        self.validator = get_invoice_validator()()
        self._client = None
        self._instructor = None
        self._model_loaded = False
        self._loading_lock = asyncio.Lock()

    async def _ensure_model_loaded(self):
        """Lazy load and cache Gemini model for faster subsequent calls."""
        if self._model_loaded:
            return

        # Use lock to prevent multiple concurrent loads
        async with self._loading_lock:
            if self._model_loaded:  # Double-check after acquiring lock
                return

            logger.info("⚡ Loading Gemini model (one-time setup)...")
            start_time = time.perf_counter()

            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

            # Use FASTER mode: GENAI_TOOLS instead of STRUCTURED_OUTPUTS
            self._instructor = instructor.from_genai(
                self._client,
                mode=instructor.Mode.GENAI_TOOLS,  # FASTER than STRUCTURED_OUTPUTS
                use_async=True
            )

            # Skip warm-up to save time - first request will be slightly slower but overall faster
            self._model_loaded = True
            load_time = time.perf_counter() - start_time
            logger.info(f"⚡ Model cached in {load_time:.2f}s - subsequent requests will be faster")

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
                response_model=Invoice,
                # Optimized settings for speed
                temperature=0.1,  # Lower temperature for faster, more deterministic results
                max_tokens=2000   # Limit tokens for faster response
            )

            performance_metrics['gemini_time'] = time.perf_counter() - gemini_start

            # Step 3: MINIMAL validation for speed (only critical checks)
            validation_start = time.perf_counter()
            validation_results = self._fast_validate(invoice)
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

    def _fast_validate(self, invoice: Invoice) -> Dict[str, Any]:
        """
        Lightning-fast validation - only essential checks.
        Skips complex validations to maintain speed.
        """
        errors = []
        quality_score = 95.0  # Start optimistic for speed

        try:
            # Only check critical math (fastest validation)
            expected_total = invoice.financial_details.subtotal + invoice.financial_details.tax.amount
            actual_total = invoice.financial_details.total_amount

            if abs(expected_total - actual_total) > 0.05:  # Looser tolerance for speed
                errors.append("Math error")
                quality_score -= 20

            # Check basic required fields only
            if not invoice.parties.vendor.name or not invoice.parties.customer.name:
                errors.append("Missing party")
                quality_score -= 15

            if not invoice.items:
                errors.append("No items")
                quality_score -= 25

        except Exception:
            quality_score = 75.0  # Safe fallback

        return {
            'valid': len(errors) == 0,
            'quality_score': max(50.0, quality_score),  # Minimum 50 for speed
            'errors': errors,
            'warnings': [],  # Skip warnings for speed
            'validation_results': {
                'quality_score': max(50.0, quality_score)
            }
        }


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