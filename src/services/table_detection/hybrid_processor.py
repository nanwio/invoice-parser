"""Hybrid table processor combining TATR + PaddleOCR.

Pipeline:
1. TATR: Detect table structures (cells with row/col indices)
2. PaddleOCR: Detect and recognize text (bounding boxes + content)
3. Matcher: Assign texts to cells using vectorized IoU
4. Formatter: Generate TOON output for LLM

Performance target: <5 seconds per page on NVIDIA L4 GPU
"""

import asyncio
from typing import List, Dict, Any, Tuple
from loguru import logger
from PIL import Image
import numpy as np

from src.services.table_detection.tatr_processor import TATRProcessor, TableDetection
from src.services.ocr.paddle.text_detector import PaddleTextDetector, TextBox
from src.services.table_detection.cell_text_matcher import CellTextMatcher


class HybridTableProcessor:
    """Orchestrates TATR + PaddleOCR for accurate table extraction."""

    def __init__(self, device: str = None, confidence_threshold: float = 0.7):
        """Initialize hybrid processor.

        Args:
            device: 'cuda' or 'cpu' (auto-detect if None)
            confidence_threshold: Min confidence for TATR cell detection
        """
        self.tatr = TATRProcessor(device=device, confidence_threshold=confidence_threshold)
        self.paddle_ocr = PaddleTextDetector()

        logger.info("HybridTableProcessor initialized (TATR + PaddleOCR)")

    async def process_image_async(self, image: Image.Image, page_num: int) -> Dict[str, Any]:
        """Process single page with hybrid pipeline.

        Args:
            image: PIL Image (RGB)
            page_num: Page number

        Returns:
            Processing result dictionary with text and table data
        """
        logger.debug(f"Processing page {page_num} with TATR + PaddleOCR")

        # Run TATR and PaddleOCR in parallel for maximum speed
        tatr_task = self.tatr.detect_tables_async(image)
        ocr_task = self.paddle_ocr.detect_text_async(image)

        tables, text_boxes = await asyncio.gather(tatr_task, ocr_task)

        logger.debug(f"Page {page_num}: TATR found {len(tables)} tables, PaddleOCR found {len(text_boxes)} texts")

        # Process tables
        all_toon_parts = []
        all_html_parts = []
        table_count = 0

        for table_idx, table in enumerate(tables, 1):
            table_count += 1

            # Match texts to cells
            cell_bbox_list = [
                (cell.row, cell.col, cell.bbox)
                for cell in table.cells
            ]

            cell_texts = CellTextMatcher.match_texts_to_cells(
                text_boxes=text_boxes,
                cell_boxes=cell_bbox_list,
                iou_threshold=0.5,
                use_centroid_fallback=True
            )

            # Format as TOON
            toon_repr = CellTextMatcher.format_table_as_toon(
                cell_texts=cell_texts,
                num_rows=table.num_rows,
                num_cols=table.num_cols,
                page_num=page_num,
                table_num=table_idx
            )
            all_toon_parts.append(toon_repr)

            # Format as JSON (for HTML generation if needed)
            table_json = CellTextMatcher.format_table_as_json(
                cell_texts=cell_texts,
                num_rows=table.num_rows,
                num_cols=table.num_cols
            )
            all_html_parts.append(self._generate_html_table(table_json))

            logger.debug(f"Page {page_num}: Extracted table {table_idx} "
                        f"({table.num_rows} rows × {table.num_cols} cols)")

        # Extract non-table text (texts not assigned to any table)
        non_table_text = self._extract_non_table_text(text_boxes, tables)

        # Combine table and non-table text
        combined_text_parts = []

        if non_table_text:
            combined_text_parts.append(non_table_text)

        combined_text_parts.extend(all_toon_parts)

        combined_text = "\n\n".join(combined_text_parts)
        combined_html = "\n".join(all_html_parts)

        logger.info(f"Page {page_num}: Extracted {table_count} tables, "
                   f"text length: {len(combined_text)} chars")

        return {
            "page_number": page_num,
            "text": combined_text,
            "html": combined_html,
            "structure_score": 1.0,
            "table_count": table_count,
            "region_count": len(tables) + (1 if non_table_text else 0)
        }

    async def process_images_parallel(self, images: List[Image.Image]) -> List[Dict[str, Any]]:
        """Process multiple pages in parallel.

        Args:
            images: List of PIL Images

        Returns:
            List of processing results
        """
        logger.info(f"Processing {len(images)} pages with hybrid TATR+PaddleOCR pipeline")

        tasks = [
            self.process_image_async(img, idx + 1)
            for idx, img in enumerate(images)
        ]

        results = await asyncio.gather(*tasks)

        total_tables = sum(r.get("table_count", 0) for r in results)
        total_regions = sum(r.get("region_count", 0) for r in results)

        logger.info(f"Hybrid processing complete: {len(results)} pages, "
                   f"{total_tables} tables, {total_regions} regions")

        return results

    def _extract_non_table_text(self, text_boxes: List[TextBox], tables: List[TableDetection]) -> str:
        """Extract text that is outside all table boundaries.

        Args:
            text_boxes: All detected text boxes
            tables: All detected tables

        Returns:
            Concatenated non-table text
        """
        if not tables:
            # No tables, all text is non-table text
            return "\n".join(tb.text for tb in text_boxes)

        # Filter texts outside all tables
        non_table_texts = []

        for text_box in text_boxes:
            cx, cy = text_box.centroid
            is_in_table = False

            for table in tables:
                tx1, ty1, tx2, ty2 = table.bbox
                if tx1 <= cx <= tx2 and ty1 <= cy <= ty2:
                    is_in_table = True
                    break

            if not is_in_table:
                non_table_texts.append(text_box.text)

        return "\n".join(non_table_texts) if non_table_texts else ""

    def _generate_html_table(self, table_data: List[List[str]]) -> str:
        """Generate HTML representation of table.

        Args:
            table_data: 2D list of cell contents

        Returns:
            HTML table string
        """
        if not table_data:
            return ""

        html_lines = ["<table>"]

        for row in table_data:
            html_lines.append("  <tr>")
            for cell in row:
                html_lines.append(f"    <td>{cell}</td>")
            html_lines.append("  </tr>")

        html_lines.append("</table>")

        return "\n".join(html_lines)
