# Copyright 2024 Artificial Intelligence Labs, SL

"""
DONUT Model Loader - SIMPLE and FOCUSED
One responsibility: load and manage DONUT model
"""

import asyncio
from typing import Optional, Dict, Any
from loguru import logger


class DonutModelManager:
    """
    Manages DONUT model loading and inference.
    Under 100 lines, single responsibility.
    """

    def __init__(self):
        """Initialize model manager."""
        self._model = None
        self._processor = None
        self._loaded = False

    async def load_model(self) -> bool:
        """
        Load DONUT model for invoice processing.

        Returns:
            bool: True if loaded successfully
        """
        if self._loaded:
            return True

        try:
            logger.info("Loading DONUT model...")

            # Import here to avoid startup overhead
            from transformers import DonutProcessor, VisionEncoderDecoderModel

            # Use pretrained DONUT model for document understanding
            model_name = "naver-clova-ix/donut-base-finetuned-cord-v2"

            self._processor = DonutProcessor.from_pretrained(model_name)
            self._model = VisionEncoderDecoderModel.from_pretrained(model_name)

            # Move to CPU (for now - can add GPU later)
            self._model.eval()

            self._loaded = True
            logger.info("DONUT model loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load DONUT model: {e}")
            return False

    async def extract_text(self, image) -> Optional[Dict[str, Any]]:
        """
        Extract text from image using DONUT.

        Args:
            image: PIL Image object

        Returns:
            Dict with extracted data or None
        """
        if not self._loaded:
            logger.error("Model not loaded")
            return None

        try:
            # Prepare input
            pixel_values = self._processor(image, return_tensors="pt").pixel_values

            # Generate output
            decoder_input_ids = self._processor.tokenizer(
                "<s_cord-v2>",
                add_special_tokens=False,
                return_tensors="pt"
            ).input_ids

            # Run inference
            outputs = self._model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=self._model.decoder.config.max_position_embeddings,
                pad_token_id=self._processor.tokenizer.pad_token_id,
                eos_token_id=self._processor.tokenizer.eos_token_id,
                use_cache=True,
                bad_words_ids=[[self._processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )

            # Decode sequence
            sequence = self._processor.batch_decode(outputs.sequences)[0]
            sequence = sequence.replace(self._processor.tokenizer.eos_token, "").replace(self._processor.tokenizer.pad_token, "")

            # Parse the sequence to extract structured data
            return self._parse_donut_output(sequence)

        except Exception as e:
            logger.error(f"DONUT extraction failed: {e}")
            return None

    def _parse_donut_output(self, sequence: str) -> Dict[str, Any]:
        """Parse DONUT model output to extract invoice fields."""
        from invoice_processing.ai_services.ocr_engines.donut_output_parser import donut_parser
        return donut_parser.parse_donut_output(sequence)


# Global instance
donut_model = DonutModelManager()