"""
Gemini AI processor for invoice structuring (Text-only mode).
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
    Processes invoices using Google Gemini Flash-Lite in text mode.

    Workflow: PaddleOCR extracts text → Gemini structures into JSON
    """

    def __init__(self):
        """Initialize the Gemini processor in JSON mode with semantic guidance."""
        genai.configure(api_key=app_settings.ai_model.GEMINI_API_KEY)

        self._client = genai.GenerativeModel(
            model_name=app_settings.ai_model.GEMINI_MODEL_NAME,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        )
        logger.info("Gemini processor initialized in TEXT mode with semantic ontology")


    def _clean_json_comments(self, json_text: str) -> str:
        """
        Remove JSON comments that Gemini might add despite being told not to.

        Handles:
        - Inline comments: "key": value  # comment
        - Python-style comments at end of lines
        """
        import re

        # Remove inline comments (# anything) at end of lines
        # This regex preserves strings but removes # comments
        lines = []
        for line in json_text.split('\n'):
            # Don't remove # inside strings
            # Simple heuristic: if # appears after a comma or before a closing brace/bracket
            if '#' in line:
                # Find position of # that's not inside a string
                in_string = False
                quote_char = None
                clean_line = []

                for i, char in enumerate(line):
                    if char in ('"', "'") and (i == 0 or line[i-1] != '\\'):
                        if not in_string:
                            in_string = True
                            quote_char = char
                        elif char == quote_char:
                            in_string = False
                            quote_char = None

                    if char == '#' and not in_string:
                        # Found comment, truncate here
                        break
                    clean_line.append(char)

                lines.append(''.join(clean_line).rstrip())
            else:
                lines.append(line)

        return '\n'.join(lines)

    async def structure_invoice_data_from_text(self, ocr_text: str) -> Tuple[Optional[Invoice], Dict[str, Any]]:
        """
        Structures invoice data from OCR text, returning a Pydantic Invoice object.
        Uses comprehensive prompt with semantic ontology and few-shot learning.
        """
        logger.info("Structuring invoice data from OCR text with Gemini JSON mode + semantic guidance.")

        try:
            # Generate dynamic schema from Pydantic model
            schema = Invoice.model_json_schema()
            schema_str = json.dumps(schema, indent=2)

            # Use the comprehensive prompt with schema, semantic ontology, and few-shot example
            full_prompt = get_structuring_prompt(schema_str) + ocr_text

            # Call Gemini with JSON mode
            response = await self._client.generate_content_async(full_prompt)

            # Parse the JSON response and strip markdown code blocks
            json_text = response.text.strip()

            # Remove markdown code blocks if present
            if json_text.startswith('```'):
                # Remove opening ```json or ```
                lines = json_text.split('\n', 1)
                if len(lines) > 1:
                    json_text = lines[1]

            if json_text.endswith('```'):
                # Remove closing ```
                json_text = json_text.rsplit('\n```', 1)[0]

            json_text = json_text.strip()

            # CRITICAL: Remove any JSON comments that Gemini might have added
            json_text = self._clean_json_comments(json_text)

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
        except ValueError as e:
            # Pydantic validation errors are ValueError subclass
            logger.error(f"Pydantic validation failed: {e}")
            logger.error(f"Raw JSON that failed validation: {json_text if 'json_text' in locals() else 'N/A'}")
            return None, {
                "success": False,
                "error": "Validation error",
                "error_detail": str(e),
                "error_type": "pydantic_validation"
            }
        except Exception as e:
            logger.error(f"Gemini structuring failed: {e}")
            return None, {"success": False, "error": str(e)}

