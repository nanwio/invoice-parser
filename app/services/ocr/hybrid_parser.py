# Copyright 2024 Artificial Intelligence Labs, SL

import time
from typing import Dict, Any, Tuple, Optional
from loguru import logger

from app.services.parser.models import Invoice
from app.services.parser.parser import enhanced_invoice_parser
from app.services.validation import InvoiceValidator
from .donut_engine import donut_engine


class HybridInvoiceParser:
    """
    Ultra-fast hybrid parser combining DONUT OCR with Gemini fallback.

    Strategy:
    1. Try DONUT first (2-3s) - optimized for invoices
    2. Fallback to Gemini (1-2s) if DONUT fails
    3. Always validate results

    Target: <5 seconds total processing time
    """

    def __init__(self):
        self.validator = InvoiceValidator()
        self.donut_timeout = 10.0  # Max time for DONUT processing
        self.confidence_threshold = 0.7  # Minimum confidence for DONUT results

    async def parse_bytes_fast(self, document_bytes: bytes) -> Tuple[Invoice, Dict[str, Any]]:
        """
        Ultra-fast hybrid parsing with performance monitoring.

        Returns:
            Tuple of (parsed_invoice, performance_metrics)
        """
        start_time = time.perf_counter()
        performance_metrics = {
            'total_time': 0.0,
            'donut_time': 0.0,
            'gemini_time': 0.0,
            'validation_time': 0.0,
            'method_used': 'unknown',
            'donut_success': False,
            'gemini_fallback': False,
            'quality_score': 0.0
        }

        try:
            # Step 1: Try DONUT OCR first
            logger.info("Starting DONUT OCR processing...")
            donut_start = time.perf_counter()

            donut_result = None
            try:
                donut_raw = donut_engine.extract_from_pdf_bytes(document_bytes)
                if donut_raw:
                    donut_result = donut_engine.convert_donut_to_invoice(donut_raw)
                    performance_metrics['donut_success'] = True
                    logger.info("DONUT extraction successful")
            except Exception as e:
                logger.warning(f"DONUT processing failed: {e}")

            performance_metrics['donut_time'] = time.perf_counter() - donut_start

            # Step 2: Validate DONUT result
            if donut_result:
                validation_start = time.perf_counter()
                validation_results = self.validator.validate_invoice(donut_result)
                performance_metrics['validation_time'] = time.perf_counter() - validation_start

                # Check if DONUT result is good enough
                quality_score = validation_results['quality_score']
                performance_metrics['quality_score'] = quality_score

                if quality_score >= (self.confidence_threshold * 100) and validation_results['is_valid']:
                    performance_metrics['method_used'] = 'donut'
                    performance_metrics['total_time'] = time.perf_counter() - start_time

                    logger.info(f"DONUT result accepted - Quality: {quality_score:.1f}/100")
                    return donut_result, {**performance_metrics, **validation_results}

            # Step 3: Fallback to Gemini if DONUT fails or quality is low
            logger.info("Falling back to Gemini processing...")
            performance_metrics['gemini_fallback'] = True

            gemini_start = time.perf_counter()
            gemini_result, gemini_validation = await enhanced_invoice_parser.parse_bytes(
                document_bytes,
                use_preprocessing=False  # Skip preprocessing for speed
            )
            performance_metrics['gemini_time'] = time.perf_counter() - gemini_start
            performance_metrics['method_used'] = 'gemini_fallback'
            performance_metrics['quality_score'] = gemini_validation['quality_score']

            # Combine validation results
            validation_results = gemini_validation
            performance_metrics['validation_time'] += gemini_validation.get('validation_time', 0)

            performance_metrics['total_time'] = time.perf_counter() - start_time

            logger.info(f"Gemini fallback completed - Quality: {gemini_validation['quality_score']:.1f}/100")
            return gemini_result, {**performance_metrics, **validation_results}

        except Exception as e:
            performance_metrics['total_time'] = time.perf_counter() - start_time
            logger.error(f"Hybrid parsing completely failed: {e}")
            raise

    async def parse_bytes_donut_only(self, document_bytes: bytes) -> Optional[Tuple[Invoice, Dict[str, Any]]]:
        """
        DONUT-only parsing for performance testing.
        """
        start_time = time.perf_counter()

        try:
            donut_raw = donut_engine.extract_from_pdf_bytes(document_bytes)
            if not donut_raw:
                return None

            donut_result = donut_engine.convert_donut_to_invoice(donut_raw)
            if not donut_result:
                return None

            validation_results = self.validator.validate_invoice(donut_result)

            performance_metrics = {
                'total_time': time.perf_counter() - start_time,
                'method_used': 'donut_only',
                'quality_score': validation_results['quality_score']
            }

            return donut_result, {**performance_metrics, **validation_results}

        except Exception as e:
            logger.error(f"DONUT-only parsing failed: {e}")
            return None

    def get_performance_stats(self, metrics: Dict[str, Any]) -> str:
        """
        Generate human-readable performance summary.
        """
        total_time = metrics.get('total_time', 0)
        method = metrics.get('method_used', 'unknown')
        quality = metrics.get('quality_score', 0)

        summary = f"Processed in {total_time:.2f}s using {method} (Quality: {quality:.1f}/100)"

        if metrics.get('donut_success'):
            donut_time = metrics.get('donut_time', 0)
            summary += f" | DONUT: {donut_time:.2f}s"

        if metrics.get('gemini_fallback'):
            gemini_time = metrics.get('gemini_time', 0)
            summary += f" | Gemini fallback: {gemini_time:.2f}s"

        return summary


# Global instance
hybrid_parser = HybridInvoiceParser()