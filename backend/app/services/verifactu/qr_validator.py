# Copyright 2024 Artificial Intelligence Labs, SL

import re
import cv2
import base64
import numpy as np
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs
from loguru import logger

try:
    from pyzbar import pyzbar
    from pyzbar.pyzbar import ZBarSymbol
    QR_AVAILABLE = True
except ImportError:
    logger.warning("pyzbar not available - QR detection will be limited")
    QR_AVAILABLE = False

from app.services.verifactu.models import QRValidationResult


class QRValidator:
    """
    VERIFACTU QR Code Detection and Validation System.

    Validates QR codes according to VERIFACTU technical specifications:
    - Detects presence of QR codes in invoice documents
    - Validates QR content against AEAT URL structure
    - Verifies QR data matches invoice information
    """

    def __init__(self):
        self.verifactu_url_patterns = [
            r'https://sede\.agenciatributaria\.gob\.es/Sede/verificafactura',
            r'https://www2\.agenciatributaria\.gob\.es/wlpl/BUCV-JDIT/VerificaFactura',
            r'https://.*\.aeat\.es/.*verifactu.*',
            r'https://.*\.agenciatributaria\.gob\.es/.*verifica.*'
        ]

        # Required QR parameters for VERIFACTU
        self.required_qr_params = {
            'nif': 'NIF del emisor',
            'num': 'Número de factura',
            'fecha': 'Fecha de factura',
            'importe': 'Importe total'
        }

    def validate_qr_in_invoice(self, document_bytes: bytes, invoice_data: Dict[str, Any]) -> QRValidationResult:
        """
        Main QR validation method for VERIFACTU compliance.

        Args:
            document_bytes: PDF document bytes
            invoice_data: Parsed invoice data for comparison

        Returns:
            QRValidationResult with complete validation status
        """
        result = QRValidationResult(qr_present=False)

        try:
            # Step 1: Detect QR codes in document
            qr_codes = self._detect_qr_codes(document_bytes)

            if not qr_codes:
                result.errors.append("No se detectó código QR en la factura")
                logger.warning("No QR code detected in invoice document")
                return result

            result.qr_present = True
            logger.info(f"Detected {len(qr_codes)} QR code(s) in document")

            # Step 2: Validate each QR code found
            for i, qr_data in enumerate(qr_codes):
                logger.info(f"Validating QR code {i+1}: {qr_data[:100]}...")

                qr_result = self._validate_single_qr(qr_data, invoice_data)

                # Use the best QR validation result
                if qr_result.aeat_url_valid and qr_result.invoice_data_match:
                    result.qr_readable = True
                    result.qr_data = qr_data
                    result.aeat_url_valid = qr_result.aeat_url_valid
                    result.invoice_data_match = qr_result.invoice_data_match
                    logger.info("Found valid VERIFACTU QR code")
                    return result
                elif qr_result.aeat_url_valid:
                    # Keep this as backup if no perfect match found
                    result.qr_readable = True
                    result.qr_data = qr_data
                    result.aeat_url_valid = True
                    result.errors.extend(qr_result.errors)

            # If we reach here, no fully valid QR was found
            if not result.aeat_url_valid:
                result.errors.append("QR detectado pero no contiene URL válida de AEAT")

            return result

        except Exception as e:
            logger.error(f"Error validating QR codes: {e}")
            result.errors.append(f"Error en validación de QR: {str(e)}")
            return result

    def _detect_qr_codes(self, document_bytes: bytes) -> List[str]:
        """Detect and decode QR codes from PDF document."""
        if not QR_AVAILABLE:
            logger.warning("QR detection unavailable - pyzbar not installed")
            return []

        try:
            # Convert PDF to images for QR detection
            from pdf2image import convert_from_bytes

            images = convert_from_bytes(document_bytes, dpi=300, first_page=1, last_page=3)
            qr_codes = []

            for i, image in enumerate(images):
                logger.debug(f"Scanning page {i+1} for QR codes")

                # Convert PIL image to OpenCV format
                cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

                # Detect QR codes using pyzbar
                decoded_objects = pyzbar.decode(cv_image, symbols=[ZBarSymbol.QRCODE])

                for obj in decoded_objects:
                    qr_data = obj.data.decode('utf-8')
                    qr_codes.append(qr_data)
                    logger.info(f"QR code detected on page {i+1}")

            return qr_codes

        except Exception as e:
            logger.error(f"Error detecting QR codes: {e}")
            return []

    def _validate_single_qr(self, qr_data: str, invoice_data: Dict[str, Any]) -> QRValidationResult:
        """Validate a single QR code against VERIFACTU requirements."""
        result = QRValidationResult(
            qr_present=True,
            qr_readable=True,
            qr_data=qr_data
        )

        try:
            # Step 1: Validate URL structure
            if self._is_valid_aeat_url(qr_data):
                result.aeat_url_valid = True
                logger.debug("QR contains valid AEAT URL structure")
            else:
                result.errors.append("QR no contiene URL válida de AEAT/VERIFACTU")
                return result

            # Step 2: Extract and validate parameters
            qr_params = self._extract_qr_parameters(qr_data)

            if not qr_params:
                result.errors.append("No se pudieron extraer parámetros del QR")
                return result

            # Step 3: Compare with invoice data
            match_errors = self._compare_qr_with_invoice(qr_params, invoice_data)

            if not match_errors:
                result.invoice_data_match = True
                logger.info("QR data matches invoice information")
            else:
                result.errors.extend(match_errors)
                logger.warning(f"QR data mismatch: {', '.join(match_errors)}")

            return result

        except Exception as e:
            logger.error(f"Error validating QR: {e}")
            result.errors.append(f"Error validando QR: {str(e)}")
            return result

    def _is_valid_aeat_url(self, qr_data: str) -> bool:
        """Check if QR contains valid AEAT/VERIFACTU URL."""
        for pattern in self.verifactu_url_patterns:
            if re.search(pattern, qr_data, re.IGNORECASE):
                return True
        return False

    def _extract_qr_parameters(self, qr_data: str) -> Optional[Dict[str, str]]:
        """Extract parameters from VERIFACTU QR URL."""
        try:
            parsed_url = urlparse(qr_data)
            params = parse_qs(parsed_url.query)

            # Convert list values to single strings
            clean_params = {}
            for key, value_list in params.items():
                if value_list:
                    clean_params[key.lower()] = value_list[0]

            return clean_params

        except Exception as e:
            logger.error(f"Error extracting QR parameters: {e}")
            return None

    def _compare_qr_with_invoice(self, qr_params: Dict[str, str], invoice_data: Dict[str, Any]) -> List[str]:
        """Compare QR parameters with actual invoice data."""
        errors = []

        try:
            # Extract invoice values for comparison
            invoice_nif = self._extract_invoice_nif(invoice_data)
            invoice_number = self._extract_invoice_number(invoice_data)
            invoice_date = self._extract_invoice_date(invoice_data)
            invoice_total = self._extract_invoice_total(invoice_data)

            # Validate NIF match
            if 'nif' in qr_params and invoice_nif:
                if not self._compare_nif(qr_params['nif'], invoice_nif):
                    errors.append(f"NIF en QR ({qr_params['nif']}) no coincide con factura ({invoice_nif})")

            # Validate invoice number match
            if 'num' in qr_params and invoice_number:
                if not self._compare_invoice_number(qr_params['num'], invoice_number):
                    errors.append(f"Número de factura en QR ({qr_params['num']}) no coincide con factura ({invoice_number})")

            # Validate date match
            if 'fecha' in qr_params and invoice_date:
                if not self._compare_date(qr_params['fecha'], invoice_date):
                    errors.append(f"Fecha en QR ({qr_params['fecha']}) no coincide con factura ({invoice_date})")

            # Validate total amount match
            if 'importe' in qr_params and invoice_total:
                if not self._compare_amount(qr_params['importe'], invoice_total):
                    errors.append(f"Importe en QR ({qr_params['importe']}) no coincide con factura ({invoice_total})")

            return errors

        except Exception as e:
            logger.error(f"Error comparing QR with invoice: {e}")
            return [f"Error comparando datos: {str(e)}"]

    def _extract_invoice_nif(self, invoice_data: Dict[str, Any]) -> Optional[str]:
        """Extract NIF from invoice data."""
        try:
            if 'parties' in invoice_data and 'vendor' in invoice_data['parties']:
                return invoice_data['parties']['vendor'].get('tax_id')
        except:
            pass
        return None

    def _extract_invoice_number(self, invoice_data: Dict[str, Any]) -> Optional[str]:
        """Extract invoice number from invoice data."""
        try:
            if 'metadata' in invoice_data:
                return invoice_data['metadata'].get('invoice_number')
        except:
            pass
        return None

    def _extract_invoice_date(self, invoice_data: Dict[str, Any]) -> Optional[str]:
        """Extract invoice date from invoice data."""
        try:
            if 'metadata' in invoice_data:
                return invoice_data['metadata'].get('issue_date')
        except:
            pass
        return None

    def _extract_invoice_total(self, invoice_data: Dict[str, Any]) -> Optional[float]:
        """Extract total amount from invoice data."""
        try:
            if 'financial_details' in invoice_data:
                return invoice_data['financial_details'].get('total_amount')
        except:
            pass
        return None

    def _compare_nif(self, qr_nif: str, invoice_nif: str) -> bool:
        """Compare NIF values with normalization."""
        if not qr_nif or not invoice_nif:
            return False

        # Normalize NIFs (remove spaces, convert to uppercase)
        qr_nif_clean = re.sub(r'\s+', '', qr_nif.upper())
        invoice_nif_clean = re.sub(r'\s+', '', invoice_nif.upper())

        return qr_nif_clean == invoice_nif_clean

    def _compare_invoice_number(self, qr_num: str, invoice_num: str) -> bool:
        """Compare invoice numbers with normalization."""
        if not qr_num or not invoice_num:
            return False

        # Normalize numbers (remove spaces and special chars)
        qr_num_clean = re.sub(r'[^\w]', '', qr_num)
        invoice_num_clean = re.sub(r'[^\w]', '', invoice_num)

        return qr_num_clean == invoice_num_clean

    def _compare_date(self, qr_date: str, invoice_date: str) -> bool:
        """Compare dates with flexible formatting."""
        if not qr_date or not invoice_date:
            return False

        try:
            from datetime import datetime

            # Try multiple date formats
            date_formats = [
                '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d',
                '%d.%m.%Y', '%Y.%m.%d', '%Y%m%d'
            ]

            qr_date_obj = None
            invoice_date_obj = None

            # Parse QR date
            for fmt in date_formats:
                try:
                    qr_date_obj = datetime.strptime(qr_date, fmt)
                    break
                except ValueError:
                    continue

            # Parse invoice date
            for fmt in date_formats:
                try:
                    invoice_date_obj = datetime.strptime(invoice_date, fmt)
                    break
                except ValueError:
                    continue

            if qr_date_obj and invoice_date_obj:
                return qr_date_obj.date() == invoice_date_obj.date()

        except Exception as e:
            logger.warning(f"Date comparison failed: {e}")

        return False

    def _compare_amount(self, qr_amount: str, invoice_amount: float) -> bool:
        """Compare amounts with tolerance."""
        if not qr_amount or invoice_amount is None:
            return False

        try:
            # Parse QR amount (handle different decimal separators)
            qr_amount_clean = qr_amount.replace(',', '.')
            qr_amount_float = float(qr_amount_clean)

            # Compare with small tolerance
            tolerance = 0.01
            return abs(qr_amount_float - invoice_amount) <= tolerance

        except (ValueError, TypeError) as e:
            logger.warning(f"Amount comparison failed: {e}")
            return False

    def generate_missing_qr_suggestion(self, invoice_data: Dict[str, Any]) -> Optional[str]:
        """Generate QR code URL suggestion for missing QR."""
        try:
            nif = self._extract_invoice_nif(invoice_data)
            number = self._extract_invoice_number(invoice_data)
            date = self._extract_invoice_date(invoice_data)
            total = self._extract_invoice_total(invoice_data)

            if not all([nif, number, date, total]):
                return None

            # Format date for QR
            formatted_date = self._format_date_for_qr(date)

            # Generate VERIFACTU QR URL
            qr_url = (
                f"https://sede.agenciatributaria.gob.es/Sede/verificafactura?"
                f"nif={nif}&num={number}&fecha={formatted_date}&importe={total:.2f}"
            )

            return qr_url

        except Exception as e:
            logger.error(f"Error generating QR suggestion: {e}")
            return None

    def _format_date_for_qr(self, date_str: str) -> str:
        """Format date for QR code (YYYY-MM-DD)."""
        try:
            from datetime import datetime

            # Try to parse and reformat
            date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']

            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            # If parsing fails, return as-is
            return date_str

        except Exception:
            return date_str