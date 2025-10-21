"""
Invoice Table Processor using PaddleOCR specialized table modules.

This module uses TableStructureRecognition and DocImgOrientationClassification
to properly extract structured data from invoice tables, preserving column-row relationships.
"""
import asyncio
from typing import List, Dict, Any
from loguru import logger
from PIL import Image
import html

try:
    from paddleocr import TableStructureRecognition, DocImgOrientationClassification
    PADDLE_TABLE_AVAILABLE = True
except ImportError:
    logger.warning("PaddleOCR table modules not available. Install paddleocr>=2.7")
    PADDLE_TABLE_AVAILABLE = False


class InvoiceTableProcessor:
    """
    Processes invoice pages with tables using specialized PaddleOCR modules.

    Uses:
    - DocImgOrientationClassification: Detects and corrects document rotation
    - TableStructureRecognition: Extracts table structure as HTML
    """

    def __init__(self):
        """Initialize table processing models."""
        if not PADDLE_TABLE_AVAILABLE:
            raise ImportError("PaddleOCR table modules not installed")

        logger.info("Initializing Invoice Table Processor with PaddleOCR specialized modules")

        # Orientation classifier (very fast: ~0.6ms)
        self.orientation_classifier = DocImgOrientationClassification(
            model_name="PP-LCNet_x1_0_doc_ori",
            enable_hpi=True  # High-performance mode
        )

        # Table structure recognizer (SLANet_plus: best for complex tables)
        self.table_recognizer = TableStructureRecognition(
            model_name="SLANet_plus",  # 63.69% accuracy, improved for complex/wireless tables
            enable_hpi=True,  # High-performance mode
            batch_size=1
        )

        logger.success("Table processing models loaded successfully")

    async def process_image_async(self, image: Image.Image, page_num: int) -> Dict[str, Any]:
        """
        Process a single invoice page image with table structure recognition.

        Args:
            image: PIL Image of the invoice page
            page_num: Page number (for logging)

        Returns:
            Dictionary with:
                - page_number: int
                - text: Structured text representation
                - html: Raw HTML table structure
                - structure_score: Confidence score
        """
        logger.debug(f"Processing page {page_num} with table recognition")

        # Step 1: Detect and correct orientation (async)
        orientation_result = await asyncio.to_thread(
            self.orientation_classifier.predict,
            image,
            batch_size=1
        )

        orientation_class = orientation_result[0]["class_ids"][0]
        orientation_angles = {0: 0, 1: 90, 2: 180, 3: 270}
        angle = orientation_angles.get(orientation_class, 0)

        if angle != 0:
            logger.info(f"Page {page_num} rotated {angle}° - correcting orientation")
            image = image.rotate(-angle, expand=True)  # Counter-rotate to correct

        # Step 2: Recognize table structure (async)
        table_result = await asyncio.to_thread(
            self.table_recognizer.predict,
            image,
            batch_size=1
        )

        # Extract HTML structure and confidence
        html_structure = table_result[0]["structure"]  # List of HTML tokens
        structure_score = table_result[0].get("structure_score", 0.0)

        # Convert token list to HTML string
        html_str = "".join(html_structure)

        logger.debug(f"Page {page_num}: Table structure extracted (score: {structure_score:.2f})")

        # Step 3: Convert HTML table to structured text for Gemini
        structured_text = self._html_table_to_text(html_str, page_num)

        return {
            "page_number": page_num,
            "text": structured_text,
            "html": html_str,
            "structure_score": structure_score,
            "orientation_corrected": angle != 0,
            "rotation_angle": angle
        }

    def _html_table_to_text(self, html_str: str, page_num: int) -> str:
        """
        Convert HTML table structure to clean text format for Gemini.

        Preserves table structure but makes it readable for LLM parsing.
        """
        try:
            # Unescape HTML entities
            clean_html = html.unescape(html_str)

            # Simple conversion: replace HTML tags with text markers
            # This preserves structure while being LLM-friendly
            text = clean_html.replace("<html><body>", "")
            text = text.replace("</body></html>", "")
            text = text.replace("<table>", f"\n[TABLE PAGE {page_num}]\n")
            text = text.replace("</table>", "\n[END TABLE]\n")
            text = text.replace("<tr>", "\n[ROW] ")
            text = text.replace("</tr>", " [/ROW]")
            text = text.replace("<td>", "[CELL] ")
            text = text.replace("</td>", " [/CELL] ")
            text = text.replace("<thead>", "[HEADER] ")
            text = text.replace("</thead>", " [/HEADER]\n")
            text = text.replace("<tbody>", "")
            text = text.replace("</tbody>", "")

            # Clean up extra whitespace
            text = "\n".join(line.strip() for line in text.split("\n") if line.strip())

            return text

        except Exception as e:
            logger.error(f"Failed to convert HTML to text for page {page_num}: {e}")
            # Fallback: return HTML as-is
            return html_str

    async def process_images_parallel(self, images: List[Image.Image]) -> List[Dict[str, Any]]:
        """
        Process multiple invoice pages in parallel.

        Args:
            images: List of PIL Images

        Returns:
            List of processing results (one per page)
        """
        logger.info(f"Processing {len(images)} pages with table recognition")

        # Process all pages in parallel
        tasks = [
            self.process_image_async(img, idx + 1)
            for idx, img in enumerate(images)
        ]

        results = await asyncio.gather(*tasks)

        # Log summary
        avg_score = sum(r["structure_score"] for r in results) / len(results)
        logger.info(f"Table processing complete: {len(results)} pages, avg confidence: {avg_score:.2f}")

        return results
