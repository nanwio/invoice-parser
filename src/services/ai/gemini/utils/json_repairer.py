"""JSON repair utilities for handling truncated/corrupt Gemini responses."""
import json
from loguru import logger


class JSONRepairer:
    """Repairs truncated or malformed JSON from Gemini."""

    @staticmethod
    def repair(json_text: str, error: json.JSONDecodeError) -> str:
        """
        Attempt to repair truncated JSON.

        Args:
            json_text: Malformed JSON text
            error: JSONDecodeError with position info

        Returns:
            Repaired JSON text

        Raises:
            json.JSONDecodeError: If repair fails
        """
        logger.warning(f"JSON parsing failed at position {error.pos}: {error.msg}")
        logger.warning("Attempting to repair JSON (likely truncated response from Gemini)")

        truncate_pos = error.pos
        json_text_truncated = json_text[:truncate_pos].rstrip()

        open_braces = json_text_truncated.count('{') - json_text_truncated.count('}')
        open_brackets = json_text_truncated.count('[') - json_text_truncated.count(']')

        if json_text_truncated.endswith(','):
            json_text_truncated = json_text_truncated[:-1]

        json_text_repaired = json_text_truncated + (']' * open_brackets) + ('}' * open_braces)

        logger.info(f"Repaired JSON: added {open_brackets} closing brackets and {open_braces} closing braces")

        try:
            json.loads(json_text_repaired)
            logger.warning("✓ JSON repair successful! Parsed truncated invoice with potentially incomplete items list.")
            return json_text_repaired
        except json.JSONDecodeError as e2:
            logger.error(f"JSON repair failed: {e2}")
            raise error
