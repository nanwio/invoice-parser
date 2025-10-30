"""Text extraction from PPStructure regions."""
from typing import List, Dict, Any
from loguru import logger


class RegionTextExtractor:
    """Extracts text from PPStructure regions."""

    @staticmethod
    def extract(regions: List[Dict[str, Any]], page_num: int) -> str:
        """
        Extract all text from regions (fallback when no tables found).

        Args:
            regions: List of PPStructure regions
            page_num: Page number

        Returns:
            Combined text from all regions
        """
        all_text = []

        for idx, region in enumerate(regions):
            region_type = region.get('type', 'unknown')
            res = region.get('res', {})

            if isinstance(res, dict):
                text_content = res.get('text', '')
                if text_content:
                    all_text.append(f"[{region_type.upper()} {idx+1}]\n{text_content}")
            elif isinstance(res, list):
                lines = [line.get('text', '') for line in res if isinstance(line, dict)]
                if lines:
                    combined = "\n".join(lines)
                    all_text.append(f"[{region_type.upper()} {idx+1}]\n{combined}")
            elif isinstance(res, str):
                all_text.append(f"[{region_type.upper()} {idx+1}]\n{res}")

        combined = "\n\n".join(all_text)
        logger.debug(f"Page {page_num}: Extracted {len(all_text)} regions as fallback text")

        return combined if combined else f"[PAGE {page_num} - NO TEXT EXTRACTED]"
