"""
Gemini AI processor
"""

import instructor
from typing import Tuple, Dict, Any, Optional
from loguru import logger
import google.generativeai as genai

from invoice_processing.models.invoice_data import Invoice
from configuration.app_settings import app_settings

instructor.patch()

class GeminiInvoiceProcessor:
    """
    Processes invoices using Google Gemini, guided by Pydantic models with Instructor.
    """

    def __init__(self):
        """Initialize the Gemini processor and the instructor client."""
        self._client = genai.GenerativeModel(
            model_name=app_settings.ai_model.GEMINI_MODEL_NAME
        )
        genai.configure(api_key=app_settings.ai_model.GEMINI_API_KEY)

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
        """
        logger.info("Structuring invoice data from OCR text with Gemini and Instructor.")
        
        try:
            full_prompt = self._get_structuring_prompt() + ocr_text
            
            # Use instructor to get a Pydantic object directly
            invoice_response = await self._client.generate_content_async(
                full_prompt,
                response_model=Invoice,
                request_options={"max_retries": 2}
            )
            
            metadata = {
                "success": True,
                "model": app_settings.ai_model.GEMINI_MODEL_NAME,
            }
            return invoice_response, metadata

        except Exception as e:
            logger.error(f"Gemini structuring with Instructor failed: {e}")
            return None, {"success": False, "error": str(e)}

    def _get_structuring_prompt(self) -> str:
        """
        Get the detailed, structured prompt that guides the LLM to output
        data matching the `Invoice` Pydantic model.
        """
        return """
        [SYSTEM]
        You are a world-class AI engine for invoice processing. Your task is to convert raw OCR text from any invoice into a structured JSON object that strictly adheres to the provided Pydantic model schema.

        [TASK]
        1.  **Analyze**: Carefully read the OCR text, which may be spread across multiple pages indicated by "[INICIO PÁGINA X]" markers.
        2.  **Extract**: Identify and extract all fields defined in the [FIELD DEFINITIONS] section.
        3.  **Structure**: Format the data into a valid JSON object matching the `Invoice` model. Pay close attention to nested structures like `vendor`, `customer`, `financials`, and `items`.

        [RULES]
        - **Strict Adherence**: Only extract information present in the text. DO NOT invent or infer data.
        - **Handle Missing Data**: If a field is not found, its value MUST be `null`. Do not omit keys.
        - **Data Types**: All monetary values must be numbers (float or int). Quantities should be integers. Dates must be in YYYY-MM-DD format if possible.
        - **Completeness**: Extract all line items.

        [FIELD DEFINITIONS]
        - `vendor`: The company issuing the invoice. Includes `name`, `tax_id`, `email`, `address`.
        - `customer`: The company receiving the invoice. Includes `name`, `tax_id`, `email`, `address`.
        - `financials`: A nested object containing all monetary details.
            - `currency`: The currency of the invoice (e.g., "EUR", "USD").
            - `subtotal`: The total amount before taxes.
            - `tax`: A nested object for tax details.
                - `type`: The type of tax (e.g., "IVA", "IGIC").
                - `rate`: The tax rate as a percentage (e.g., 21.0 for 21%).
                - `amount`: The total tax amount.
            - `total_amount`: The final, total amount to be paid.
        - `items`: A list of all line items. Each item is an object with `description`, `quantity`, `unit_price`, and `line_total`.
        - `metadata`: A nested object for invoice metadata.
            - `invoice_number`: The unique identifier for the invoice.
            - `issue_date`: The date the invoice was created.
            - `due_date`: The date payment is due.
        - `notes`: Any additional text or comments.

        [OCR TEXT TO PROCESS]
        """