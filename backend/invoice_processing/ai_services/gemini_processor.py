"""
Gemini AI processor
"""

from typing import Tuple, Dict, Any, Optional
from loguru import logger
import google.generativeai as genai
import json

from invoice_processing.models.invoice_data import Invoice
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
        """
        logger.info("Structuring invoice data from OCR text with Gemini JSON mode.")

        try:
            # Get the schema from the Pydantic model
            schema = Invoice.model_json_schema()
            full_prompt = self._get_structuring_prompt(schema) + ocr_text

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

    def _get_structuring_prompt(self, schema: dict) -> str:
        """
        Get the detailed, structured prompt that guides the LLM to output
        data matching the `Invoice` Pydantic model.
        """
        schema_str = json.dumps(schema, indent=2)
        return f"""[SYSTEM]
You are a world-class AI engine for invoice processing with expertise in international accounting standards.
Your task is to convert raw OCR text from invoices (from any country) into structured JSON that strictly adheres to the provided schema.

[TASK]
1. **Analyze**: Carefully read the OCR text, which may span multiple pages (marked with "[INICIO PÁGINA X]").
2. **Extract**: Identify ALL financial components including base amounts, taxes, withholdings, discounts, and surcharges.
3. **Structure**: Format data into valid JSON matching the schema exactly.

[CRITICAL FINANCIAL EXTRACTION RULES]

**Financial Details Breakdown:**
- **subtotal**: Base amount BEFORE any adjustments (taxes, discounts, withholdings)
- **discount**: Any discounts applied (look for "Descuento", "Discount", "Rebate")
- **tax**: PRIMARY tax (IVA, IGIC, VAT, GST, Sales Tax)
  - Extract type, rate (%), and amount
- **additional_taxes**: Any SECONDARY taxes (use array if multiple taxes exist)
- **withholding**: TAX RETENTIONS/WITHHOLDINGS (critical for Spanish IRPF, Income Tax, WHT)
  - Look for: "RETENCIÓN", "IRPF", "Withholding", "Retention", "Retenção"
  - These are ALWAYS NEGATIVE amounts that reduce the total
  - Extract type, rate (%), and amount (as positive number - will be subtracted in calculation)
- **surcharges**: Additional fees, shipping, handling charges
- **total_amount**: FINAL amount to pay after ALL adjustments

**Calculation Formula for Verification:**
total = subtotal - discount + tax + additional_taxes - withholding + surcharges

**Common Patterns by Country:**
- Spain: IVA/IGIC (tax) + IRPF (withholding)
- Mexico: IVA (tax) + ISR (withholding)
- USA: Sales Tax (tax)
- UK: VAT (tax)
- Latin America: Look for "Retención" or "Retenção"

[GENERAL RULES]
- **Accuracy**: Only extract information explicitly present in the text
- **Missing Data**: Use null for optional fields not found, reasonable defaults for required fields
- **Data Types**: Numbers for monetary values, integers for quantities, YYYY-MM-DD for dates
- **Completeness**: Extract ALL line items, taxes, and adjustments
- **Output Format**: Return ONLY valid JSON. No markdown, no code blocks, no explanations

[JSON SCHEMA]
{schema_str}

[OCR TEXT TO PROCESS]
"""