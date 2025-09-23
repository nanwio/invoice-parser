# Copyright 2024 Artificial Intelligence Labs, SL

"""
DONUT Output Parser - SIMPLE and FOCUSED
One responsibility: parse DONUT model output
"""

import re
from typing import Dict, Any
from loguru import logger


class DonutOutputParser:
    """
    Parses DONUT model output to extract invoice fields.
    Under 100 lines, single responsibility.
    """

    @staticmethod
    def parse_donut_output(sequence: str) -> Dict[str, Any]:
        """
        Parse DONUT model output to extract invoice fields.
        Simple regex-based parsing.

        Args:
            sequence: Raw output from DONUT model

        Returns:
            Dict with extracted invoice data
        """
        data = {}

        try:
            # Extract company names (simple patterns)
            company_match = re.search(r'"company":\s*"([^"]+)"', sequence)
            if company_match:
                data["vendor_name"] = company_match.group(1)

            # Extract totals
            total_match = re.search(r'"total_price":\s*"([^"]+)"', sequence)
            if total_match:
                total_str = total_match.group(1).replace(",", "").replace("$", "").replace("€", "")
                try:
                    data["total_amount"] = float(total_str)
                except ValueError:
                    data["total_amount"] = 0.0

            # Extract addresses
            address_match = re.search(r'"address":\s*"([^"]+)"', sequence)
            if address_match:
                data["address"] = address_match.group(1)

            # Extract dates
            date_match = re.search(r'"date":\s*"([^"]+)"', sequence)
            if date_match:
                data["date"] = date_match.group(1)

            # Set confidence based on extraction success
            fields_found = len([v for v in data.values() if v])
            data["confidence"] = min(0.9, fields_found * 0.2 + 0.1)

            logger.debug(f"Parsed DONUT output: {len(data)} fields extracted")
            return data

        except Exception as e:
            logger.error(f"DONUT output parsing failed: {e}")
            return {"confidence": 0.0}


# Convenience instance
donut_parser = DonutOutputParser()