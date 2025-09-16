# Copyright 2024 Artificial Intelligence Labs, SL

import re
from typing import List, Optional, Dict, Any
from difflib import SequenceMatcher
from loguru import logger

from app.services.verifactu.models import PhraseValidationResult


class PhraseValidator:
    """
    VERIFACTU Mandatory Phrase Detection and Validation System.

    Validates that invoices contain the mandatory VERIFACTU phrases according to
    Spanish tax regulations. Provides intelligent detection with typo correction.
    """

    def __init__(self):
        # Official mandatory phrases for VERIFACTU compliance (2026)
        self.mandatory_phrases = [
            "Factura verificable en la sede electrónica de la AEAT",
            "VERIFACTU",
            "Verificable en la sede electrónica de la Agencia Tributaria",
            "Factura verificable en sede electrónica AEAT"
        ]

        # Common variations and acceptable alternatives
        self.phrase_variations = {
            "factura verificable": [
                "factura verificable",
                "factura verificada",
                "factura comprobable",
                "documento verificable"
            ],
            "sede electronica": [
                "sede electrónica",
                "sede electronica",
                "sede digital",
                "portal electrónico",
                "portal electronico"
            ],
            "aeat": [
                "aeat",
                "agencia tributaria",
                "agencia estatal de administración tributaria",
                "hacienda"
            ]
        }

        # Minimum confidence threshold for phrase detection
        self.confidence_threshold = 0.7

    def validate_mandatory_phrase(self, extracted_text: str) -> PhraseValidationResult:
        """
        Main validation method for VERIFACTU mandatory phrases.

        Args:
            extracted_text: Text extracted from invoice document

        Returns:
            PhraseValidationResult with detection status and suggestions
        """
        logger.info("Validating VERIFACTU mandatory phrases")

        # Clean and normalize text for analysis
        normalized_text = self._normalize_text(extracted_text)

        # Step 1: Check for exact phrase matches
        exact_match_result = self._check_exact_matches(normalized_text)
        if exact_match_result.phrase_present and exact_match_result.exact_match:
            logger.info(f"Exact VERIFACTU phrase match found: {exact_match_result.found_phrase}")
            return exact_match_result

        # Step 2: Check for fuzzy matches with typos
        fuzzy_match_result = self._check_fuzzy_matches(normalized_text)
        if fuzzy_match_result.phrase_present:
            logger.info(f"Fuzzy VERIFACTU phrase match found: {fuzzy_match_result.found_phrase}")
            return fuzzy_match_result

        # Step 3: Check for partial matches (components present)
        partial_match_result = self._check_partial_matches(normalized_text)
        if partial_match_result.phrase_present:
            logger.warning(f"Partial VERIFACTU phrase detected: {partial_match_result.found_phrase}")
            return partial_match_result

        # No phrase found
        logger.warning("No VERIFACTU mandatory phrase detected")
        return PhraseValidationResult(
            phrase_present=False,
            exact_match=False,
            confidence=0.0,
            suggested_correction=self._get_default_phrase_suggestion()
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for better phrase matching."""
        if not text:
            return ""

        # Convert to lowercase and normalize whitespace
        normalized = re.sub(r'\s+', ' ', text.lower().strip())

        # Remove common OCR artifacts
        normalized = re.sub(r'[^\w\sáéíóúñü]', ' ', normalized)

        # Normalize accented characters for comparison
        accent_map = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ñ': 'n',
            'ü': 'u'
        }
        for accented, plain in accent_map.items():
            normalized = normalized.replace(accented, plain)

        return normalized

    def _check_exact_matches(self, normalized_text: str) -> PhraseValidationResult:
        """Check for exact matches of mandatory phrases."""
        for phrase in self.mandatory_phrases:
            normalized_phrase = self._normalize_text(phrase)

            if normalized_phrase in normalized_text:
                return PhraseValidationResult(
                    phrase_present=True,
                    exact_match=True,
                    found_phrase=phrase,
                    confidence=1.0
                )

        return PhraseValidationResult(phrase_present=False, exact_match=False)

    def _check_fuzzy_matches(self, normalized_text: str) -> PhraseValidationResult:
        """Check for fuzzy matches allowing for typos and OCR errors."""
        best_match = None
        best_confidence = 0.0
        best_phrase = None

        for phrase in self.mandatory_phrases:
            normalized_phrase = self._normalize_text(phrase)

            # Use sliding window to find best match in text
            confidence, match_text = self._find_best_fuzzy_match(
                normalized_phrase,
                normalized_text
            )

            if confidence > best_confidence and confidence >= self.confidence_threshold:
                best_confidence = confidence
                best_match = match_text
                best_phrase = phrase

        if best_match:
            return PhraseValidationResult(
                phrase_present=True,
                exact_match=False,
                found_phrase=best_match,
                confidence=best_confidence,
                suggested_correction=best_phrase
            )

        return PhraseValidationResult(phrase_present=False, exact_match=False)

    def _find_best_fuzzy_match(self, target_phrase: str, text: str) -> tuple[float, Optional[str]]:
        """Find the best fuzzy match for a phrase in text using sliding window."""
        words = text.split()
        target_words = target_phrase.split()
        target_length = len(target_words)

        best_ratio = 0.0
        best_match = None

        # Sliding window approach
        for i in range(len(words) - target_length + 1):
            window = ' '.join(words[i:i + target_length])
            ratio = SequenceMatcher(None, target_phrase, window).ratio()

            if ratio > best_ratio:
                best_ratio = ratio
                best_match = window

        # Also check with some flexibility in window size
        for window_size in [target_length - 1, target_length + 1, target_length + 2]:
            if window_size < 1:
                continue

            for i in range(len(words) - window_size + 1):
                window = ' '.join(words[i:i + window_size])
                ratio = SequenceMatcher(None, target_phrase, window).ratio()

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = window

        return best_ratio, best_match

    def _check_partial_matches(self, normalized_text: str) -> PhraseValidationResult:
        """Check for partial matches where key components are present."""
        # Check for key components
        has_factura = any(variant in normalized_text for variant in
                         self.phrase_variations["factura verificable"])

        has_sede = any(variant in normalized_text for variant in
                      self.phrase_variations["sede electronica"])

        has_aeat = any(variant in normalized_text for variant in
                      self.phrase_variations["aeat"])

        has_verifactu = "verifactu" in normalized_text

        # Score based on components present
        component_score = 0
        found_components = []

        if has_factura:
            component_score += 0.4
            found_components.append("factura verificable")

        if has_sede:
            component_score += 0.3
            found_components.append("sede electrónica")

        if has_aeat:
            component_score += 0.2
            found_components.append("AEAT")

        if has_verifactu:
            component_score += 0.8  # VERIFACTU alone is quite strong
            found_components.append("VERIFACTU")

        if component_score >= 0.5:  # At least half the components
            found_phrase = " + ".join(found_components)
            confidence = min(component_score, 0.9)  # Cap confidence for partial matches

            return PhraseValidationResult(
                phrase_present=True,
                exact_match=False,
                found_phrase=found_phrase,
                confidence=confidence,
                suggested_correction=self._suggest_complete_phrase(found_components)
            )

        return PhraseValidationResult(phrase_present=False, exact_match=False)

    def _suggest_complete_phrase(self, found_components: List[str]) -> str:
        """Suggest a complete phrase based on found components."""
        if "VERIFACTU" in found_components:
            return "VERIFACTU"

        if "factura verificable" in found_components and "AEAT" in found_components:
            if "sede electrónica" in found_components:
                return "Factura verificable en la sede electrónica de la AEAT"
            else:
                return "Factura verificable AEAT"

        return self._get_default_phrase_suggestion()

    def _get_default_phrase_suggestion(self) -> str:
        """Get the default phrase suggestion for missing phrases."""
        return "VERIFACTU"

    def suggest_phrase_insertion(self, extracted_text: str, invoice_data: Dict[str, Any]) -> Optional[str]:
        """
        Suggest where and how to insert the mandatory phrase.

        Args:
            extracted_text: Current document text
            invoice_data: Parsed invoice data

        Returns:
            Suggested phrase insertion strategy
        """
        try:
            # Analyze document structure to suggest best insertion point
            lines = extracted_text.split('\n')

            # Look for good insertion points
            header_end_line = self._find_header_end(lines)
            footer_start_line = self._find_footer_start(lines)

            # Suggest insertion in footer (most common)
            if footer_start_line is not None:
                return f"Insertar 'VERIFACTU' en el pie de página (línea {footer_start_line + 1})"

            # Suggest insertion at end of document
            return "Insertar 'VERIFACTU' al final del documento"

        except Exception as e:
            logger.error(f"Error suggesting phrase insertion: {e}")
            return "Insertar 'VERIFACTU' en el documento"

    def _find_header_end(self, lines: List[str]) -> Optional[int]:
        """Find where the document header likely ends."""
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            if any(keyword in line.lower() for keyword in
                  ['factura', 'invoice', 'fecha', 'date', 'número', 'number']):
                return i
        return None

    def _find_footer_start(self, lines: List[str]) -> Optional[int]:
        """Find where the document footer likely starts."""
        for i, line in enumerate(reversed(lines[-10:])):  # Check last 10 lines
            if any(keyword in line.lower() for keyword in
                  ['total', 'subtotal', 'iva', 'tax', 'condiciones', 'terms']):
                return len(lines) - 10 + (9 - i)
        return None

    def validate_phrase_quality(self, phrase: str) -> Dict[str, Any]:
        """
        Validate the quality of a VERIFACTU phrase.

        Args:
            phrase: The phrase to validate

        Returns:
            Quality assessment with suggestions
        """
        normalized_phrase = self._normalize_text(phrase)

        # Check against known good phrases
        quality_score = 0.0
        issues = []
        suggestions = []

        # Exact match with mandatory phrases
        for mandatory in self.mandatory_phrases:
            if self._normalize_text(mandatory) == normalized_phrase:
                quality_score = 100.0
                break

        if quality_score < 100.0:
            # Check for partial matches
            best_match_score = 0.0
            best_match_phrase = None

            for mandatory in self.mandatory_phrases:
                score = SequenceMatcher(None, normalized_phrase,
                                      self._normalize_text(mandatory)).ratio() * 100

                if score > best_match_score:
                    best_match_score = score
                    best_match_phrase = mandatory

            quality_score = best_match_score

            if quality_score < 90:
                issues.append("Frase no coincide exactamente con las frases obligatorias")
                suggestions.append(f"Usar: {best_match_phrase}")

        # Check for common issues
        if not re.search(r'\bverifactu\b|\baeat\b', normalized_phrase):
            issues.append("Falta referencia a VERIFACTU o AEAT")
            suggestions.append("Incluir 'VERIFACTU' o 'AEAT'")

        return {
            'quality_score': quality_score,
            'issues': issues,
            'suggestions': suggestions,
            'best_match': best_match_phrase if quality_score < 100 else phrase
        }