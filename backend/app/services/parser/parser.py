# Copyright 2024 Artificial Intelligence Labs, SL

import base64
import instructor

from google import genai
from loguru import logger
from instructor.multimodal import PDF, Image
from typing import Dict, Any, Tuple

from app.services.parser.models import Invoice
from app.services.prompts import EXTRACTION_PROMPT
from app.services.preprocessing import ImageProcessor
from app.settings import settings


class EnhancedInvoiceParser:
    """
    Professional-grade invoice parser with advanced preprocessing and validation.
    """

    def __init__(self):
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._instructor = instructor.from_genai(
            self._client,
            mode=instructor.Mode.GENAI_TOOLS,  # FASTER than STRUCTURED_OUTPUTS
            use_async=True
        )
        self.image_processor = ImageProcessor()
        from app.services.validation import get_invoice_validator
        self.validator = get_invoice_validator()()

    async def parse_bytes(self, document_bytes: bytes, use_preprocessing: bool = True) -> Tuple[Invoice, Dict[str, Any]]:
        """
        Parse a PDF invoice with professional-grade preprocessing and validation.

        Args:
            document_bytes: Raw PDF bytes
            use_preprocessing: Whether to apply image preprocessing (default: True)

        Returns:
            Tuple of (parsed_invoice, validation_results)
        """
        logger.info("Starting enhanced invoice parsing...")

        try:
            # Step 1: Advanced preprocessing (if enabled)
            if use_preprocessing:
                logger.info("Applying professional image preprocessing...")
                processed_content = self.image_processor.preprocess_pdf_bytes(document_bytes)

                # Use preprocessed image
                if processed_content.startswith("data:image/"):
                    messages = [{
                        "role": "user",
                        "content": [
                            EXTRACTION_PROMPT,
                            Image.from_url(processed_content)
                        ]
                    }]
                else:
                    # Fallback to original PDF
                    messages = [{
                        "role": "user",
                        "content": [
                            EXTRACTION_PROMPT,
                            PDF.from_base64(processed_content.split(',')[1])
                        ]
                    }]
            else:
                # Use original PDF without preprocessing
                b64 = base64.b64encode(document_bytes).decode()
                messages = [{
                    "role": "user",
                    "content": [
                        EXTRACTION_PROMPT,
                        PDF.from_base64(f"data:application/pdf;base64,{b64}")
                    ]
                }]

            # Step 2: AI-powered extraction
            logger.info("Extracting structured data with Gemini...")
            invoice = await self._instructor.chat.completions.create(
                model=settings.GEMINI_MODEL_NAME,
                messages=messages,  # type: ignore
                response_model=Invoice,
                max_retries=2,  # Professional retry logic
            )

            # Step 3: Professional validation and quality assessment
            logger.info("Validating extracted data...")
            validation_results = self.validator.validate_invoice(invoice)

            # Log quality metrics
            quality_score = validation_results['quality_score']
            logger.info(f"Invoice parsing completed - Quality score: {quality_score:.1f}/100")

            if validation_results['errors']:
                logger.warning(f"Validation errors found: {len(validation_results['errors'])}")
                for error in validation_results['errors']:
                    logger.warning(f"  - {error['field']}: {error['message']}")

            return invoice, validation_results

        except Exception as e:
            logger.error(f"Enhanced invoice parsing failed: {e}")
            # Try fallback parsing without preprocessing
            if use_preprocessing:
                logger.info("Attempting fallback parsing without preprocessing...")
                return await self.parse_bytes(document_bytes, use_preprocessing=False)
            else:
                raise e

    async def parse_bytes_simple(self, document_bytes: bytes) -> Invoice:
        """
        Simple parsing method for backward compatibility.
        Returns only the invoice without validation results.
        """
        invoice, _ = await self.parse_bytes(document_bytes)
        return invoice


# Maintain backward compatibility
class InvoiceParser(EnhancedInvoiceParser):
    """Backward compatible invoice parser."""

    async def parse_bytes(self, document_bytes: bytes) -> Invoice:
        # Call the parent class method directly with preprocessing disabled for speed
        invoice, _ = await super().parse_bytes(document_bytes, use_preprocessing=False)
        return invoice


# Global instances
invoice_parser = InvoiceParser()
enhanced_invoice_parser = EnhancedInvoiceParser()