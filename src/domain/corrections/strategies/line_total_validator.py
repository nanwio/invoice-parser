"""Corrects line_total values that grossly disagree with quantity x unit_price.

When the LLM picks a wrong column (e.g. a discount percentage instead of the printed
line total), the resulting line_total fails the cheap arithmetic check
`line_total ~= qty * unit_price * (1 - discount)`. This validator scans the raw OCR
text for a numeric token that fits the plausibility window and substitutes it.
"""
import re
from typing import Optional

from loguru import logger

from src.domain.models import Invoice


class LineTotalValidator:
    """Substitute implausible line_total values using nearby OCR numbers."""

    MISMATCH_THRESHOLD = 0.5   # |actual - expected| / expected above this triggers correction
    TOLERANCE_LOW = 0.5        # candidate >= expected * 0.5  (allows up to 50% line discount)
    TOLERANCE_HIGH = 1.05      # candidate <= expected * 1.05 (allows minor rounding above)
    NUMBER_RE = re.compile(r"\d+(?:[,.]\d+)?")

    @classmethod
    def apply(cls, invoice: Invoice, ocr_text: Optional[str]) -> Invoice:
        if not invoice.items or not ocr_text:
            return invoice

        candidates = cls._extract_numbers(ocr_text)
        if not candidates:
            return invoice

        for idx, item in enumerate(invoice.items):
            qty = item.quantity
            price = item.unit_price
            actual = item.line_total
            if qty <= 0 or price <= 0:
                continue

            expected = qty * price
            rel_err = abs(actual - expected) / expected
            if rel_err <= cls.MISMATCH_THRESHOLD:
                continue

            lo = cls.TOLERANCE_LOW * expected
            hi = cls.TOLERANCE_HIGH * expected
            # Exclude the item's own qty/unit_price/line_total: those are OCR tokens that
            # happen to live in the row but cannot be the real line_total we are searching for.
            forbidden = {round(qty, 4), round(price, 4), round(actual, 4)}
            in_range = [c for c in candidates if lo <= c <= hi and round(c, 4) not in forbidden]

            label = (item.description or "")[:40]
            if not in_range:
                logger.warning(
                    f"Item {idx+1} '{label}': line_total={actual} disagrees with "
                    f"qty*price={expected:.2f} (rel_err={rel_err:.0%}); no OCR substitute "
                    f"in [{lo:.2f}, {hi:.2f}]"
                )
                continue

            best = min(in_range, key=lambda c: abs(c - expected))
            logger.info(
                f"Item {idx+1} '{label}': line_total corrected {actual} -> {best} "
                f"(qty*price={expected:.2f}, rel_err was {rel_err:.0%})"
            )
            item.line_total = best

        return invoice

    @classmethod
    def _extract_numbers(cls, text: str) -> list[float]:
        """Extract numeric tokens. Spanish convention: comma is the decimal separator."""
        result: list[float] = []
        for match in cls.NUMBER_RE.finditer(text):
            tok = match.group(0)
            try:
                result.append(float(tok.replace(",", ".")))
            except ValueError:
                continue
        return result
