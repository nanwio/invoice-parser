# Copyright 2024 Artificial Intelligence Labs, SL

import base64
from loguru import logger


class ImageProcessor:
    """
    Lightweight image processor for PDF preprocessing.
    Optimized for speed - minimal processing only.
    """

    def __init__(self):
        pass

    def preprocess_pdf_bytes(self, document_bytes: bytes) -> str:
        """
        Fast preprocessing - just convert to base64 for now.
        Advanced preprocessing can be added later if needed.

        Args:
            document_bytes: Raw PDF bytes

        Returns:
            Base64 encoded data URL
        """
        try:
            # For now, just return the PDF as base64 (no actual preprocessing)
            # This prevents crashes while maintaining speed
            b64 = base64.b64encode(document_bytes).decode()
            return f"data:application/pdf;base64,{b64}"

        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            # Fallback to original
            b64 = base64.b64encode(document_bytes).decode()
            return f"data:application/pdf;base64,{b64}"