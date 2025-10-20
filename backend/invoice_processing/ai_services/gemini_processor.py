"""
Gemini AI processor with multimodal vision support
"""

from typing import Tuple, Dict, Any, Optional, List
from loguru import logger
import google.generativeai as genai
import json
from PIL import Image

from invoice_processing.models.invoice_data import Invoice
from invoice_processing.ai_services.gemini.prompts import get_structuring_prompt
from configuration.app_settings import app_settings

class GeminiInvoiceProcessor:
    """
    Processes invoices using Google Gemini Flash-Lite in multimodal vision mode.

    This processor can work in two modes:
    1. Vision mode (preferred): Processes PDF pages as images for better accuracy
    2. Text mode (fallback): Processes OCR text when vision is not available
    """

    def __init__(self, vision_mode: bool = True):
        """
        Initialize the Gemini processor in JSON mode with semantic guidance.

        Args:
            vision_mode: If True, use multimodal vision. If False, use text-only mode.
        """
        genai.configure(api_key=app_settings.ai_model.GEMINI_API_KEY)
        self.vision_mode = vision_mode

        self._client = genai.GenerativeModel(
            model_name=app_settings.ai_model.GEMINI_MODEL_NAME,
            generation_config={
                "response_mime_type": "application/json",
                "temperature": 0.1,
            }
        )
        logger.info(f"Gemini processor initialized in {'VISION' if vision_mode else 'TEXT'} mode with semantic ontology")

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

    async def structure_invoice_data_from_images(self, images: List[Image.Image]) -> Tuple[Optional[Invoice], Dict[str, Any]]:
        """
        Structures invoice data from PDF page images using Gemini Vision (multimodal).

        This is the PREFERRED method for complex invoices because:
        - Gemini can SEE visual structure (boxes, tables, highlighted sections)
        - Better at identifying summary sections vs breakdowns
        - Understands spatial layout and document hierarchy
        - More accurate for multi-page consolidated invoices
        - Enhanced with semantic ontology and few-shot learning

        Args:
            images: List of PIL Images (PDF pages converted to images)

        Returns:
            Tuple of (Invoice object or None, metadata dict)
        """
        logger.info(f"Structuring invoice data from {len(images)} images with Gemini Vision + semantic guidance.")

        try:
            # Generate dynamic schema from Pydantic model
            schema = Invoice.model_json_schema()
            schema_str = json.dumps(schema, indent=2)

            # Use the comprehensive prompt with schema, semantic ontology, and few-shot example
            prompt = get_structuring_prompt(schema_str)

            # Prepare content for multimodal request: [prompt, image1, image2, ...]
            content = [prompt]
            content.extend(images)

            logger.info(f"Sending {len(images)} images to Gemini Flash-Lite Vision with semantic ontology...")

            # Call Gemini with multimodal content (text + images)
            response = await self._client.generate_content_async(content)

            # Parse the JSON response
            json_text = response.text.strip()
            invoice_dict = json.loads(json_text)

            # Validate and create Pydantic object
            invoice = Invoice.model_validate(invoice_dict)

            metadata = {
                "success": True,
                "model": app_settings.ai_model.GEMINI_MODEL_NAME,
                "mode": "vision_multimodal",
                "num_pages": len(images),
                "raw_json_length": len(json_text),
            }
            logger.info(f"✅ Successfully extracted invoice using vision mode")
            return invoice, metadata

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            logger.error(f"Raw response: {response.text if 'response' in locals() else 'N/A'}")
            return None, {"success": False, "error": f"JSON parse error: {str(e)}", "mode": "vision"}
        except ValueError as e:
            # Pydantic validation errors are ValueError subclass
            logger.error(f"Pydantic validation failed: {e}")
            logger.error(f"Raw JSON that failed validation: {json_text if 'json_text' in locals() else 'N/A'}")
            return None, {
                "success": False,
                "error": "Validation error",
                "error_detail": str(e),
                "error_type": "pydantic_validation",
                "mode": "vision"
            }
        except Exception as e:
            logger.error(f"Gemini vision structuring failed: {e}")
            return None, {"success": False, "error": str(e), "mode": "vision"}