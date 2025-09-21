# Copyright 2024 Artificial Intelligence Labs, SL

import base64
import instructor

from google import genai
from instructor.multimodal import PDF

from app.services.prompts import CLASSIFICATION_PROMPT
from app.settings import settings

from .models import DocumentClassification


class DocumentClassifier:
    """
    Classify documents to filter out non-invoices.
    """
    
    def __init__(self):
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._instructor = instructor.from_genai(
            self._client,
            mode=instructor.Mode.GENAI_STRUCTURED_OUTPUTS,
            use_async=True
        )

    async def classify_bytes(self, document_bytes: bytes) -> DocumentClassification:

        b64 = base64.b64encode(document_bytes).decode()
        messages = [{
            "role": "user",
            "content": [
                CLASSIFICATION_PROMPT,
                PDF.from_base64(f"data:application/pdf;base64,{b64}")
            ]
        }]

        classification = await self._instructor.chat.completions.create(
            model=settings.GEMINI_MODEL_NAME,
            messages=messages, # noqa
            response_model=DocumentClassification,
        )

        return classification


document_classifier = DocumentClassifier()