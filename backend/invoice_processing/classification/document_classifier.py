"""
Document classifier
One responsibility: classify if document is an invoice or not
"""

import base64
from typing import Optional
from pydantic import BaseModel

try:
    import google.generativeai as genai
except ImportError:
    logger.warning("google-generativeai not installed")
    genai = None

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
        self._model = None
        self._configured = False

    def _configure(self) -> bool:
        """Configure Gemini client."""
        if self._configured:
            return True

        try:
            if not genai:
                logger.error("google-generativeai not installed")
                return False

            genai.configure(api_key=app_settings.ai_model.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(app_settings.ai_model.GEMINI_MODEL_NAME)
            self._configured = True
            return True

        except Exception as e:
            logger.error(f"Failed to configure Gemini for classification: {e}")
            return False

    async def classify_bytes(self, document_bytes: bytes) -> DocumentClassification:
        """
        Classify document bytes to determine if it's an invoice.
        """
        logger.info("Classifying document type")

        try:
            if not self._configure():
                return DocumentClassification(
                    is_invoice=True,  # Default to True if can't classify
                    confidence=0.5,
                    document_type="unknown",
                    reason="Classification failed - assuming invoice"
                )

            pdf_data = {
                "inline_data": {
                    "mime_type": "application/pdf",
                    "data": base64.b64encode(document_bytes).decode()
                }
            }

            prompt = """Analyze this document. Is it an invoice? Answer with:
            - is_invoice: true/false
            - confidence: 0.0-1.0
            - document_type: "invoice" or "receipt" or "other"
            - reason: brief explanation

            An invoice must clearly state vendor/customer, list items/services with prices,
            and show a total amount due. Format as JSON."""

            response = await self._model.generate_content_async([prompt, pdf_data])

            if response and response.text:
                # Simple parsing - for production would use more robust parsing
                text = response.text.lower()
                is_invoice = "true" in text or "invoice" in text
                confidence = 0.8 if is_invoice else 0.9

                return DocumentClassification(
                    is_invoice=is_invoice,
                    confidence=confidence,
                    document_type="invoice" if is_invoice else "other",
                    reason=response.text[:100]  # First 100 chars
                )

            # Fallback if no response
            return DocumentClassification(
                is_invoice=True,  # Default assume invoice
                confidence=0.5,
                document_type="unknown",
                reason="No response from classification model"
            )

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # SAFE FALLBACK: If classification fails, assume it's NOT a valid invoice.
            return DocumentClassification(
                is_invoice=False,
                confidence=0.0,
                document_type="classification_failed",
                reason=f"An error occurred during classification: {str(e)}"
            )


# Global classifier instance
document_classifier = DocumentClassifier()