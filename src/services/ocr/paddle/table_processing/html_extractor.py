"""HTML to text extractor for PPStructure table output."""
import re
from typing import List
from html.parser import HTMLParser
from loguru import logger


class TableHTMLParser(HTMLParser):
    """Parse HTML table and extract text with structure preservation."""

    def __init__(self):
        super().__init__()
        self.rows: List[List[str]] = []
        self.current_row: List[str] = []
        self.current_cell: str = ""
        self.in_cell = False

    def handle_starttag(self, tag, attrs):
        if tag in ('td', 'th'):
            self.in_cell = True
            self.current_cell = ""
        elif tag == 'tr':
            self.current_row = []

    def handle_endtag(self, tag):
        if tag in ('td', 'th'):
            self.in_cell = False
            self.current_row.append(self.current_cell.strip())
        elif tag == 'tr':
            if self.current_row:
                self.rows.append(self.current_row)

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell += data


class HTMLTextExtractor:
    """Extract structured text from PPStructure HTML table output."""

    @staticmethod
    def extract_text(html: str) -> str:
        """
        Extract text from HTML table preserving some structure.

        Args:
            html: HTML string from PPStructure

        Returns:
            Structured text representation
        """
        if not html:
            return ""

        parser = TableHTMLParser()
        try:
            parser.feed(html)
        except Exception as e:
            logger.warning(f"HTML parsing error: {e}")
            # Fallback: strip HTML tags
            return HTMLTextExtractor._strip_html_tags(html)

        # Convert rows to text
        lines = []
        for row in parser.rows:
            # Filter empty cells
            cells = [c for c in row if c.strip()]
            if cells:
                # Join cells with separator
                line = " | ".join(cells)
                lines.append(line)

        text = "\n".join(lines)

        logger.debug(f"HTMLTextExtractor: {len(parser.rows)} rows -> {len(text)} chars")
        return text

    @staticmethod
    def _strip_html_tags(html: str) -> str:
        """Fallback: remove HTML tags."""
        clean = re.sub(r'<[^>]+>', ' ', html)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()

    @staticmethod
    def extract_structured(html: str) -> str:
        """
        Extract text with intelligent entity classification.

        Analyzes text content to identify vendor vs customer based on:
        - Presence of contact info (email, phone, IBAN) = VENDOR
        - Spanish NIF/CIF patterns with entity type identification

        Args:
            html: HTML string from PPStructure

        Returns:
            Text with entity markers for Gemini processing
        """
        if not html:
            return ""

        parser = TableHTMLParser()
        try:
            parser.feed(html)
        except Exception as e:
            logger.warning(f"HTML parsing error: {e}")
            return HTMLTextExtractor._strip_html_tags(html)

        if not parser.rows:
            return HTMLTextExtractor._strip_html_tags(html)

        # Flatten all cells for analysis
        all_text_parts = []
        vendor_indicators = []
        customer_indicators = []

        for row in parser.rows:
            for cell in row:
                cell = cell.strip()
                if not cell:
                    continue

                # Check for vendor indicators (contact info)
                has_email = '@' in cell and '.' in cell.split('@')[-1] if '@' in cell else False
                has_phone = bool(re.search(r'Tel[:\s]*\d{6,}', cell, re.I))
                has_iban = bool(re.search(r'ES\d{2}\s*\d{4}', cell))

                if has_email or has_phone or has_iban:
                    vendor_indicators.append(cell)
                else:
                    all_text_parts.append(cell)

        # Build output - vendor info first (entities with contact), then rest
        output_parts = []

        if vendor_indicators:
            vendor_text = "\n".join(vendor_indicators)
            output_parts.append(f"[VENDOR_INFO - Has contact details]\n{vendor_text}")

        if all_text_parts:
            # Join remaining text, removing duplicates while preserving order
            seen = set()
            unique_parts = []
            for part in all_text_parts:
                if part not in seen:
                    seen.add(part)
                    unique_parts.append(part)
            remaining_text = "\n".join(unique_parts)
            output_parts.append(f"[DOCUMENT_CONTENT]\n{remaining_text}")

        return "\n\n".join(output_parts)
