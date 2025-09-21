# Copyright 2024 Artificial Intelligence Labs, SL

import re
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from app.services.verifactu.models import VerifactuFormatResult


class FormatValidator:
    """
    VERIFACTU Format Validation System.

    Validates invoice data structure according to official VERIFACTU technical
    specifications from the Spanish Tax Agency (AEAT).
    """

    def __init__(self):
        # Required fields according to VERIFACTU specifications (2026)
        self.required_fields = {
            'issuer_data': {
                'nif': 'NIF del emisor',
                'name': 'Nombre o razón social del emisor',
                'address': 'Dirección del emisor'
            },
            'invoice_data': {
                'number': 'Número de factura',
                'issue_date': 'Fecha de emisión',
                'total_amount': 'Importe total'
            },
            'tax_data': {
                'tax_amount': 'Importe de IVA',
                'tax_rate': 'Tipo de IVA aplicado',
                'subtotal': 'Base imponible'
            },
            'verifactu_specific': {
                'hash': 'Hash criptográfico VERIFACTU',
                'registry_number': 'Número de registro',
                'chain_code': 'Código de encadenamiento'
            }
        }

        # VERIFACTU specific identifiers format validation
        self.identifier_patterns = {
            'verifactu_code': r'^[A-Z0-9]{8,16}$',  # VERIFACTU unique code
            'hash_verifactu': r'^[A-Fa-f0-9]{64}$',  # SHA256 hash
            'qr_code_id': r'^QR[A-Z0-9]{10,}$'  # QR identifier
        }

        # Valid tax rates for Spain (2024)
        self.valid_tax_rates = [0, 4, 10, 21]  # Standard Spanish VAT rates

    def validate_verifactu_format(self, invoice_data: Dict[str, Any]) -> VerifactuFormatResult:
        """
        Main VERIFACTU format validation method.

        Args:
            invoice_data: Parsed invoice data to validate

        Returns:
            VerifactuFormatResult with complete validation status
        """
        logger.info("Validating VERIFACTU format compliance")

        result = VerifactuFormatResult(has_required_fields=False)

        try:
            # Step 1: Validate required fields presence
            missing_fields = self._check_required_fields(invoice_data)
            result.missing_fields = missing_fields
            result.has_required_fields = len(missing_fields) == 0

            # Step 2: Validate field formats and values
            invalid_fields = self._validate_field_formats(invoice_data)
            result.invalid_fields = invalid_fields

            # Step 3: Validate VERIFACTU specific identifiers
            result.valid_identifiers = self._validate_identifiers(invoice_data)

            # Step 4: Validate data structure consistency
            result.structure_valid = self._validate_structure_consistency(invoice_data)

            # Step 5: Validate cryptographic hash if present
            result.hash_valid = self._validate_verifactu_hash(invoice_data)

            # Overall validation
            result.has_required_fields = len(result.missing_fields) == 0
            field_validation_passed = len(result.invalid_fields) == 0

            logger.info(
                f"VERIFACTU format validation - "
                f"Required fields: {result.has_required_fields}, "
                f"Valid identifiers: {result.valid_identifiers}, "
                f"Structure valid: {result.structure_valid}, "
                f"Field formats: {field_validation_passed}"
            )

            return result

        except Exception as e:
            logger.error(f"Error validating VERIFACTU format: {e}")
            result.invalid_fields.append(f"Error de validación: {str(e)}")
            return result

    def _check_required_fields(self, invoice_data: Dict[str, Any]) -> List[str]:
        """Check for presence of all required VERIFACTU fields."""
        missing_fields = []

        try:
            # Check issuer data
            issuer_missing = self._check_issuer_fields(invoice_data)
            missing_fields.extend(issuer_missing)

            # Check invoice metadata
            invoice_missing = self._check_invoice_fields(invoice_data)
            missing_fields.extend(invoice_missing)

            # Check tax/financial data
            tax_missing = self._check_tax_fields(invoice_data)
            missing_fields.extend(tax_missing)

            return missing_fields

        except Exception as e:
            logger.error(f"Error checking required fields: {e}")
            return [f"Error verificando campos: {str(e)}"]

    def _check_issuer_fields(self, invoice_data: Dict[str, Any]) -> List[str]:
        """Check issuer-related required fields."""
        missing = []

        try:
            parties = invoice_data.get('parties', {})
            vendor = parties.get('vendor', {})

            if not vendor.get('tax_id'):
                missing.append("NIF del emisor")

            if not vendor.get('name'):
                missing.append("Nombre del emisor")

            if not vendor.get('address'):
                missing.append("Dirección del emisor")

        except Exception as e:
            missing.append(f"Error datos emisor: {str(e)}")

        return missing

    def _check_invoice_fields(self, invoice_data: Dict[str, Any]) -> List[str]:
        """Check invoice metadata required fields."""
        missing = []

        try:
            metadata = invoice_data.get('metadata', {})

            if not metadata.get('invoice_number'):
                missing.append("Número de factura")

            if not metadata.get('issue_date'):
                missing.append("Fecha de emisión")

        except Exception as e:
            missing.append(f"Error metadatos factura: {str(e)}")

        return missing

    def _check_tax_fields(self, invoice_data: Dict[str, Any]) -> List[str]:
        """Check tax and financial required fields."""
        missing = []

        try:
            financial = invoice_data.get('financial_details', {})

            if financial.get('total_amount') is None:
                missing.append("Importe total")

            if financial.get('subtotal') is None:
                missing.append("Base imponible")

            tax = financial.get('tax', {})
            if tax.get('amount') is None:
                missing.append("Importe de IVA")

            if tax.get('rate') is None:
                missing.append("Tipo de IVA")

        except Exception as e:
            missing.append(f"Error datos fiscales: {str(e)}")

        return missing

    def _validate_field_formats(self, invoice_data: Dict[str, Any]) -> List[str]:
        """Validate format of fields according to VERIFACTU specifications."""
        invalid_fields = []

        try:
            # Validate NIF format
            nif_error = self._validate_nif_format(invoice_data)
            if nif_error:
                invalid_fields.append(nif_error)

            # Validate date formats
            date_errors = self._validate_date_formats(invoice_data)
            invalid_fields.extend(date_errors)

            # Validate tax rates
            tax_errors = self._validate_tax_rates(invoice_data)
            invalid_fields.extend(tax_errors)

            # Validate amounts
            amount_errors = self._validate_amounts(invoice_data)
            invalid_fields.extend(amount_errors)

            # Validate invoice number format
            number_error = self._validate_invoice_number_format(invoice_data)
            if number_error:
                invalid_fields.append(number_error)

        except Exception as e:
            invalid_fields.append(f"Error validando formatos: {str(e)}")

        return invalid_fields

    def _validate_nif_format(self, invoice_data: Dict[str, Any]) -> Optional[str]:
        """Validate Spanish NIF/CIF format."""
        try:
            from app.services.validation.spain_validators import SpanishTaxIDValidator

            vendor = invoice_data.get('parties', {}).get('vendor', {})
            tax_id = vendor.get('tax_id')

            if not tax_id:
                return None  # Missing field already reported

            validator = SpanishTaxIDValidator()
            is_valid, _ = validator.validate_tax_id(tax_id)

            if not is_valid:
                return f"NIF/CIF inválido: {tax_id}"

        except Exception as e:
            return f"Error validando NIF: {str(e)}"

        return None

    def _validate_date_formats(self, invoice_data: Dict[str, Any]) -> List[str]:
        """Validate date field formats."""
        errors = []

        try:
            metadata = invoice_data.get('metadata', {})

            # Validate issue date
            issue_date = metadata.get('issue_date')
            if issue_date and not self._is_valid_date_format(issue_date):
                errors.append(f"Formato de fecha inválido: {issue_date}")

            # Validate due date if present
            due_date = metadata.get('due_date')
            if due_date and not self._is_valid_date_format(due_date):
                errors.append(f"Formato de fecha vencimiento inválido: {due_date}")

        except Exception as e:
            errors.append(f"Error validando fechas: {str(e)}")

        return errors

    def _is_valid_date_format(self, date_str: str) -> bool:
        """Check if date string is in valid format."""
        date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']

        for fmt in date_formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue

        return False

    def _validate_tax_rates(self, invoice_data: Dict[str, Any]) -> List[str]:
        """Validate tax rates are within Spanish standards."""
        errors = []

        try:
            financial = invoice_data.get('financial_details', {})
            tax = financial.get('tax', {})
            tax_rate = tax.get('rate')

            if tax_rate is not None:
                if tax_rate not in self.valid_tax_rates:
                    errors.append(
                        f"Tipo de IVA no estándar: {tax_rate}% "
                        f"(válidos: {', '.join(map(str, self.valid_tax_rates))}%)"
                    )

        except Exception as e:
            errors.append(f"Error validando tipos de IVA: {str(e)}")

        return errors

    def _validate_amounts(self, invoice_data: Dict[str, Any]) -> List[str]:
        """Validate amount fields for mathematical consistency."""
        errors = []

        try:
            financial = invoice_data.get('financial_details', {})

            subtotal = financial.get('subtotal', 0)
            tax_amount = financial.get('tax', {}).get('amount', 0)
            total = financial.get('total_amount', 0)

            # Check mathematical consistency
            expected_total = subtotal + tax_amount
            tolerance = 0.02

            if abs(expected_total - total) > tolerance:
                errors.append(
                    f"Inconsistencia matemática: "
                    f"Subtotal ({subtotal}) + IVA ({tax_amount}) = {expected_total} "
                    f"≠ Total ({total})"
                )

            # Check for negative amounts
            if subtotal < 0:
                errors.append(f"Base imponible negativa: {subtotal}")

            if tax_amount < 0:
                errors.append(f"Importe de IVA negativo: {tax_amount}")

            if total < 0:
                errors.append(f"Importe total negativo: {total}")

        except Exception as e:
            errors.append(f"Error validando importes: {str(e)}")

        return errors

    def _validate_invoice_number_format(self, invoice_data: Dict[str, Any]) -> Optional[str]:
        """Validate invoice number format requirements."""
        try:
            metadata = invoice_data.get('metadata', {})
            invoice_number = metadata.get('invoice_number')

            if not invoice_number:
                return None  # Missing field already reported

            # Check minimum length (VERIFACTU requirement)
            if len(invoice_number.strip()) < 1:
                return "Número de factura vacío"

            # Check for valid characters (alphanumeric and basic symbols)
            if not re.match(r'^[A-Za-z0-9\-_/]+$', invoice_number):
                return f"Número de factura contiene caracteres inválidos: {invoice_number}"

        except Exception as e:
            return f"Error validando número de factura: {str(e)}"

        return None

    def _validate_identifiers(self, invoice_data: Dict[str, Any]) -> bool:
        """Validate VERIFACTU specific identifier formats."""
        try:
            # Check for VERIFACTU code if present
            verifactu_code = invoice_data.get('verifactu_code')
            if verifactu_code:
                if not re.match(self.identifier_patterns['verifactu_code'], verifactu_code):
                    logger.warning(f"Invalid VERIFACTU code format: {verifactu_code}")
                    return False

            # Check for hash if present
            verifactu_hash = invoice_data.get('verifactu_hash')
            if verifactu_hash:
                if not re.match(self.identifier_patterns['hash_verifactu'], verifactu_hash):
                    logger.warning(f"Invalid VERIFACTU hash format: {verifactu_hash}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Error validating identifiers: {e}")
            return False

    def _validate_structure_consistency(self, invoice_data: Dict[str, Any]) -> bool:
        """Validate overall data structure consistency."""
        try:
            # Check that line items sum matches financial totals
            items = invoice_data.get('items', [])
            if items:
                items_total = sum(item.get('line_total', 0) for item in items)
                subtotal = invoice_data.get('financial_details', {}).get('subtotal', 0)

                tolerance = 0.02
                if abs(items_total - subtotal) > tolerance:
                    logger.warning(f"Line items total ({items_total}) doesn't match subtotal ({subtotal})")
                    return False

            # Check customer/vendor data consistency
            parties = invoice_data.get('parties', {})
            if not parties.get('vendor') or not parties.get('customer'):
                logger.warning("Missing vendor or customer information")
                return False

            # Check date consistency
            metadata = invoice_data.get('metadata', {})
            issue_date = metadata.get('issue_date')
            due_date = metadata.get('due_date')

            if issue_date and due_date:
                try:
                    issue_dt = datetime.strptime(issue_date, '%Y-%m-%d')
                    due_dt = datetime.strptime(due_date, '%Y-%m-%d')

                    if due_dt < issue_dt:
                        logger.warning(f"Due date ({due_date}) before issue date ({issue_date})")
                        return False
                except ValueError:
                    # Date format validation handled elsewhere
                    pass

            return True

        except Exception as e:
            logger.error(f"Error validating structure consistency: {e}")
            return False

    def _validate_verifactu_hash(self, invoice_data: Dict[str, Any]) -> bool:
        """Validate VERIFACTU cryptographic hash if present."""
        try:
            verifactu_hash = invoice_data.get('verifactu_hash')

            if not verifactu_hash:
                # Hash is optional, so no hash is valid
                return True

            # Validate hash format
            if not re.match(self.identifier_patterns['hash_verifactu'], verifactu_hash):
                logger.warning(f"Invalid hash format: {verifactu_hash}")
                return False

            # Calculate expected hash (simplified version)
            calculated_hash = self._calculate_invoice_hash(invoice_data)

            if calculated_hash and calculated_hash.upper() != verifactu_hash.upper():
                logger.warning("VERIFACTU hash doesn't match calculated value")
                return False

            logger.info("VERIFACTU hash validated successfully")
            return True

        except Exception as e:
            logger.error(f"Error validating VERIFACTU hash: {e}")
            return False

    def _calculate_invoice_hash(self, invoice_data: Dict[str, Any]) -> Optional[str]:
        """Calculate expected VERIFACTU hash for invoice data."""
        try:
            # Simplified hash calculation for validation
            # In real VERIFACTU, this would follow exact official algorithm

            hash_components = []

            # Add core invoice components to hash
            metadata = invoice_data.get('metadata', {})
            if metadata.get('invoice_number'):
                hash_components.append(metadata['invoice_number'])

            if metadata.get('issue_date'):
                hash_components.append(metadata['issue_date'])

            vendor = invoice_data.get('parties', {}).get('vendor', {})
            if vendor.get('tax_id'):
                hash_components.append(vendor['tax_id'])

            financial = invoice_data.get('financial_details', {})
            if financial.get('total_amount') is not None:
                hash_components.append(str(financial['total_amount']))

            # Create hash string
            hash_string = '|'.join(hash_components)

            # Calculate SHA256 hash
            return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()

        except Exception as e:
            logger.error(f"Error calculating invoice hash: {e}")
            return None

    def generate_verifactu_compliance_report(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive VERIFACTU compliance report."""
        validation_result = self.validate_verifactu_format(invoice_data)

        compliance_score = 0
        max_score = 100

        # Score based on validation results
        if validation_result.has_required_fields:
            compliance_score += 40

        if validation_result.valid_identifiers:
            compliance_score += 20

        if validation_result.structure_valid:
            compliance_score += 20

        if validation_result.hash_valid:
            compliance_score += 10

        if len(validation_result.invalid_fields) == 0:
            compliance_score += 10

        # Generate recommendations
        recommendations = []

        if not validation_result.has_required_fields:
            recommendations.append("Completar campos obligatorios faltantes")

        if not validation_result.valid_identifiers:
            recommendations.append("Corregir formato de identificadores VERIFACTU")

        if not validation_result.structure_valid:
            recommendations.append("Revisar consistencia de datos")

        if validation_result.invalid_fields:
            recommendations.append("Corregir formato de campos inválidos")

        return {
            'compliance_score': compliance_score,
            'validation_result': validation_result,
            'recommendations': recommendations,
            'ready_for_verifactu': compliance_score >= 90
        }