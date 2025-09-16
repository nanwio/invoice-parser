# Copyright 2024 Artificial Intelligence Labs, SL

import json
import torch
from PIL import Image
from io import BytesIO
from typing import Dict, Any, Optional
from loguru import logger
from transformers import DonutProcessor, VisionEncoderDecoderModel
from pdf2image import convert_from_bytes

from app.services.parser.models import Invoice


class DonutOCREngine:
    """
    DONUT OCR Engine for ultra-fast invoice processing.
    End-to-end vision transformer optimized for document understanding.
    """

    def __init__(self):
        self.model_name = "naver-clova-ix/donut-base-finetuned-cord-v2"
        self.processor = None
        self.model = None
        self.device = "cpu"  # CPU-only for cost efficiency
        self.is_loaded = False

    def load_model(self):
        """Lazy load DONUT model to optimize startup time."""
        if self.is_loaded:
            return

        try:
            logger.info("Loading DONUT OCR model...")

            # Load processor and model
            self.processor = DonutProcessor.from_pretrained(self.model_name)
            self.model = VisionEncoderDecoderModel.from_pretrained(self.model_name)

            # Move to CPU and optimize
            self.model.to(self.device)
            self.model.eval()

            # Optimize for inference
            if hasattr(torch, 'compile'):
                self.model = torch.compile(self.model, mode="reduce-overhead")

            self.is_loaded = True
            logger.info("DONUT model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load DONUT model: {e}")
            raise

    def extract_from_pdf_bytes(self, pdf_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Extract structured data from PDF using DONUT.

        Args:
            pdf_bytes: Raw PDF bytes

        Returns:
            Structured invoice data or None if extraction fails
        """
        try:
            if not self.is_loaded:
                self.load_model()

            # Convert PDF to image (first page only for speed)
            images = convert_from_bytes(
                pdf_bytes,
                dpi=150,  # Lower DPI for speed, DONUT works well with this
                first_page=1,
                last_page=1,
                fmt='RGB'
            )

            if not images:
                logger.warning("No images extracted from PDF")
                return None

            image = images[0]
            logger.info(f"Processing image: {image.size}")

            # Process with DONUT
            result = self._process_with_donut(image)

            return result

        except Exception as e:
            logger.error(f"DONUT extraction failed: {e}")
            return None

    def _process_with_donut(self, image: Image.Image) -> Optional[Dict[str, Any]]:
        """
        Process image with DONUT model.
        """
        try:
            # Prepare prompt for invoice parsing
            task_prompt = "<s_cord-v2>"
            decoder_input_ids = self.processor.tokenizer(
                task_prompt,
                add_special_tokens=False,
                return_tensors="pt"
            ).input_ids

            # Process image
            pixel_values = self.processor(
                image,
                return_tensors="pt"
            ).pixel_values

            # Generate with optimized settings for speed
            with torch.no_grad():
                outputs = self.model.generate(
                    pixel_values.to(self.device),
                    decoder_input_ids=decoder_input_ids.to(self.device),
                    max_length=self.model.decoder.config.max_position_embeddings,
                    pad_token_id=self.processor.tokenizer.pad_token_id,
                    eos_token_id=self.processor.tokenizer.eos_token_id,
                    use_cache=True,
                    bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
                    return_dict_in_generate=True,
                    do_sample=False,  # Greedy decoding for speed
                    num_beams=1,      # Single beam for speed
                )

            # Decode output
            sequence = self.processor.batch_decode(outputs.sequences)[0]
            sequence = sequence.replace(self.processor.tokenizer.eos_token, "").replace(self.processor.tokenizer.pad_token, "")
            sequence = sequence.replace(task_prompt, "")

            # Parse JSON result
            try:
                result = json.loads(sequence)
                logger.info("DONUT extraction successful")
                return result
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse DONUT JSON output: {e}")
                return None

        except Exception as e:
            logger.error(f"DONUT processing failed: {e}")
            return None

    def convert_donut_to_invoice(self, donut_result: Dict[str, Any]) -> Optional[Invoice]:
        """
        Convert DONUT output format to our Invoice model.
        DONUT CORD format needs mapping to our structure.
        """
        try:
            if not donut_result or 'gt_parse' not in donut_result:
                return None

            parsed_data = donut_result['gt_parse']

            # This is a simplified converter - would need refinement based on actual DONUT output
            # DONUT CORD format has menu items, totals, etc.

            # Extract basic information (this would need adjustment based on actual DONUT output structure)
            invoice_data = {
                'metadata': {
                    'invoice_number': parsed_data.get('invoice_number'),
                    'issue_date': parsed_data.get('date'),
                },
                'parties': {
                    'vendor': {
                        'name': parsed_data.get('vendor_name', 'Unknown'),
                    },
                    'customer': {
                        'name': parsed_data.get('customer_name', 'Unknown'),
                    }
                },
                'financial_details': {
                    'currency': 'EUR',  # Default assumption
                    'subtotal': float(parsed_data.get('subtotal', 0)),
                    'total_amount': float(parsed_data.get('total', 0)),
                    'tax': {
                        'type': 'IVA',
                        'rate': 21.0,  # Default Spanish rate
                        'amount': 0.0
                    }
                },
                'items': []
            }

            # Extract line items if available
            if 'menu' in parsed_data:
                for item in parsed_data['menu']:
                    invoice_data['items'].append({
                        'description': item.get('nm', ''),
                        'quantity': int(item.get('cnt', 1)),
                        'unit_price': float(item.get('price', 0)),
                        'line_total': float(item.get('price', 0)) * int(item.get('cnt', 1))
                    })

            # Create Invoice object
            return Invoice.model_validate(invoice_data)

        except Exception as e:
            logger.error(f"DONUT to Invoice conversion failed: {e}")
            return None


# Global instance
donut_engine = DonutOCREngine()