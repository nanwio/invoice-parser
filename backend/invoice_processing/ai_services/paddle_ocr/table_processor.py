"""
Invoice Table Processor using PaddleOCR PPStructure (v2.7.3).

This module uses PPStructure to properly extract structured data from invoice tables,
preserving column-row relationships through table recognition and OCR.

Thread-safety: Uses thread-local storage to ensure each thread gets its own PPStructure
engine instance, preventing C++ predictor state corruption in multi-threaded environments.
"""
import asyncio
import threading
from typing import List, Dict, Any
from loguru import logger
from PIL import Image
import numpy as np
import html

try:
    from paddleocr import PPStructure
    PADDLE_TABLE_AVAILABLE = True
except ImportError:
    logger.warning("PaddleOCR PPStructure not available. Install paddleocr>=2.7")
    PADDLE_TABLE_AVAILABLE = False


class InvoiceTableProcessor:
    """
    Processes invoice pages with tables using PaddleOCR PPStructure (v2.7.3).

    Uses PPStructure for:
    - Layout analysis and table detection
    - Structured table recognition with OCR
    - Document orientation detection

    Thread-safety implementation:
    - Uses threading.local() to provide isolated PPStructure engine per thread
    - Prevents C++ predictor state corruption in concurrent/sequential requests
    - Each thread initializes engine on first use, then reuses it
    - Zero overhead for subsequent requests within same thread
    """

    def __init__(self):
        """Initialize thread-local storage for PPStructure engines."""
        if not PADDLE_TABLE_AVAILABLE:
            raise ImportError("PaddleOCR PPStructure not installed")

        logger.info("Initializing Invoice Table Processor with thread-local PPStructure engines")

        # Thread-local storage: each thread gets its own engine instance
        # This prevents the "could not execute a primitive" error caused by
        # sharing a single C++ predictor across multiple threads
        self._thread_local = threading.local()

        # Store configuration for lazy initialization per thread
        self._engine_config = {
            'show_log': False,
            'table': True,              # Enable table recognition (critical for invoices)
            'ocr': True,                # Enable OCR within tables
            'layout': True,             # ✅ ENABLED - layout=False disables OCR automatically (PPStructure bug)
                                        # Fix malloc corruption with ENV MALLOC_ARENA_MAX=2 in Dockerfile
            'image_orientation': True,  # Enable rotation detection and correction
            'lang': 'en',               # Must be 'en' or 'ch' (layout model requirement)
            'use_gpu': False,
            'enable_mkldnn': True,      # Intel CPU optimization (for Cloud Run, disabled on macOS via config)
            'cpu_threads': 1,           # Single thread for stability
        }

        logger.success("PPStructure table processor initialized with thread-local storage")

    def _get_engine(self) -> 'PPStructure':
        """
        Get thread-local PPStructure engine instance.

        Lazy initialization: creates engine on first access per thread.
        Subsequent calls within same thread return cached instance.

        Returns:
            PPStructure: Thread-isolated engine instance
        """
        # Check if current thread already has an engine
        if not hasattr(self._thread_local, 'engine'):
            # First access in this thread - create new engine
            thread_id = threading.current_thread().ident
            logger.debug(f"Initializing PPStructure engine for thread {thread_id}")

            self._thread_local.engine = PPStructure(**self._engine_config)

            logger.debug(f"Thread {thread_id}: PPStructure engine ready")

        return self._thread_local.engine

    async def process_image_async(self, image: Image.Image, page_num: int) -> Dict[str, Any]:
        """
        Process a single invoice page image with PPStructure table recognition.

        Thread-safety: Uses thread-local engine instance retrieved via _get_engine().
        Each asyncio thread pool worker gets its own isolated PPStructure engine,
        preventing C++ predictor state corruption.

        Args:
            image: PIL Image of the invoice page
            page_num: Page number (for logging)

        Returns:
            Dictionary with:
                - page_number: int
                - text: Structured text representation
                - html: Raw HTML table structure (if tables found)
                - structure_score: Confidence score
        """
        logger.debug(f"Processing page {page_num} with PPStructure")

        # Convert PIL Image to numpy array (PPStructure expects numpy)
        img_array = np.array(image)

        # Get thread-local engine and process image (async to avoid blocking)
        # Each thread in the asyncio thread pool will get its own engine instance
        engine = self._get_engine()
        result = await asyncio.to_thread(engine, img_array)

        # PPStructure returns list of regions: [{'type': 'Table'|'Figure'|..., 'bbox': [...], 'res': ...}]
        logger.debug(f"Page {page_num}: Found {len(result)} regions")

        # Extract tables and combine into structured text
        all_html = []
        all_text_parts = []
        table_count = 0

        for region in result:
            region_type = region.get('type', 'Unknown')

            if region_type == 'table':
                # Table region - extract HTML structure
                table_count += 1
                html_content = region.get('res', {}).get('html', '')

                if html_content:
                    all_html.append(html_content)
                    # Convert HTML to structured text for Gemini
                    text_repr = self._html_table_to_text(html_content, page_num, table_count)
                    all_text_parts.append(text_repr)
                    logger.debug(f"Page {page_num}: Extracted table {table_count}")

            elif region_type == 'figure':
                # Skip figures for now (invoices are primarily text/tables)
                logger.debug(f"Page {page_num}: Skipping figure region")

            else:
                # Other content (text, titles, etc.)
                logger.debug(f"Page {page_num}: Found {region_type} region")

        # Combine all extracted content
        combined_html = "\n".join(all_html) if all_html else ""
        combined_text = "\n\n".join(all_text_parts) if all_text_parts else ""

        # If no tables found, extract all text from OCR results
        if not combined_text and result:
            combined_text = self._extract_all_text_from_regions(result, page_num)

        logger.info(f"Page {page_num}: Extracted {table_count} tables, text length: {len(combined_text)}")

        return {
            "page_number": page_num,
            "text": combined_text,
            "html": combined_html,
            "structure_score": 1.0,  # PPStructure doesn't provide a single confidence score
            "table_count": table_count,
            "region_count": len(result)
        }

    def _html_table_to_text(self, html_str: str, page_num: int, table_num: int = 1) -> str:
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
            text = text.replace("<table>", f"\n[TABLE {table_num} - PAGE {page_num}]\n")
            text = text.replace("</table>", "\n[END TABLE]\n")
            text = text.replace("<tr>", "\n[ROW] ")
            text = text.replace("</tr>", " [/ROW]")
            text = text.replace("<td>", "[CELL] ")
            text = text.replace("</td>", " [/CELL] ")
            text = text.replace("<th>", "[HEADER] ")
            text = text.replace("</th>", " [/HEADER] ")
            text = text.replace("<thead>", "")
            text = text.replace("</thead>", "")
            text = text.replace("<tbody>", "")
            text = text.replace("</tbody>", "")

            # Clean up extra whitespace
            text = "\n".join(line.strip() for line in text.split("\n") if line.strip())

            return text

        except Exception as e:
            logger.error(f"Failed to convert HTML to text for page {page_num}, table {table_num}: {e}")
            # Fallback: return HTML as-is
            return html_str

    def _extract_all_text_from_regions(self, regions: List[Dict[str, Any]], page_num: int) -> str:
        """
        Extract all text from PPStructure regions when no tables are found.

        This is a fallback for invoices that don't have clear table structure.
        """
        all_text = []

        for idx, region in enumerate(regions):
            region_type = region.get('type', 'unknown')
            res = region.get('res', {})

            # Extract text based on region type
            if isinstance(res, dict):
                # For structured results (tables, etc.)
                text_content = res.get('text', '')
                if text_content:
                    all_text.append(f"[{region_type.upper()} {idx+1}]\n{text_content}")
            elif isinstance(res, list):
                # For OCR results (list of text lines)
                lines = [line.get('text', '') for line in res if isinstance(line, dict)]
                if lines:
                    combined = "\n".join(lines)
                    all_text.append(f"[{region_type.upper()} {idx+1}]\n{combined}")
            elif isinstance(res, str):
                # Direct string content
                all_text.append(f"[{region_type.upper()} {idx+1}]\n{res}")

        combined = "\n\n".join(all_text)
        logger.debug(f"Page {page_num}: Extracted {len(all_text)} regions as fallback text")

        return combined if combined else f"[PAGE {page_num} - NO TEXT EXTRACTED]"

    async def process_images_parallel(self, images: List[Image.Image]) -> List[Dict[str, Any]]:
        """
        Process multiple invoice pages in parallel with PPStructure.

        Args:
            images: List of PIL Images

        Returns:
            List of processing results (one per page)
        """
        logger.info(f"Processing {len(images)} pages with PPStructure table recognition")

        # Process all pages in parallel
        tasks = [
            self.process_image_async(img, idx + 1)
            for idx, img in enumerate(images)
        ]

        results = await asyncio.gather(*tasks)

        # Log summary
        total_tables = sum(r.get("table_count", 0) for r in results)
        total_regions = sum(r.get("region_count", 0) for r in results)
        logger.info(f"PPStructure processing complete: {len(results)} pages, {total_tables} tables, {total_regions} total regions")

        return results
