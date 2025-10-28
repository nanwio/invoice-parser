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
            # CRITICAL: Truncate extremely long OCR text to prevent Gemini timeout
            # Gemini Flash can handle ~1M tokens input, but very long docs (>150k chars) cause timeouts/quality issues
            MAX_OCR_LENGTH = 150000  # Conservative limit: ~30k tokens
            original_length = len(ocr_text)

            if original_length > MAX_OCR_LENGTH:
                logger.warning(f"OCR text is very long ({original_length} chars). Truncating to {MAX_OCR_LENGTH} chars to prevent timeout.")
                # Truncate but keep beginning (has summary) and end (has totals)
                # Keep first 100k + last 50k chars
                ocr_text = ocr_text[:100000] + "\n\n[... MIDDLE CONTENT TRUNCATED ...]\n\n" + ocr_text[-50000:]
                logger.info(f"Truncated OCR text from {original_length} to {len(ocr_text)} chars")

            # Generate dynamic schema from Pydantic model
            schema = Invoice.model_json_schema()
            schema_str = json.dumps(schema, indent=2)

            # Use the comprehensive prompt with schema, semantic ontology, and few-shot example
            full_prompt = get_structuring_prompt(schema_str) + ocr_text

            # Call Gemini with JSON mode
            # IMPORTANT: Timeout set to 120s (default 60s was too short for large invoices)
            response = await self._client.generate_content_async(
                full_prompt,
                request_options={"timeout": 120}
            )

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

            # CRITICAL: Validate JSON before parsing (detect truncation/corruption)
            # For very long invoices, Gemini may generate incomplete JSON
            try:
                invoice_dict = json.loads(json_text)
            except json.JSONDecodeError as e:
                # Try to fix common JSON corruption issues
                logger.warning(f"JSON parsing failed at position {e.pos}: {e.msg}")
                logger.warning(f"Attempting to repair JSON (likely truncated response from Gemini)")

                # Find the last valid closing brace
                # Strategy: Remove incomplete trailing content and close the JSON properly
                truncate_pos = e.pos
                json_text_truncated = json_text[:truncate_pos].rstrip()

                # Try to close the JSON by adding missing closing braces
                # Count unclosed braces
                open_braces = json_text_truncated.count('{') - json_text_truncated.count('}')
                open_brackets = json_text_truncated.count('[') - json_text_truncated.count(']')

                # Remove trailing comma if present
                if json_text_truncated.endswith(','):
                    json_text_truncated = json_text_truncated[:-1]

                # Add missing closing brackets and braces
                json_text_repaired = json_text_truncated + (']' * open_brackets) + ('}' * open_braces)

                logger.info(f"Repaired JSON: added {open_brackets} closing brackets and {open_braces} closing braces")

                try:
                    invoice_dict = json.loads(json_text_repaired)
                    logger.warning(f"✓ JSON repair successful! Parsed truncated invoice with potentially incomplete items list.")
                except json.JSONDecodeError as e2:
                    # Repair failed, raise original error
                    logger.error(f"JSON repair failed: {e2}")
                    raise e  # Raise original error

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

