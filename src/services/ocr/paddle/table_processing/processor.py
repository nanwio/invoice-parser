"""Invoice table processor using PaddleOCR PPStructure."""
import asyncio
from typing import List, Dict, Any
from loguru import logger
from PIL import Image
import numpy as np

from src.services.ocr.paddle.provider import PaddleOCRProvider
from .html_converter import HTMLTableConverter
from .text_extractor import RegionTextExtractor


class InvoiceTableProcessor:
    """Processes invoice pages with PPStructure table recognition."""

    def __init__(self, engine=None, gpu_lock=None):
        """
        Initialize with optional dependency injection.

        Args:
            engine: PPStructure engine (default: from provider)
            gpu_lock: GPU lock (default: from provider)
        """
        self.engine = engine if engine is not None else PaddleOCRProvider.get_engine()
        self.gpu_lock = gpu_lock if gpu_lock is not None else PaddleOCRProvider.get_lock()
        self._is_gpu_available = PaddleOCRProvider.is_gpu_available()

        logger.info(
            f"Invoice Table Processor initialized "
            f"({'GPU mode with lock' if self._is_gpu_available else 'CPU mode'})"
        )

    async def process_image_async(self, image: Image.Image, page_num: int) -> Dict[str, Any]:
        """
        Process single page with PPStructure.

        Args:
            image: PIL Image
            page_num: Page number

        Returns:
            Processing result dictionary
        """
        logger.debug(f"Processing page {page_num} with PPStructure")

        img_array = np.array(image)

        def process_with_lock():
            with self.gpu_lock:
                return self.engine(img_array)

        result = await asyncio.to_thread(process_with_lock)

        logger.debug(f"Page {page_num}: Found {len(result)} regions")

        all_html, all_text_parts, table_count = self._process_regions(result, page_num)

        combined_html = "\n".join(all_html) if all_html else ""
        combined_text = "\n\n".join(all_text_parts) if all_text_parts else ""

        if not combined_text and result:
            combined_text = RegionTextExtractor.extract(result, page_num)

        logger.info(f"Page {page_num}: Extracted {table_count} tables, text length: {len(combined_text)}")

        return {
            "page_number": page_num,
            "text": combined_text,
            "html": combined_html,
            "structure_score": 1.0,
            "table_count": table_count,
            "region_count": len(result)
        }

    def _process_regions(self, regions: List[Dict[str, Any]], page_num: int) -> tuple:
        """
        Process PPStructure regions to extract tables and text.

        Args:
            regions: List of regions from PPStructure
            page_num: Page number

        Returns:
            Tuple of (html_list, text_list, table_count)
        """
        all_html = []
        all_text_parts = []
        table_count = 0

        for region in regions:
            region_type = region.get('type', 'Unknown')

            if region_type == 'table':
                table_count += 1
                html_content = region.get('res', {}).get('html', '')

                if html_content:
                    all_html.append(html_content)
                    text_repr = HTMLTableConverter.convert(html_content, page_num, table_count)
                    all_text_parts.append(text_repr)
                    logger.debug(f"Page {page_num}: Extracted table {table_count}")

            elif region_type == 'figure':
                logger.debug(f"Page {page_num}: Skipping figure region")
            else:
                logger.debug(f"Page {page_num}: Found {region_type} region")

        return all_html, all_text_parts, table_count

    async def process_images_parallel(self, images: List[Image.Image]) -> List[Dict[str, Any]]:
        """
        Process multiple pages in parallel.

        Args:
            images: List of PIL Images

        Returns:
            List of processing results
        """
        logger.info(f"Processing {len(images)} pages with PPStructure table recognition")

        tasks = [
            self.process_image_async(img, idx + 1)
            for idx, img in enumerate(images)
        ]

        results = await asyncio.gather(*tasks)

        total_tables = sum(r.get("table_count", 0) for r in results)
        total_regions = sum(r.get("region_count", 0) for r in results)
        logger.info(f"PPStructure complete: {len(results)} pages, {total_tables} tables, {total_regions} regions")

        return results
