"""
Gemini AI processor
"""

from typing import Tuple, Dict, Any, Optional
from loguru import logger
import google.generativeai as genai
import json

from invoice_processing.models.invoice_data import Invoice
from invoice_processing.ai_services.gemini.prompts import get_structuring_prompt
from configuration.app_settings import app_settings

class GeminiInvoiceProcessor:
    """
    Processes invoices using Google Gemini with JSON mode.
    """

    def __init__(self):
        """Initialize the Gemini processor."""
        genai.configure(api_key=app_settings.ai_model.GEMINI_API_KEY)
        self._client = genai.GenerativeModel(
            model_name=app_settings.ai_model.GEMINI_MODEL_NAME,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        )

    async def _warm_up_connection(self):
        """A simple check to ensure the API key is valid during startup."""
        try:
            # A lightweight call to verify credentials
            await genai.GenerativeModel.count_tokens_async(self._client, "warmup")
            logger.info("Gemini connection warmed up successfully.")
        except Exception as e:
            logger.error(f"Gemini warm-up failed. Check API key and configuration. Error: {e}")

    async def structure_invoice_data_from_text(self, ocr_text: str) -> Tuple[Optional[Invoice], Dict[str, Any]]:
        """
        Structures invoice data from OCR text, returning a Pydantic Invoice object.
        Uses centralized prompt from prompts.py with EN16931/UBL extensibility support.
        """
        logger.info("Structuring invoice data from OCR text with Gemini JSON mode.")

        try:
            # Generate dynamic schema from Pydantic model
            schema = Invoice.model_json_schema()
            schema_str = json.dumps(schema, indent=2)

            # Use the centralized, comprehensive prompt with dynamic schema
            full_prompt = get_structuring_prompt(schema_str) + ocr_text

            # Call Gemini with JSON mode
            response = await self._client.generate_content_async(full_prompt)

            # Parse the JSON response
            json_text = response.text.strip()
            invoice_dict = json.loads(json_text)

            # Validate and create Pydantic object
            invoice = Invoice.model_validate(invoice_dict)

            metadata = {
                "success": True,
                "model": app_settings.ai_model.GEMINI_MODEL_NAME,
                "raw_json_length": len(json_text),
            }
            return invoice, metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Raw response: {response.text if 'response' in locals() else 'N/A'}")
            return None, {"success": False, "error": f"JSON parse error: {str(e)}"}
        except Exception as e:
            logger.error(f"Gemini structuring failed: {e}")
            return None, {"success": False, "error": str(e)}