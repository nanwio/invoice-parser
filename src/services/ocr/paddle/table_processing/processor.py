"""Invoice table processor using PaddleOCR PPStructure."""
import asyncio
from typing import Any
from loguru import logger
from PIL import Image
import numpy as np
import cv2

from src.services.ocr.paddle.provider import PaddleOCRProvider
from src.services.ocr.paddle.quality_analysis.detector import ImageQualityDetector
from src.services.ocr.paddle.preprocessing.orchestrator import PreprocessingOrchestrator
from src.services.ocr.paddle.spatial import SpatialZoneClassifier
from .toon_converter import TOONConverter, TOONTableAnalyzer
from .text_extractor import RegionTextExtractor
from .html_extractor import HTMLTextExtractor


class InvoiceTableProcessor:
    """
    Processes invoice pages with adaptive PPStructure extraction.

    Uses dual-mode strategy:
    1. First tries layout mode (better for complex documents)
    2. Falls back to table mode if layout extracts insufficient text
    """

    def __init__(self, engine=None, gpu_lock=None):
        """
        Initialize with dual engines for adaptive extraction.

        Args:
            engine: PPStructure engine (default: layout engine from provider)
            gpu_lock: GPU lock (default: from provider)
        """
        # Dual engines for adaptive fallback
        self.layout_engine = PaddleOCRProvider.get_layout_engine()
        self.table_engine = PaddleOCRProvider.get_table_engine()
        self.gpu_lock = gpu_lock if gpu_lock is not None else PaddleOCRProvider.get_lock()
        self._is_gpu_available = PaddleOCRProvider.is_gpu_available()

        # Fallback threshold
        self.fallback_threshold = PaddleOCRProvider.get_fallback_threshold()

        # Add image quality analysis and preprocessing
        self.quality_detector = ImageQualityDetector()
        self.preprocessor = PreprocessingOrchestrator()

        logger.info(
            f"Invoice Table Processor initialized with adaptive fallback "
            f"(threshold={self.fallback_threshold} chars, "
            f"{'GPU mode' if self._is_gpu_available else 'CPU mode'})"
        )

    async def process_image_async(self, image: Image.Image, page_num: int) -> dict[str, Any]:
        """
        Process single page with PPStructure using adaptive dual-mode strategy.

        Strategy:
        1. First tries layout mode (better for complex documents with headers/footers)
        2. Falls back to table mode if layout extracts insufficient text (<threshold chars)

        Args:
            image: PIL Image
            page_num: Page number

        Returns:
            Processing result dictionary
        """
        logger.debug(f"Processing page {page_num} with PPStructure (adaptive mode)")

        # Convert PIL to numpy array (BGR for OpenCV)
        img_array = np.array(image.convert('RGB'))
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # Analyze image quality
        quality_analysis = self.quality_detector.analyze(img_array)
        logger.debug(f"Page {page_num} quality: score={quality_analysis.overall_score:.1f}, "
                    f"contrast={quality_analysis.contrast_score:.1f}, "
                    f"noise={quality_analysis.noise_level:.1f}")

        # Apply preprocessing if needed
        if quality_analysis.overall_score < 70.0:
            logger.info(f"Page {page_num}: Applying preprocessing (low quality detected)")
            img_array = self.preprocessor.preprocess(img_array, quality_analysis)

        # Get image dimensions for spatial zone classification
        img_height, img_width = img_array.shape[:2]

        # --- ADAPTIVE DUAL-MODE STRATEGY ---
        # Step 1: Try layout mode first (better for complex documents)
        logger.info(f"Page {page_num}: Trying layout mode first...")

        def run_layout_engine():
            return self.layout_engine(img_array)

        layout_result = await asyncio.to_thread(run_layout_engine)
        logger.debug(f"Page {page_num}: Layout mode returned {len(layout_result)} regions")

        # Process layout result
        layout_html, layout_text_parts, layout_table_count = self._process_regions(
            layout_result, page_num, img_height, img_width
        )
        layout_text = "\n\n".join(layout_text_parts) if layout_text_parts else ""

        if not layout_text and layout_result:
            layout_text = RegionTextExtractor.extract(layout_result, page_num)

        layout_chars = len(layout_text)
        logger.info(f"Page {page_num}: Layout mode extracted {layout_chars} chars")

        # Step 2: Check if fallback is needed
        if layout_chars >= self.fallback_threshold:
            # Layout mode extracted enough text - use it
            logger.info(f"Page {page_num}: Layout mode sufficient ({layout_chars} >= {self.fallback_threshold})")
            combined_html = "\n".join(layout_html) if layout_html else ""
            return {
                "page_number": page_num,
                "text": layout_text,
                "html": combined_html,
                "structure_score": 1.0,
                "table_count": layout_table_count,
                "region_count": len(layout_result),
                "extraction_mode": "layout"
            }

        # Step 3: Fallback to table mode
        logger.info(f"Page {page_num}: Layout mode insufficient ({layout_chars} < {self.fallback_threshold}), "
                   f"falling back to table mode...")

        def run_table_engine():
            return self.table_engine(img_array)

        table_result = await asyncio.to_thread(run_table_engine)
        logger.debug(f"Page {page_num}: Table mode returned {len(table_result)} regions")

        # Process table result
        table_html, table_text_parts, table_table_count = self._process_regions(
            table_result, page_num, img_height, img_width
        )
        table_text = "\n\n".join(table_text_parts) if table_text_parts else ""

        if not table_text and table_result:
            table_text = RegionTextExtractor.extract(table_result, page_num)

        table_chars = len(table_text)
        logger.info(f"Page {page_num}: Table mode extracted {table_chars} chars")

        # Step 4: Choose the better result
        if table_chars > layout_chars:
            logger.info(f"Page {page_num}: Using table mode result ({table_chars} > {layout_chars} chars)")
            combined_html = "\n".join(table_html) if table_html else ""
            return {
                "page_number": page_num,
                "text": table_text,
                "html": combined_html,
                "structure_score": 1.0,
                "table_count": table_table_count,
                "region_count": len(table_result),
                "extraction_mode": "table"
            }
        else:
            # Even though layout had less than threshold, it's still better than table
            logger.info(f"Page {page_num}: Keeping layout mode result ({layout_chars} >= {table_chars} chars)")
            combined_html = "\n".join(layout_html) if layout_html else ""
            return {
                "page_number": page_num,
                "text": layout_text,
                "html": combined_html,
                "structure_score": 1.0,
                "table_count": layout_table_count,
                "region_count": len(layout_result),
                "extraction_mode": "layout"
            }

    def _process_regions(
        self,
        regions: list[dict[str, Any]],
        page_num: int,
        img_height: int = 1000,
        img_width: int = 800
    ) -> tuple:
        """
        Process PPStructure regions to extract tables and text.

        Uses spatial zone classification (based on S2 Chunking methodology)
        to organize text into logical document zones.

        Args:
            regions: List of regions from PPStructure
            page_num: Page number
            img_height: Image height for spatial analysis
            img_width: Image width for spatial analysis

        Returns:
            Tuple of (html_list, text_list, table_count)
        """
        all_html = []
        all_text_parts = []
        table_count = 0

        # Initialize spatial zone classifier
        zone_classifier = SpatialZoneClassifier(img_height, img_width)

        for region in regions:
            region_type = region.get('type', 'Unknown')
            res = region.get('res', {})
            bbox = region.get('bbox', [])

            # Debug: Log region details
            logger.debug(
                f"Page {page_num}: Region type='{region_type}', "
                f"bbox={bbox[:2] if bbox else 'N/A'}, "
                f"res_type={type(res).__name__}, "
                f"res_len={len(res) if hasattr(res, '__len__') else 'N/A'}"
            )

            if region_type == 'table':
                table_count += 1
                html_content = res.get('html', '') if isinstance(res, dict) else ''

                if html_content:
                    all_html.append(html_content)

                    # Check if this is a full-page table (layout=False mode)
                    # In this case, extract structured text instead of TOON format
                    is_full_page = (
                        bbox and len(bbox) >= 4 and
                        bbox[0] < 50 and bbox[1] < 50 and  # Starts near top-left
                        (bbox[2] - bbox[0]) > img_width * 0.9  # Spans most of width
                    )

                    logger.debug(
                        f"Page {page_num}: is_full_page check: bbox={bbox}, "
                        f"img_width={img_width}, result={is_full_page}"
                    )

                    if is_full_page:
                        # Full-page table = document extracted as table (layout=False)
                        # Use structured text extraction with zone markers
                        structured_text = HTMLTextExtractor.extract_structured(html_content)
                        if structured_text:
                            all_text_parts.append(structured_text)
                            logger.info(
                                f"Page {page_num}: Full-page extraction ({len(structured_text)} chars)"
                            )
                            logger.debug(f"Page {page_num}: Extracted text:\n{structured_text[:500]}...")
                    else:
                        # Normal table within document
                        toon_repr = TOONConverter.convert_html_table(html_content, page_num, table_count)
                        all_text_parts.append(toon_repr)
                        logger.debug(f"Page {page_num}: Extracted table {table_count} (TOON format)")

            elif region_type in ('figure', 'text', 'title'):
                # These regions contain OCR text - use hybrid zone classification
                if isinstance(res, list) and len(res) > 0:
                    # Apply hybrid zone classification (content + spatial + PPStructure type)
                    zoned_items = zone_classifier.classify_all(res, region_type=region_type)
                    zoned_text = zone_classifier.format_zoned_text(zoned_items)

                    if zoned_text:
                        all_text_parts.append(zoned_text)
                        logger.debug(
                            f"Page {page_num}: Spatial zone classification applied "
                            f"to {region_type} ({len(zoned_items)} items classified)"
                        )
                else:
                    # Fallback to simple extraction - log what we got
                    logger.warning(
                        f"Page {page_num}: {region_type} region has non-list res: "
                        f"type={type(res).__name__}, preview={str(res)[:200]}"
                    )
                    text_content = self._extract_text_from_region(res)
                    if text_content:
                        all_text_parts.append(f"[DOCUMENT TEXT]\n{text_content}")
                        logger.debug(f"Page {page_num}: Extracted text from {region_type} region ({len(text_content)} chars)")

            elif region_type in ('header', 'footer', 'reference'):
                # Extract text from text-based regions
                text_content = self._extract_text_from_region(res)
                if text_content:
                    all_text_parts.append(f"[{region_type.upper()}]\n{text_content}")
                    logger.debug(f"Page {page_num}: Extracted {region_type} region ({len(text_content)} chars)")

            else:
                # Try to extract text from unknown region types
                text_content = self._extract_text_from_region(res)
                if text_content:
                    all_text_parts.append(text_content)
                logger.debug(f"Page {page_num}: Found {region_type} region")

        return all_html, all_text_parts, table_count

    def _extract_text_from_region(self, res: Any) -> str:
        """
        Extract text content from a region's result.

        Args:
            res: Region result (can be dict, list, or str)

        Returns:
            Extracted text
        """
        if isinstance(res, dict):
            return res.get('text', '')
        elif isinstance(res, list):
            # OCR result format: list of [bbox, (text, confidence)]
            lines = []
            for item in res:
                if isinstance(item, dict):
                    lines.append(item.get('text', ''))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    text_part = item[1]
                    if isinstance(text_part, (list, tuple)) and len(text_part) >= 1:
                        lines.append(str(text_part[0]))
                    elif isinstance(text_part, str):
                        lines.append(text_part)
            return '\n'.join(filter(None, lines))
        elif isinstance(res, str):
            return res
        return ''

    async def process_images_parallel(self, images: list[Image.Image]) -> list[dict[str, Any]]:
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
