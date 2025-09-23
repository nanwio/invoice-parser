from io import BytesIO
from typing import List, Tuple
from pdf2image import convert_from_path
from PIL import Image
from surya.ocr import run_ocr
from surya.model.detection import segformer
from surya.model.recognition import load_model, load_processor
from surya.postprocessing.text import draw_text_on_image
import torch

from invoice_processing.utilities.document_utils import get_pypdf_document_hash

class SuryaProcessor:
    """
    Handles invoice processing using the Surya OCR engine.

    This class encapsulates the logic for converting PDF documents to images,
    running the OCR process to detect and recognize text, and preparing
    the output for further processing by a language model.
    """

    def __init__(self):
        self.langs = ["en", "es"]
        self.det_processor, self.det_model = self._load_detection_models()
        self.rec_model, self.rec_processor = self._load_recognition_models()

    def _load_detection_models(self):
        """Loads the text detection models."""
        det_processor = segformer.load_processor()
        det_model = segformer.load_model()
        return det_processor, det_model

    def _load_recognition_models(self):
        """Loads the text recognition models."""
        rec_model = load_model()
        rec_processor = load_processor()
        return rec_model, rec_processor

    def _convert_pdf_to_images(self, pdf_path: str) -> List[Image.Image]:
        """Converts a PDF file to a list of PIL images."""
        return convert_from_path(pdf_path)

    def _run_ocr_on_images(self, images: List[Image.Image]) -> List[str]:
        """
        Runs the OCR process on a list of images and returns the detected text lines.
        """
        predictions = run_ocr(images, [self.langs] * len(images), self.det_model, self.det_processor, self.rec_model, self.rec_processor)
        
        text_lines = []
        for pred in predictions:
            for line in pred.text_lines:
                text_lines.append(line.text)
        
        return text_lines

    def process_invoice(self, pdf_path: str) -> Tuple[str, str]:
        """
        Processes an invoice PDF, extracts text using Surya OCR, and returns
        the formatted text and the document hash.

        Args:
            pdf_path: The file path to the PDF invoice.

        Returns:
            A tuple containing the formatted OCR text and the SHA256 hash of the document.
        """
        doc_hash = get_pypdf_document_hash(pdf_path)
        images = self._convert_pdf_to_images(pdf_path)
        text_lines = self._run_ocr_on_images(images)
        
        formatted_text = "\n".join(text_lines)
        
        return formatted_text, doc_hash
