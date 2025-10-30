"""Text truncation utilities for Gemini input."""
from loguru import logger


class TextTruncator:
    """Truncates excessively long text for Gemini processing."""

    MAX_LENGTH = 150000  # Conservative limit: ~30k tokens

    @staticmethod
    def truncate(ocr_text: str) -> str:
        """
        Truncate excessively long OCR text to prevent Gemini timeout.

        Args:
            ocr_text: Raw OCR text

        Returns:
            Truncated text if needed
        """
        original_length = len(ocr_text)

        if original_length <= TextTruncator.MAX_LENGTH:
            return ocr_text

        logger.warning(
            f"OCR text is very long ({original_length} chars). "
            f"Truncating to {TextTruncator.MAX_LENGTH} chars to prevent timeout."
        )

        # Keep first 100k + last 50k chars (preserves summary and totals)
        truncated = ocr_text[:100000] + "\\n\\n[... MIDDLE CONTENT TRUNCATED ...]\\n\\n" + ocr_text[-50000:]

        logger.info(f"Truncated OCR text from {original_length} to {len(truncated)} chars")

        return truncated
