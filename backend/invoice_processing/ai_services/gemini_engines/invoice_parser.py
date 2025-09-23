# Copyright 2024 Artificial Intelligence Labs, SL

"""
Invoice Parser - SIMPLE and FOCUSED
One responsibility: parse invoice text into structured data
"""

import json
import re
from typing import Dict, Any, Optional
from loguru import logger


class InvoiceTextParser:
    """
    Parses extracted text into structured invoice data.
    Under 100 lines, single responsibility.
    """

    @staticmethod
    def parse_to_invoice_data(text: str) -> Optional[Dict[str, Any]]:
        """
        Parse Gemini extracted text to invoice data.

        Args:
            text: Raw text from Gemini

        Returns:
            Dict with parsed invoice data or None
        """
        try:
            # Try to parse as JSON first (if Gemini returns structured JSON)
            if text.strip().startswith('{'):
                return json.loads(text)

            # Otherwise, use regex parsing
            return InvoiceTextParser._regex_parse(text)

        except Exception as e:
            logger.error(f"Invoice parsing failed: {e}")
            return None

    @staticmethod
    def _regex_parse(text: str) -> Dict[str, Any]:
        """
        Parse invoice text using regex patterns.
        Simple fallback for unstructured text.
        """
        data = {}

        # Extract vendor name (look for common patterns)
        vendor_patterns = [
            r"vendor[:\s]+([^\n]+)",
            r"from[:\s]+([^\n]+)",
            r"bill from[:\s]+([^\n]+)",
        ]
        for pattern in vendor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["vendor_name"] = match.group(1).strip()
                break

        # Extract customer name
        customer_patterns = [
            r"customer[:\s]+([^\n]+)",
            r"to[:\s]+([^\n]+)",
            r"bill to[:\s]+([^\n]+)",
        ]
        for pattern in customer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["customer_name"] = match.group(1).strip()
                break

        # Extract total amount
        total_patterns = [
            r"total[:\s]+[\$€]?(\d+[.,]\d{2})",
            r"amount[:\s]+[\$€]?(\d+[.,]\d{2})",
            r"[\$€](\d+[.,]\d{2})",
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '.')
                try:
                    data["total_amount"] = float(amount_str)
                    break
                except ValueError:
                    continue

        # Set confidence based on extraction success
        fields_found = len([v for v in data.values() if v])
        data["confidence"] = min(0.9, fields_found * 0.3)

        return data


# Convenience instance
invoice_parser = InvoiceTextParser()