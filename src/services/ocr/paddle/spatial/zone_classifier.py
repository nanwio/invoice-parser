"""
Hybrid Zone Classifier for Document Layout Analysis.

Combines three classification strategies (in priority order):
1. Content-based classification (text patterns - most reliable)
2. PPStructure region type (when provided)
3. Spatial position (fallback)

Based on S2 Chunking methodology (arXiv:2501.05485) with content analysis.
"""
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class DocumentZone(Enum):
    """Document zones for invoice structure."""
    HEADER = "HEADER"           # Vendor info at top
    CUSTOMER_BOX = "CUSTOMER"   # Customer info box
    CONTENT = "CONTENT"         # Invoice details, line items
    FOOTER = "FOOTER"           # Legal info, payment details


@dataclass
class ZonedTextItem:
    """Text item with zone classification."""
    text: str
    zone: DocumentZone
    bbox: Tuple[float, float, float, float]
    confidence: float
    y_center: float
    x_center: float


class ContentAnalyzer:
    """
    Analyzes text content to determine semantic zone.

    This is the key improvement: classify based on WHAT the text says,
    not just WHERE it is positioned.
    """

    # Vendor contact patterns (email, phone, IBAN, website)
    EMAIL_PATTERN = re.compile(r'[\w.+-]+@[\w.-]+\.\w+', re.IGNORECASE)
    PHONE_PATTERN = re.compile(r'(?:Tel[éef]?[:\.\s]*|Tfno[:\.\s]*|Phone[:\.\s]*)?\d{3}[\s.-]?\d{3}[\s.-]?\d{3,4}', re.IGNORECASE)
    IBAN_PATTERN = re.compile(r'[A-Z]{2}\d{2}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}[\s]?\d{4}', re.IGNORECASE)
    WEBSITE_PATTERN = re.compile(r'www\.[\w.-]+\.\w+', re.IGNORECASE)

    # Spanish tax ID patterns
    NIF_CIF_PATTERN = re.compile(r'\b[A-Z][-]?\d{7,8}[-]?[A-Z0-9]?\b', re.IGNORECASE)

    # Currency/numeric patterns (prices, amounts)
    CURRENCY_PATTERN = re.compile(r'[\d.,]+\s*[€$£]|[€$£]\s*[\d.,]+|\d+[.,]\d{2}\s*(?:EUR|USD)?', re.IGNORECASE)
    PURE_NUMERIC_PATTERN = re.compile(r'^\s*[\d.,]+\s*[€$£%]?\s*$')

    # Invoice field keywords
    PRICE_KEYWORDS = {'precio', 'price', 'pvp', 'importe', 'amount', 'total', 'subtotal',
                      'base', 'cuota', 'iva', 'igic', 'tax', 'dto', 'descuento'}

    # Customer section keywords
    CUSTOMER_KEYWORDS = {'cliente', 'customer', 'bill to', 'ship to', 'facturar a',
                         'destinatario', 'comprador', 'buyer'}

    # Address patterns
    ADDRESS_INDICATORS = {'calle', 'c/', 'av.', 'avda', 'plaza', 'street', 'road',
                          'paseo', 'carretera', 'urbanización', 'edif', 'edificio',
                          'piso', 'puerta', 'pta', 'bajo', 'local'}

    POSTAL_CODE_PATTERN = re.compile(r'\b\d{5}\b')

    @classmethod
    def has_vendor_contact_info(cls, text: str) -> bool:
        """Check if text contains vendor contact indicators (email, phone, IBAN)."""
        text_lower = text.lower()
        return bool(
            cls.EMAIL_PATTERN.search(text) or
            cls.IBAN_PATTERN.search(text) or
            cls.WEBSITE_PATTERN.search(text) or
            (cls.PHONE_PATTERN.search(text) and ('tel' in text_lower or 'tfno' in text_lower))
        )

    @classmethod
    def is_numeric_or_price(cls, text: str) -> bool:
        """Check if text is primarily numeric/currency (prices, quantities)."""
        text = text.strip()
        if not text:
            return False

        # Direct numeric/currency check
        if cls.PURE_NUMERIC_PATTERN.match(text):
            return True

        # Check for currency amounts
        if cls.CURRENCY_PATTERN.search(text):
            # If text is short and has currency, it's a price
            if len(text) < 20:
                return True

        # Check for price keywords only (without substantial other text)
        text_lower = text.lower()
        words = set(text_lower.split())
        if words & cls.PRICE_KEYWORDS and len(text) < 30:
            return True

        return False

    @classmethod
    def has_address_pattern(cls, text: str) -> bool:
        """Check if text contains address indicators."""
        text_lower = text.lower()

        # Check for address keywords
        has_address_keyword = any(ind in text_lower for ind in cls.ADDRESS_INDICATORS)

        # Check for postal code
        has_postal = bool(cls.POSTAL_CODE_PATTERN.search(text))

        # Must have address keyword OR (postal code AND reasonable length)
        return has_address_keyword or (has_postal and len(text) > 15)

    @classmethod
    def has_customer_keyword(cls, text: str) -> bool:
        """Check if text contains customer section keywords."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in cls.CUSTOMER_KEYWORDS)

    @classmethod
    def analyze(cls, text: str) -> Dict[str, bool]:
        """
        Analyze text content and return classification signals.

        Returns:
            Dict with boolean flags for different content types
        """
        return {
            'has_vendor_contact': cls.has_vendor_contact_info(text),
            'is_numeric_price': cls.is_numeric_or_price(text),
            'has_address': cls.has_address_pattern(text),
            'has_customer_keyword': cls.has_customer_keyword(text),
            'has_tax_id': bool(cls.NIF_CIF_PATTERN.search(text)),
        }


class HybridZoneClassifier:
    """
    Hybrid zone classifier combining content analysis with spatial heuristics.

    Classification priority:
    1. Content-based (most reliable for invoices)
    2. PPStructure region type (if provided)
    3. Spatial position (fallback)
    """

    # Spatial thresholds (percentage of document dimensions)
    HEADER_THRESHOLD = 0.18      # Top 18% is header
    FOOTER_THRESHOLD = 0.85      # Bottom 15% is footer
    CUSTOMER_BOX_X_THRESHOLD = 0.55  # Right 45% may contain customer box
    CUSTOMER_BOX_Y_MAX = 0.35        # Customer box usually in top 35%

    def __init__(self, image_height: int, image_width: int):
        """Initialize classifier with document dimensions."""
        self.image_height = image_height
        self.image_width = image_width
        self.analyzer = ContentAnalyzer

        # Calculate pixel thresholds
        self.header_y_limit = image_height * self.HEADER_THRESHOLD
        self.footer_y_start = image_height * self.FOOTER_THRESHOLD
        self.customer_x_start = image_width * self.CUSTOMER_BOX_X_THRESHOLD
        self.customer_y_limit = image_height * self.CUSTOMER_BOX_Y_MAX

        logger.debug(
            f"HybridZoneClassifier initialized: "
            f"header_y<{self.header_y_limit:.0f}, "
            f"footer_y>{self.footer_y_start:.0f}, "
            f"customer_x>{self.customer_x_start:.0f}"
        )

    def classify_text_item(
        self,
        text: str,
        bbox: List,
        confidence: float,
        region_type: Optional[str] = None
    ) -> ZonedTextItem:
        """
        Classify a text item using hybrid approach.

        Args:
            text: OCR text content
            bbox: Bounding box
            confidence: OCR confidence score
            region_type: PPStructure region type (optional)

        Returns:
            ZonedTextItem with zone classification
        """
        # Normalize bbox format
        if len(bbox) == 4 and isinstance(bbox[0], list):
            x1, y1 = bbox[0]
            x2, y2 = bbox[2]
        elif len(bbox) == 4:
            x1, y1, x2, y2 = bbox
        else:
            logger.warning(f"Unknown bbox format: {bbox}")
            return ZonedTextItem(
                text=text, zone=DocumentZone.CONTENT,
                bbox=(0, 0, 0, 0), confidence=confidence,
                y_center=self.image_height / 2,
                x_center=self.image_width / 2
            )

        y_center = (y1 + y2) / 2
        x_center = (x1 + x2) / 2

        # Determine zone using hybrid approach
        zone = self._classify_hybrid(text, x_center, y_center, region_type)

        return ZonedTextItem(
            text=text, zone=zone,
            bbox=(x1, y1, x2, y2), confidence=confidence,
            y_center=y_center, x_center=x_center
        )

    def _classify_hybrid(
        self,
        text: str,
        x_center: float,
        y_center: float,
        region_type: Optional[str] = None
    ) -> DocumentZone:
        """
        Hybrid classification: content first, then position.

        Priority:
        1. Content-based classification (text patterns)
        2. PPStructure region type
        3. Spatial position fallback
        """
        # Analyze content
        content = self.analyzer.analyze(text)

        # --- PRIORITY 1: Content-based classification ---

        # Numeric/price content on the right side → CONTENT (not customer!)
        # This fixes the receipt/ticket issue
        if content['is_numeric_price']:
            return DocumentZone.CONTENT

        # Vendor contact info (email/phone/IBAN) → HEADER or FOOTER depending on position
        if content['has_vendor_contact']:
            if y_center > self.footer_y_start:
                return DocumentZone.FOOTER
            return DocumentZone.HEADER

        # Customer keyword explicitly mentioned → CUSTOMER_BOX
        if content['has_customer_keyword']:
            return DocumentZone.CUSTOMER_BOX

        # --- PRIORITY 2: PPStructure region type ---

        if region_type:
            region_type_lower = region_type.lower()
            if region_type_lower == 'header':
                return DocumentZone.HEADER
            elif region_type_lower == 'footer':
                return DocumentZone.FOOTER
            elif region_type_lower == 'table':
                return DocumentZone.CONTENT

        # --- PRIORITY 3: Spatial position fallback ---

        # Check for potential customer box (right side, upper area)
        # BUT only if it contains address-like content or tax ID
        is_right_upper = (
            x_center > self.customer_x_start and
            y_center < self.customer_y_limit and
            y_center > self.header_y_limit * 0.5
        )

        if is_right_upper:
            # Only classify as CUSTOMER if it looks like customer data
            if content['has_address'] or content['has_tax_id']:
                return DocumentZone.CUSTOMER_BOX
            # Otherwise, it's probably invoice content (prices, totals)
            return DocumentZone.CONTENT

        # Header (top of document)
        if y_center < self.header_y_limit:
            return DocumentZone.HEADER

        # Footer (bottom of document)
        if y_center > self.footer_y_start:
            return DocumentZone.FOOTER

        # Default to content
        return DocumentZone.CONTENT

    def classify_all(
        self,
        ocr_results: List[Dict[str, Any]],
        region_type: Optional[str] = None
    ) -> List[ZonedTextItem]:
        """
        Classify all OCR results into zones.

        Args:
            ocr_results: List of OCR results
            region_type: PPStructure region type for all items (optional)

        Returns:
            List of ZonedTextItem sorted by reading order
        """
        zoned_items = []

        for item in ocr_results:
            if isinstance(item, dict):
                text = item.get('text', '')
                confidence = item.get('confidence', 0.0)
                bbox = item.get('text_region') or item.get('bbox', [[0,0], [0,0], [0,0], [0,0]])
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                bbox = item[0]
                text_conf = item[1]
                if isinstance(text_conf, (list, tuple)):
                    text = text_conf[0]
                    confidence = text_conf[1] if len(text_conf) > 1 else 0.0
                else:
                    text = str(text_conf)
                    confidence = 0.0
            else:
                continue

            if not text.strip():
                continue

            zoned_item = self.classify_text_item(text, bbox, confidence, region_type)
            zoned_items.append(zoned_item)

        # Sort by reading order
        zoned_items.sort(key=lambda x: (x.y_center, x.x_center))

        return zoned_items

    def format_zoned_text(self, zoned_items: List[ZonedTextItem]) -> str:
        """Format zoned text items with zone markers for LLM processing."""
        zones: Dict[DocumentZone, List[ZonedTextItem]] = {
            DocumentZone.HEADER: [],
            DocumentZone.CUSTOMER_BOX: [],
            DocumentZone.CONTENT: [],
            DocumentZone.FOOTER: [],
        }

        for item in zoned_items:
            zones[item.zone].append(item)

        output_parts = []

        if zones[DocumentZone.HEADER]:
            header_text = '\n'.join(item.text for item in zones[DocumentZone.HEADER])
            output_parts.append(f"[VENDOR_HEADER]\n{header_text}")

        if zones[DocumentZone.CUSTOMER_BOX]:
            customer_text = '\n'.join(item.text for item in zones[DocumentZone.CUSTOMER_BOX])
            output_parts.append(f"[CUSTOMER_INFO]\n{customer_text}")

        if zones[DocumentZone.CONTENT]:
            content_text = '\n'.join(item.text for item in zones[DocumentZone.CONTENT])
            output_parts.append(f"[INVOICE_CONTENT]\n{content_text}")

        if zones[DocumentZone.FOOTER]:
            footer_text = '\n'.join(item.text for item in zones[DocumentZone.FOOTER])
            output_parts.append(f"[VENDOR_FOOTER]\n{footer_text}")

        formatted = '\n\n'.join(output_parts)

        zone_counts = {z.value: len(items) for z, items in zones.items()}
        logger.info(f"Zone distribution: {zone_counts}")

        return formatted


# Backward compatibility alias
SpatialZoneClassifier = HybridZoneClassifier
