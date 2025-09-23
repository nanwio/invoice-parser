# Copyright 2024 Artificial Intelligence Labs, SL

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
    Under 100 lines, single responsibility.
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
            # Prepare PDF data
            pdf_data = {
                "mime_type": "application/pdf",
                "data": pdf_bytes
            }

            # Generate content
            response = await self._model.generate_content_async([prompt, pdf_data])

            if response and response.text:
                return response.text.strip()
            else:
                logger.warning("Empty response from Gemini")
                return None

        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return None

    async def extract_from_text(self, text: str, prompt: str) -> Optional[str]:
        """
        Extracts structured data from text using Gemini.

        Args:
            text: The input text to process.
            prompt: The prompt to guide the extraction.

        Returns:
            Structured text or None.
        """
        if not self._configured:
            if not self.configure():
                return None

        try:
            response = await self._model.generate_content_async([prompt, text])

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