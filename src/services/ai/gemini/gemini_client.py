"""
Gemini Client - SIMPLE and FOCUSED
One responsibility: handle Gemini API communication
"""

import base64
from typing import Dict, Any, Optional
from loguru import logger

try:
    import google.generativeai as genai
except ImportError:
    logger.warning("google-generativeai not installed")
    genai = None


class GeminiClient:
    """
    Simple Gemini API client.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """Initialize Gemini client."""
        self.api_key = api_key
        self.model_name = model_name
        self._model = None
        self._configured = False

    def configure(self) -> bool:
        """
        Configure Gemini client.

        Returns:
            bool: True if configured successfully
        """
        if self._configured:
            return True

        try:
            if not genai:
                logger.error("google-generativeai not installed")
                return False

            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)
            self._configured = True

            logger.info(f"Gemini client configured with model: {self.model_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")
            return False

    async def extract_from_pdf(self, pdf_bytes: bytes, prompt: str) -> Optional[str]:
        """
        Extract text from PDF using Gemini.

        Args:
            pdf_bytes: PDF file content
            prompt: Extraction prompt

        Returns:
            Extracted text or None
        """
        if not self._configured:
            if not self.configure():
                return None

        try:
            # Prepare PDF data for Gemini API
            import base64

            # Use genai.upload_file for better reliability
            pdf_b64 = base64.b64encode(pdf_bytes).decode()

            # Create proper Gemini content format
            pdf_part = {
                "inline_data": {
                    "mime_type": "application/pdf",
                    "data": pdf_b64
                }
            }

            # Generate content with proper format
            response = await self._model.generate_content_async([prompt, pdf_part])

            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return None

        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return None

    async def extract_from_text(self, full_prompt: str) -> Optional[str]:
        """
        Extracts structured data from a full prompt (instructions + text) using Gemini.

        Args:
            full_prompt: The complete prompt including instructions and the text to process.

        Returns:
            Structured text or None.
        """
        if not self._configured:
            if not self.configure():
                return None

        try:
            response = await self._model.generate_content_async(full_prompt)

            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return None

        except Exception as e:
            logger.error(f"Gemini text extraction failed: {e}")
            return None

    def is_configured(self) -> bool:
        """Check if client is configured."""
        return self._configured