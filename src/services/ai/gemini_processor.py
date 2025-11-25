"""Gemini AI processor for invoice structuring (Text-only mode)."""
from typing import Tuple, Dict, Any, Optional
from loguru import logger
import google.generativeai as genai
import json

from src.domain.models import Invoice
from src.services.ai.gemini.prompts_v3 import get_structuring_prompt
from src.services.ai.gemini.utils.json_cleaner import JSONCleaner
from src.services.ai.gemini.utils.json_repairer import JSONRepairer
from src.services.ai.gemini.utils.text_truncator import TextTruncator
from src.config.settings import app_settings


class GeminiInvoiceProcessor:
    """Processes invoices using Google Gemini Flash-Lite in text mode."""

    def __init__(self):
        """Initialize the Gemini processor in JSON mode."""
        genai.configure(api_key=app_settings.ai_model.GEMINI_API_KEY)

        self._client = genai.GenerativeModel(
            model_name=app_settings.ai_model.GEMINI_MODEL_NAME,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        )
        logger.info("Gemini processor initialized in TEXT mode with semantic ontology")

    async def structure_invoice_data_from_text(self, ocr_text: str) -> Tuple[Optional[Invoice], Dict[str, Any]]:
        """
        Structures invoice data from OCR text.

        Args:
            ocr_text: Extracted OCR text

        Returns:
            Tuple of (Invoice object, metadata dict)
        """
        logger.info("Structuring invoice data from OCR text with Gemini JSON mode + semantic guidance.")

        try:
            ocr_text = TextTruncator.truncate(ocr_text)
            schema = json.dumps(Invoice.model_json_schema(), indent=2)
            full_prompt = get_structuring_prompt(schema) + ocr_text

            response = await self._client.generate_content_async(
                full_prompt,
                request_options={"timeout": 120}
            )

            # DEBUG: Log Gemini response
            logger.info(f"Gemini raw response ({len(response.text)} chars): {response.text[:1000]}...")

            json_text = self._extract_json(response.text)
            invoice_dict = self._parse_json_with_repair(json_text)
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
        except ValueError as e:
            error_msg = str(e)
            logger.error(f"Pydantic validation failed: {error_msg}")
            logger.error(f"Raw JSON that failed validation: {json_text if 'json_text' in locals() else 'N/A'}")
            return None, {
                "success": False,
                "error": "Validation error",
                "error_detail": error_msg,
                "error_type": "pydantic_validation"
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Gemini structuring failed: {error_msg}")
            return None, {"success": False, "error": error_msg}

    def _extract_json(self, raw_text: str) -> str:
        """Extract clean JSON from Gemini response."""
        json_text = JSONCleaner.strip_markdown(raw_text)
        json_text = JSONCleaner.clean_comments(json_text)
        return json_text

    def _parse_json_with_repair(self, json_text: str) -> dict:
        """Parse JSON, repairing if needed."""
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            repaired = JSONRepairer.repair(json_text, e)
            return json.loads(repaired)
