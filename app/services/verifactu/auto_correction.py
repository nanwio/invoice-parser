# Copyright 2024 Artificial Intelligence Labs, SL

import qrcode
import base64
from io import BytesIO
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger

from app.services.verifactu.models import (
    VerifactuValidationResult,
    VerifactuCorrection,
    QRValidationResult,
    PhraseValidationResult
)


class VerifactuAutoCorrection:
    """
    VERIFACTU Automatic Correction System.

    Provides automated fixes for common VERIFACTU compliance issues:
    - Generate missing QR codes
    - Insert mandatory phrases
    - Correct data formats
    """

    def __init__(self):
        # QR code generation settings
        self.qr_settings = {
            'box_size': 10,
            'border': 4,
            'error_correction': qrcode.constants.ERROR_CORRECT_M
        }

        # Default phrases for insertion
        self.default_phrases = {
            'short': 'VERIFACTU',
            'full': 'Factura verificable en la sede electrónica de la AEAT'
        }

    async def apply_automatic_corrections(
        self,
        validation_result: VerifactuValidationResult,
        invoice_data: Dict[str, Any],
        document_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply automatic corrections based on validation results.

        Args:
            validation_result: VERIFACTU validation result
            invoice_data: Original invoice data
            document_text: Original document text (for phrase insertion)

        Returns:
            Dictionary with correction results and updated data
        """
        logger.info("Applying VERIFACTU automatic corrections")

        corrections_applied = []
        updated_invoice_data = invoice_data.copy()
        generated_assets = {}

        try:
            # 1. Generate missing QR code
            if self._needs_qr_correction(validation_result):
                qr_correction = await self._generate_qr_code(updated_invoice_data)
                if qr_correction:
                    corrections_applied.append(qr_correction)
                    generated_assets['qr_code'] = qr_correction

            # 2. Insert missing mandatory phrase
            if self._needs_phrase_correction(validation_result):
                phrase_correction = self._insert_mandatory_phrase(document_text, updated_invoice_data)
                if phrase_correction:
                    corrections_applied.append(phrase_correction)
                    generated_assets['verifactu_phrase'] = phrase_correction

            # 3. Format corrections
            format_corrections = self._apply_format_corrections(validation_result, updated_invoice_data)
            corrections_applied.extend(format_corrections)

            # 4. Generate corrected document suggestions
            document_suggestions = self._generate_document_suggestions(
                corrections_applied, document_text, updated_invoice_data
            )

            result = {
                'corrections_applied': len(corrections_applied),
                'corrections': corrections_applied,
                'updated_invoice_data': updated_invoice_data,
                'generated_assets': generated_assets,
                'document_suggestions': document_suggestions,
                'success': True,
                'summary': self._generate_correction_summary(corrections_applied)
            }

            logger.info(f"Applied {len(corrections_applied)} automatic corrections")
            return result

        except Exception as e:
            logger.error(f"Error applying automatic corrections: {e}")
            return {
                'corrections_applied': 0,
                'corrections': [],
                'success': False,
                'error': str(e),
                'summary': f"Error en corrección automática: {str(e)}"
            }

    def _needs_qr_correction(self, validation_result: VerifactuValidationResult) -> bool:
        """Check if QR code correction is needed."""
        qr_validation = validation_result.qr_validation
        return (qr_validation and
                (not qr_validation.qr_present or
                 not qr_validation.aeat_url_valid or
                 not qr_validation.invoice_data_match))

    def _needs_phrase_correction(self, validation_result: VerifactuValidationResult) -> bool:
        """Check if phrase correction is needed."""
        phrase_validation = validation_result.phrase_validation
        return (phrase_validation and
                (not phrase_validation.phrase_present or
                 (not phrase_validation.exact_match and phrase_validation.confidence < 0.8)))

    async def _generate_qr_code(self, invoice_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate QR code for VERIFACTU compliance."""
        try:
            # Extract required data
            vendor = invoice_data.get('parties', {}).get('vendor', {})
            metadata = invoice_data.get('metadata', {})
            financial = invoice_data.get('financial_details', {})

            nif = vendor.get('tax_id')
            invoice_number = metadata.get('invoice_number')
            issue_date = metadata.get('issue_date')
            total_amount = financial.get('total_amount')

            if not all([nif, invoice_number, issue_date, total_amount]):
                logger.warning("Insufficient data for QR generation")
                return None

            # Format date for QR (YYYY-MM-DD format required)
            formatted_date = self._format_date_for_qr(issue_date)

            # Generate VERIFACTU QR URL
            qr_url = (
                f"https://sede.agenciatributaria.gob.es/Sede/verificafactura?"
                f"nif={nif}&num={invoice_number}&fecha={formatted_date}&importe={total_amount:.2f}"
            )

            # Generate QR code image
            qr = qrcode.QRCode(
                version=1,
                error_correction=self.qr_settings['error_correction'],
                box_size=self.qr_settings['box_size'],
                border=self.qr_settings['border']
            )

            qr.add_data(qr_url)
            qr.make(fit=True)

            # Create QR code image
            qr_image = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64 for embedding
            buffer = BytesIO()
            qr_image.save(buffer, format='PNG')
            qr_image_b64 = base64.b64encode(buffer.getvalue()).decode()

            logger.info(f"Generated QR code for invoice {invoice_number}")

            return {
                'type': 'qr_generation',
                'field': 'qr_code',
                'action': 'Generated missing QR code',
                'data': {
                    'qr_url': qr_url,
                    'qr_image_base64': qr_image_b64,
                    'qr_format': 'PNG',
                    'qr_size': f"{qr_image.size[0]}x{qr_image.size[1]}"
                },
                'confidence': 1.0,
                'success': True
            }

        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return {
                'type': 'qr_generation',
                'field': 'qr_code',
                'action': 'Failed to generate QR code',
                'success': False,
                'error': str(e)
            }

    def _insert_mandatory_phrase(self, document_text: Optional[str], invoice_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Insert mandatory VERIFACTU phrase."""
        try:
            # Choose appropriate phrase
            phrase_to_insert = self.default_phrases['short']  # 'VERIFACTU' is shortest and always valid

            # Determine best insertion point
            insertion_point = self._find_best_insertion_point(document_text)

            logger.info(f"Suggesting phrase insertion: '{phrase_to_insert}' at {insertion_point}")

            return {
                'type': 'phrase_insertion',
                'field': 'verifactu_phrase',
                'action': f"Insert mandatory phrase: {phrase_to_insert}",
                'data': {
                    'phrase': phrase_to_insert,
                    'insertion_point': insertion_point,
                    'alternative_phrases': list(self.default_phrases.values())
                },
                'confidence': 1.0,
                'success': True
            }

        except Exception as e:
            logger.error(f"Error inserting mandatory phrase: {e}")
            return {
                'type': 'phrase_insertion',
                'field': 'verifactu_phrase',
                'action': 'Failed to insert phrase',
                'success': False,
                'error': str(e)
            }

    def _find_best_insertion_point(self, document_text: Optional[str]) -> str:
        """Find the best place to insert the mandatory phrase."""
        if not document_text:
            return "footer"

        text_lower = document_text.lower()

        # Look for footer indicators
        footer_indicators = ['total', 'subtotal', 'iva', 'condiciones', 'terms']
        if any(indicator in text_lower for indicator in footer_indicators):
            return "footer"

        # Look for header end
        if any(indicator in text_lower for indicator in ['factura', 'invoice', 'fecha']):
            return "after_header"

        return "end_of_document"

    def _apply_format_corrections(self, validation_result: VerifactuValidationResult, invoice_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply format corrections to invoice data."""
        corrections = []

        try:
            format_validation = validation_result.format_validation
            if not format_validation:
                return corrections

            # Fix missing required fields
            if format_validation.missing_fields:
                for field in format_validation.missing_fields:
                    correction = self._fix_missing_field(field, invoice_data)
                    if correction:
                        corrections.append(correction)

            # Fix invalid field formats
            if format_validation.invalid_fields:
                for field_error in format_validation.invalid_fields:
                    correction = self._fix_invalid_field_format(field_error, invoice_data)
                    if correction:
                        corrections.append(correction)

            return corrections

        except Exception as e:
            logger.error(f"Error applying format corrections: {e}")
            return corrections

    def _fix_missing_field(self, field_name: str, invoice_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fix missing required field."""
        field_mapping = {
            'NIF del emisor': 'parties.vendor.tax_id',
            'Nombre del emisor': 'parties.vendor.name',
            'Dirección del emisor': 'parties.vendor.address',
            'Número de factura': 'metadata.invoice_number',
            'Fecha de emisión': 'metadata.issue_date',
            'Importe total': 'financial_details.total_amount',
            'Base imponible': 'financial_details.subtotal',
            'Importe de IVA': 'financial_details.tax.amount',
            'Tipo de IVA': 'financial_details.tax.rate'
        }

        field_path = field_mapping.get(field_name)
        if not field_path:
            return None

        # Generate placeholder or derived value
        suggested_value = self._generate_field_value(field_name, invoice_data)

        return {
            'type': 'field_completion',
            'field': field_name,
            'action': f"Complete missing field: {field_name}",
            'data': {
                'field_path': field_path,
                'suggested_value': suggested_value,
                'is_placeholder': True
            },
            'confidence': 0.5,  # Lower confidence for auto-generated values
            'success': True
        }

    def _generate_field_value(self, field_name: str, invoice_data: Dict[str, Any]) -> str:
        """Generate appropriate value for missing field."""
        if 'NIF' in field_name:
            return "PENDIENTE-NIF"
        elif 'Nombre' in field_name:
            return "PENDIENTE-NOMBRE"
        elif 'Dirección' in field_name:
            return "PENDIENTE-DIRECCIÓN"
        elif 'Número' in field_name:
            return "AUTO-001"
        elif 'Fecha' in field_name:
            from datetime import datetime
            return datetime.now().strftime('%Y-%m-%d')
        elif 'Importe' in field_name or 'total' in field_name.lower():
            return "0.00"
        elif 'IVA' in field_name and 'tipo' in field_name.lower():
            return "21"  # Standard Spanish VAT rate
        else:
            return "PENDIENTE"

    def _fix_invalid_field_format(self, field_error: str, invoice_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fix invalid field format."""
        # This would need more sophisticated parsing of field_error string
        # For now, just log the issue
        logger.info(f"Field format issue identified: {field_error}")

        return {
            'type': 'format_correction',
            'field': 'field_format',
            'action': f"Format correction needed: {field_error}",
            'data': {
                'error_description': field_error,
                'manual_review_needed': True
            },
            'confidence': 0.3,
            'success': False  # Requires manual review
        }

    def _format_date_for_qr(self, date_str: str) -> str:
        """Format date for QR code (YYYY-MM-DD)."""
        try:
            from datetime import datetime

            # Try to parse and reformat
            date_formats = ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d']

            for fmt in date_formats:
                try:
                    date_obj = datetime.strptime(date_str, fmt)
                    return date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            # If parsing fails, return as-is and hope for the best
            return date_str

        except Exception:
            return date_str

    def _generate_document_suggestions(
        self,
        corrections: List[Dict[str, Any]],
        document_text: Optional[str],
        invoice_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate suggestions for document modifications."""
        suggestions = {
            'document_modifications': [],
            'template_updates': [],
            'process_improvements': []
        }

        try:
            # Document modification suggestions
            for correction in corrections:
                if correction['type'] == 'qr_generation':
                    suggestions['document_modifications'].append({
                        'action': 'Add QR code to invoice footer',
                        'position': 'bottom-right',
                        'size': '2cm x 2cm',
                        'description': 'Embed generated QR code in PDF'
                    })

                elif correction['type'] == 'phrase_insertion':
                    phrase = correction['data']['phrase']
                    position = correction['data']['insertion_point']
                    suggestions['document_modifications'].append({
                        'action': f'Add text "{phrase}"',
                        'position': position,
                        'font_size': '10pt',
                        'description': f'Insert mandatory VERIFACTU phrase in {position}'
                    })

            # Template improvement suggestions
            if len(corrections) > 0:
                suggestions['template_updates'].append({
                    'recommendation': 'Update invoice template to include VERIFACTU elements by default',
                    'priority': 'HIGH',
                    'impact': 'Prevents future compliance issues'
                })

            # Process improvements
            if any(c['type'] == 'field_completion' for c in corrections):
                suggestions['process_improvements'].append({
                    'recommendation': 'Implement data validation in invoice generation process',
                    'priority': 'MEDIUM',
                    'impact': 'Reduces missing field errors'
                })

            return suggestions

        except Exception as e:
            logger.error(f"Error generating document suggestions: {e}")
            return suggestions

    def _generate_correction_summary(self, corrections: List[Dict[str, Any]]) -> str:
        """Generate human-readable summary of corrections."""
        if not corrections:
            return "No se aplicaron correcciones automáticas."

        summary_parts = []
        correction_counts = {}

        # Count correction types
        for correction in corrections:
            correction_type = correction['type']
            correction_counts[correction_type] = correction_counts.get(correction_type, 0) + 1

        # Generate summary text
        if correction_counts.get('qr_generation', 0) > 0:
            summary_parts.append(f"✅ Generado código QR VERIFACTU")

        if correction_counts.get('phrase_insertion', 0) > 0:
            summary_parts.append(f"✅ Sugerida inserción de frase obligatoria")

        if correction_counts.get('field_completion', 0) > 0:
            count = correction_counts['field_completion']
            summary_parts.append(f"⚠️  Identificados {count} campos faltantes para completar")

        if correction_counts.get('format_correction', 0) > 0:
            count = correction_counts['format_correction']
            summary_parts.append(f"🔧 Identificadas {count} correcciones de formato")

        total_corrections = len(corrections)
        successful_corrections = len([c for c in corrections if c.get('success', False)])

        summary = f"Correcciones automáticas: {successful_corrections}/{total_corrections} exitosas.\n"
        summary += "\n".join(summary_parts)

        return summary

    def generate_correction_report(self, corrections_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed correction report for review."""
        return {
            'timestamp': datetime.now().isoformat(),
            'corrections_summary': corrections_result.get('summary', ''),
            'total_corrections': corrections_result.get('corrections_applied', 0),
            'success_rate': self._calculate_success_rate(corrections_result.get('corrections', [])),
            'generated_assets': list(corrections_result.get('generated_assets', {}).keys()),
            'next_steps': self._generate_next_steps(corrections_result),
            'quality_score_improvement': self._estimate_quality_improvement(corrections_result)
        }

    def _calculate_success_rate(self, corrections: List[Dict[str, Any]]) -> float:
        """Calculate success rate of corrections."""
        if not corrections:
            return 0.0

        successful = len([c for c in corrections if c.get('success', False)])
        return (successful / len(corrections)) * 100

    def _generate_next_steps(self, corrections_result: Dict[str, Any]) -> List[str]:
        """Generate next steps based on correction results."""
        next_steps = []

        corrections = corrections_result.get('corrections', [])

        if any(c['type'] == 'qr_generation' and c.get('success') for c in corrections):
            next_steps.append("1. Descargar código QR generado e incorporar al documento")

        if any(c['type'] == 'phrase_insertion' for c in corrections):
            next_steps.append("2. Añadir frase VERIFACTU en la posición sugerida")

        if any(c['type'] == 'field_completion' for c in corrections):
            next_steps.append("3. Completar campos faltantes identificados")

        if not corrections_result.get('success', False):
            next_steps.append("⚠️  Revisar errores y corregir manualmente")

        next_steps.append("4. Volver a validar factura corregida")

        return next_steps

    def _estimate_quality_improvement(self, corrections_result: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate quality improvement from corrections."""
        corrections = corrections_result.get('corrections', [])
        successful_corrections = [c for c in corrections if c.get('success', False)]

        # Rough estimate of quality improvement
        estimated_improvement = len(successful_corrections) * 15  # ~15 points per correction

        return {
            'estimated_score_increase': min(estimated_improvement, 50),  # Cap at 50 points
            'new_estimated_score': min(100, 50 + estimated_improvement),  # Assuming starting score of 50
            'note': 'Estimación basada en correcciones aplicadas. Validación completa requerida.'
        }