# Copyright 2024 Artificial Intelligence Labs, SL

"""
Document classifier - SIMPLE and FOCUSED
One responsibility: classify if document is an invoice or not
"""

import base64
import instructor
from typing import Optional
from pydantic import BaseModel

from google import genai
from instructor.multimodal import PDF
from loguru import logger

from configuration.app_settings import app_settings


class DocumentClassification(BaseModel):
    """Result of document classification."""
    is_invoice: bool
    confidence: float
    document_type: str
    reason: str


class DocumentClassifier:
    """
    Classify documents to filter out non-invoices.
    Simple, fast classification using Gemini.
    """

    def __init__(self):
        """Initialize classifier with Gemini."""
        self._client = genai.Client(api_key=app_settings.ai_model.GEMINI_API_KEY)
        self._instructor = instructor.from_genai(
            self._client,
            mode=instructor.Mode.GENAI_TOOLS,  # Fastest mode
            use_async=True
        )

    async def classify_bytes(self, document_bytes: bytes) -> DocumentClassification:
        """
        Classify document bytes to determine if it's an invoice.

        Args:
            document_bytes: Raw PDF bytes

        Returns:
            Classification result with confidence
        """
        logger.info("Classifying document type")

        try:
            b64 = base64.b64encode(document_bytes).decode()

            # Simple classification prompt
            prompt = """Analyze this document and determine if it's an invoice.

An invoice typically includes:
- Vendor/seller information
- Customer/buyer information
- Line items with descriptions and amounts
- Total amount due
- Invoice number or reference
- Date

Return:
- is_invoice: true if it's an invoice, false otherwise
- confidence: your confidence level (0-1)
- document_type: specific type (sales_invoice, receipt, contract, etc.)
- reason: brief explanation"""

            messages = [{
                "role": "user",
                "content": [
                    prompt,
                    {"type": "application/pdf", "data": b64}
                ]
            }]

            classification = await self._instructor.chat.completions.create(
                model=app_settings.ai_model.GEMINI_MODEL_NAME,
                messages=messages,
                response_model=DocumentClassification,
                temperature=0.1  # Low temperature for consistent classification
            )

            logger.info(f"Document classified as: {classification.document_type} (confidence: {classification.confidence:.2f})")
            return classification

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # Safe fallback - assume it's an invoice to avoid blocking valid documents
            return DocumentClassification(
                is_invoice=True,
                confidence=0.5,
                document_type="unknown",
                reason=f"Classification failed: {str(e)}"
            )


# Global classifier instance
document_classifier = DocumentClassifier()