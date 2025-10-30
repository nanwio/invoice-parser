"""HTML table to text converter."""
import html
from loguru import logger


class HTMLTableConverter:
    """Converts HTML table structure to clean text format."""

    @staticmethod
    def convert(html_str: str, page_num: int, table_num: int = 1) -> str:
        """
        Convert HTML table to LLM-friendly text format.

        Args:
            html_str: HTML table string
            page_num: Page number
            table_num: Table number on page

        Returns:
            Structured text representation
        """
        try:
            clean_html = html.unescape(html_str)

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

            text = "\n".join(line.strip() for line in text.split("\n") if line.strip())

            return text

        except Exception as e:
            logger.error(f"Failed to convert HTML (page {page_num}, table {table_num}): {e}")
            return html_str
