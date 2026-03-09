"""Helper utilities for invoice processing pipeline."""
import os
from loguru import logger


def format_ocr_results_for_llm(ocr_results: list[dict]) -> str:
    """
    Format OCR results with page delimiters for LLM processing.

    Args:
        ocr_results: List of OCR result dicts with page_number and text

    Returns:
        Formatted text string
    """
    formatted_parts = []
    for result in ocr_results:
        page_num = result.get("page_number", "N/A")
        text = result.get("text", "")
        formatted_parts.append(f"[INICIO PÁGINA {page_num}]\n{text}\n[FIN PÁGINA {page_num}]")

    return "\n\n".join(formatted_parts)


async def cleanup_temp_file(temp_path: str):
    """
    Clean up temporary file asynchronously.

    Args:
        temp_path: Path to temporary file
    """
    try:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
