# Copyright 2024 Artificial Intelligence Labs, SL

import base64
import instructor

from google import genai
from loguru import logger
from instructor.multimodal import PDF

from app.services.parser.models import Invoice
from app.services.prompts import EXTRACTION_PROMPT
from app.settings import settings


class InvoiceParser:
    def __init__(self):
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._instructor = instructor.from_genai(
            self._client,
            mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS,
            use_async=True
        )

    async def parse_bytes(self, document_bytes: bytes) -> Invoice:
        """
        Parse a PDF invoice straight from bytes.
        """

        logger.info("Parsing invoice...")
        b64 = base64.b64encode(document_bytes).decode()
        messages = [{
            "role": "user",
            "content": [
                EXTRACTION_PROMPT,
                PDF.from_base64(f"data:application/pdf;base64,{b64}")
            ]
        }]

        invoice = await self._instructor.chat.completions.create(
            model=settings.GEMINI_MODEL_NAME,
            messages=messages,  # type: ignore
            response_model=Invoice,
        )

        logger.info("Invoice parsed successfully")
        return invoice


invoice_parser = InvoiceParser()