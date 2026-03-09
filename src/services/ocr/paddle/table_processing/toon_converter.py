"""
TOON (Token-Oriented Object Notation) converter for invoice tables.

This module converts OCR table structures into token-efficient TOON format,
improving LLM understanding and reducing prompt size by ~39%.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class TableCell:
    """Represents a single table cell."""
    content: str
    is_header: bool = False


@dataclass
class TableRow:
    """Represents a table row with cells."""
    cells: List[TableCell]


@dataclass
class Table:
    """Represents a complete table structure."""
    headers: List[str]
    rows: List[List[str]]
    page_num: int
    table_num: int


class TOONConverter:
    """
    Converts HTML/structured tables into TOON format.

    TOON Format Rules:
    - Arrays declared with [N] where N is length
    - Headers declared with {field1, field2, ...}
    - Values separated by commas
    - Empty cells represented as empty string
    """

    @staticmethod
    def convert_html_table(html_str: str, page_num: int, table_num: int = 1) -> str:
        """
        Convert HTML table to TOON format.

        Args:
            html_str: HTML table string from PaddleOCR
            page_num: Page number
            table_num: Table number on page

        Returns:
            TOON-formatted table string
        """
        try:
            table = TOONConverter._parse_html_to_structure(html_str, page_num, table_num)
            return TOONConverter._structure_to_toon(table)
        except Exception as e:
            logger.error(f"Failed to convert HTML to TOON (page {page_num}, table {table_num}): {e}")
            # Fallback to simple text representation
            return TOONConverter._fallback_conversion(html_str, page_num, table_num)

    @staticmethod
    def _parse_html_to_structure(html_str: str, page_num: int, table_num: int) -> Table:
        """
        Parse HTML string into structured Table object.

        Args:
            html_str: Raw HTML string
            page_num: Page number
            table_num: Table number

        Returns:
            Table object with headers and rows
        """
        import html
        from html.parser import HTMLParser

        class TableParser(HTMLParser):
            """Simple HTML parser for table extraction."""

            def __init__(self):
                super().__init__()
                self.current_row: List[TableCell] = []
                self.rows: List[TableRow] = []
                self.in_header = False
                self.in_cell = False
                self.current_content = ""

            def handle_starttag(self, tag: str, attrs):
                if tag == "th":
                    self.in_header = True
                    self.in_cell = True
                elif tag == "td":
                    self.in_cell = True
                elif tag == "tr":
                    self.current_row = []

            def handle_endtag(self, tag: str):
                if tag in ("th", "td"):
                    content = self.current_content.strip()
                    self.current_row.append(
                        TableCell(content=content, is_header=self.in_header)
                    )
                    self.current_content = ""
                    self.in_cell = False
                    self.in_header = False
                elif tag == "tr" and self.current_row:
                    self.rows.append(TableRow(cells=self.current_row))

            def handle_data(self, data: str):
                if self.in_cell:
                    self.current_content += data

        # Parse HTML
        clean_html = html.unescape(html_str)
        parser = TableParser()
        parser.feed(clean_html)

        # Extract headers and data rows
        headers = []
        data_rows = []

        for row in parser.rows:
            if any(cell.is_header for cell in row.cells):
                # This is a header row
                headers = [cell.content for cell in row.cells]
            else:
                # This is a data row
                data_rows.append([cell.content for cell in row.cells])

        # If no explicit headers found, use generic ones
        if not headers and data_rows:
            num_cols = len(data_rows[0])
            headers = [f"col{i+1}" for i in range(num_cols)]

        return Table(
            headers=headers,
            rows=data_rows,
            page_num=page_num,
            table_num=table_num
        )

    @staticmethod
    def _structure_to_toon(table: Table) -> str:
        """
        Convert structured Table to TOON format.

        Args:
            table: Structured table object

        Returns:
            TOON-formatted string
        """
        if not table.rows:
            return f"TABLE {table.table_num} (Page {table.page_num}): Empty table"

        # Format header
        header_str = ", ".join(table.headers)

        # Format rows
        row_strings = []
        for row in table.rows:
            # Pad row if it has fewer cells than headers
            padded_row = row + [""] * (len(table.headers) - len(row))
            # Truncate if it has more
            padded_row = padded_row[:len(table.headers)]
            # Escape commas in cell content
            escaped_cells = [
                cell.replace(",", "\\,") if "," in cell else cell
                for cell in padded_row
            ]
            row_strings.append(", ".join(escaped_cells))

        # Construct TOON format
        toon_output = [
            f"TABLE {table.table_num} (Page {table.page_num}) [{len(table.rows)}]",
            f"{{{header_str}}}",
            *row_strings
        ]

        return "\n".join(toon_output)

    @staticmethod
    def _fallback_conversion(html_str: str, page_num: int, table_num: int) -> str:
        """
        Fallback conversion when HTML parsing fails.

        Args:
            html_str: Raw HTML string
            page_num: Page number
            table_num: Table number

        Returns:
            Simple text representation
        """
        import re

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', html_str)
        # Clean up whitespace
        text = ' '.join(text.split())

        return f"TABLE {table_num} (Page {page_num}): {text}"


class TOONTableAnalyzer:
    """
    Analyzes table structure to provide hints for LLM.

    Detects common invoice table patterns and provides context hints.
    """

    # Common patterns in invoice tables
    EXPENSE_CATEGORY_KEYWORDS = {
        'HONORARIOS', 'SUPLIDOS', 'PROVISIONES', 'PROV.FONDOS',
        'RETENCION', 'BASE IMP', 'BASE IMPONIBLE'
    }

    STANDARD_ITEM_KEYWORDS = {
        'DESCRIPCION', 'DESCRIPTION', 'CONCEPTO', 'ITEM',
        'CANTIDAD', 'QUANTITY', 'QTY', 'UNITS', 'UNIDADES',
        'PRECIO', 'PRICE', 'PVP', 'UNIT PRICE', 'PRECIO UNITARIO',
        'TOTAL', 'IMPORTE', 'AMOUNT', 'LINE TOTAL'
    }

    @classmethod
    def analyze_table(cls, table: Table) -> Dict[str, Any]:
        """
        Analyze table structure and provide hints.

        Args:
            table: Structured table object

        Returns:
            Dictionary with structure type and hints
        """
        headers_upper = [h.upper() for h in table.headers]

        # Count pattern matches
        expense_matches = sum(
            1 for header in headers_upper
            if any(keyword in header for keyword in cls.EXPENSE_CATEGORY_KEYWORDS)
        )

        item_matches = sum(
            1 for header in headers_upper
            if any(keyword in header for keyword in cls.STANDARD_ITEM_KEYWORDS)
        )

        # Determine structure type
        if expense_matches >= 2:
            structure_type = "expense_category_table"
            hint = (
                "STRUCTURE: Expense category table. "
                "Columns represent expense types. "
                "Extract ONE item per row with non-zero category as line_total."
            )
        elif item_matches >= 3:
            structure_type = "standard_line_items"
            hint = (
                "STRUCTURE: Standard line item table. "
                "Each row is a separate product/service. "
                "Extract one item per row."
            )
        else:
            structure_type = "generic"
            hint = ""

        logger.info(
            f"Table structure: {structure_type} "
            f"(expense={expense_matches}, item={item_matches})"
        )

        return {
            "structure_type": structure_type,
            "hint": hint,
            "headers": table.headers,
            "row_count": len(table.rows)
        }
