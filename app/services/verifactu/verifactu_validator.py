# Copyright 2024 Artificial Intelligence Labs, SL

import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger

from app.services.verifactu.models import (
    VerifactuValidationResult,
    VerifactuComplianceLevel,
    VerifactuAlert,
    VerifactuCorrection,
    VerifactuDashboardStats
)
from app.services.verifactu.qr_validator import QRValidator
from app.services.verifactu.phrase_validator import PhraseValidator
from app.services.verifactu.format_validator import FormatValidator
from app.services.verifactu.aeat_integration import AEATIntegration


class VerifactuValidator:
    """
    Main VERIFACTU Compliance Validation System.

    Orchestrates all VERIFACTU validation components:
    - QR code detection and validation
    - Mandatory phrase verification
    - Format compliance checking
    - Real-time AEAT integration
    - Compliance scoring and alerts
    """

    def __init__(self):
        self.qr_validator = QRValidator()
        self.phrase_validator = PhraseValidator()
        self.format_validator = FormatValidator()
        self.aeat_integration = AEATIntegration()

        # Compliance scoring weights
        self.scoring_weights = {
            'qr_compliance': 30,  # QR code presence and validity
            'phrase_compliance': 20,  # Mandatory phrase
            'format_compliance': 25,  # Data format and structure
            'aeat_compliance': 25   # AEAT real-time validation
        }

    async def validate_complete_verifactu_compliance(
        self,
        document_bytes: bytes,
        invoice_data: Dict[str, Any],
        extracted_text: str,
        enable_aeat_validation: bool = True
    ) -> VerifactuValidationResult:
        """
        Perform complete VERIFACTU compliance validation.

        Args:
            document_bytes: PDF document bytes for QR detection
            invoice_data: Parsed invoice data
            extracted_text: OCR extracted text
            enable_aeat_validation: Whether to perform real-time AEAT validation

        Returns:
            Complete VERIFACTU validation result with scoring and recommendations
        """
        logger.info("Starting complete VERIFACTU compliance validation")

        try:
            # Run all validations in parallel for performance
            validation_tasks = [
                self._validate_qr_compliance(document_bytes, invoice_data),
                self._validate_phrase_compliance(extracted_text),
                self._validate_format_compliance(invoice_data)
            ]

            if enable_aeat_validation:
                validation_tasks.append(self._validate_aeat_compliance(invoice_data))

            # Execute all validations
            results = await asyncio.gather(*validation_tasks, return_exceptions=True)

            # Extract results (handle exceptions)
            qr_result = results[0] if not isinstance(results[0], Exception) else None
            phrase_result = results[1] if not isinstance(results[1], Exception) else None
            format_result = results[2] if not isinstance(results[2], Exception) else None
            aeat_result = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else None

            # Handle any validation failures
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Validation {i} failed: {result}")

            # Calculate compliance score and level
            compliance_score = self._calculate_compliance_score(
                qr_result, phrase_result, format_result, aeat_result
            )

            compliance_level = self._determine_compliance_level(compliance_score)

            # Generate alerts
            alerts = self._generate_compliance_alerts(
                qr_result, phrase_result, format_result, aeat_result
            )

            # Check if auto-correction is possible
            auto_corrections = self._identify_auto_corrections(
                qr_result, phrase_result, format_result, invoice_data
            )

            # Build final result
            result = VerifactuValidationResult(
                compliance_level=compliance_level,
                compliance_score=compliance_score,
                qr_validation=qr_result,
                phrase_validation=phrase_result,
                format_validation=format_result,
                aeat_validation=aeat_result,
                alerts=alerts,
                verifactu_ready=compliance_score >= 85,
                critical_issues=len([a for a in alerts if a.level == "critical"]),
                warnings=len([a for a in alerts if a.level == "medium"]),
                can_auto_correct=len(auto_corrections) > 0,
                correction_suggestions=[c.suggested_value for c in auto_corrections]
            )

            logger.info(
                f"VERIFACTU validation completed - "
                f"Score: {compliance_score:.1f}/100, "
                f"Level: {compliance_level}, "
                f"Ready: {result.verifactu_ready}"
            )

            return result

        except Exception as e:
            logger.error(f"Error in complete VERIFACTU validation: {e}")
            # Return error result
            return VerifactuValidationResult(
                compliance_level=VerifactuComplianceLevel.NON_COMPLIANT,
                compliance_score=0.0,
                qr_validation=None,
                phrase_validation=None,
                format_validation=None,
                aeat_validation=None,
                alerts=[VerifactuAlert(
                    level="critical",
                    message=f"Error en validación VERIFACTU: {str(e)}",
                    suggestion="Revisar documento y volver a intentar"
                )],
                verifactu_ready=False,
                critical_issues=1,
                warnings=0,
                can_auto_correct=False,
                correction_suggestions=[]
            )

    async def _validate_qr_compliance(self, document_bytes: bytes, invoice_data: Dict[str, Any]):
        """Validate QR code compliance."""
        try:
            return self.qr_validator.validate_qr_in_invoice(document_bytes, invoice_data)
        except Exception as e:
            logger.error(f"QR validation failed: {e}")
            return None

    async def _validate_phrase_compliance(self, extracted_text: str):
        """Validate mandatory phrase compliance."""
        try:
            return self.phrase_validator.validate_mandatory_phrase(extracted_text)
        except Exception as e:
            logger.error(f"Phrase validation failed: {e}")
            return None

    async def _validate_format_compliance(self, invoice_data: Dict[str, Any]):
        """Validate format compliance."""
        try:
            return self.format_validator.validate_verifactu_format(invoice_data)
        except Exception as e:
            logger.error(f"Format validation failed: {e}")
            return None

    async def _validate_aeat_compliance(self, invoice_data: Dict[str, Any]):
        """Validate AEAT compliance."""
        try:
            # Extract required data for AEAT validation
            vendor = invoice_data.get('parties', {}).get('vendor', {})
            metadata = invoice_data.get('metadata', {})
            financial = invoice_data.get('financial_details', {})

            nif = vendor.get('tax_id')
            invoice_number = metadata.get('invoice_number')
            issue_date = metadata.get('issue_date')
            total_amount = financial.get('total_amount')

            if not all([nif, invoice_number, issue_date, total_amount]):
                logger.warning("Insufficient data for AEAT validation")
                return None

            return await self.aeat_integration.validate_invoice_with_aeat(
                nif, invoice_number, issue_date, total_amount
            )

        except Exception as e:
            logger.error(f"AEAT validation failed: {e}")
            return None

    def _calculate_compliance_score(self, qr_result, phrase_result, format_result, aeat_result) -> float:
        """Calculate overall compliance score based on validation results."""
        total_score = 0.0

        # QR compliance scoring
        if qr_result:
            qr_score = 0
            if qr_result.qr_present:
                qr_score += 40
                if qr_result.qr_readable:
                    qr_score += 20
                if qr_result.aeat_url_valid:
                    qr_score += 20
                if qr_result.invoice_data_match:
                    qr_score += 20
            total_score += (qr_score / 100) * self.scoring_weights['qr_compliance']

        # Phrase compliance scoring
        if phrase_result:
            phrase_score = 0
            if phrase_result.phrase_present:
                phrase_score += 60
                if phrase_result.exact_match:
                    phrase_score += 40
                else:
                    phrase_score += phrase_result.confidence * 40
            total_score += (phrase_score / 100) * self.scoring_weights['phrase_compliance']

        # Format compliance scoring
        if format_result:
            format_score = 0
            if format_result.has_required_fields:
                format_score += 40
            if format_result.valid_identifiers:
                format_score += 20
            if format_result.structure_valid:
                format_score += 20
            if format_result.hash_valid:
                format_score += 10
            if not format_result.invalid_fields:
                format_score += 10
            total_score += (format_score / 100) * self.scoring_weights['format_compliance']

        # AEAT compliance scoring
        if aeat_result:
            aeat_score = 0
            if aeat_result.issuer_registered:
                aeat_score += 40
            if aeat_result.issuer_active:
                aeat_score += 30
            if aeat_result.invoice_exists:
                aeat_score += 30
            total_score += (aeat_score / 100) * self.scoring_weights['aeat_compliance']

        return min(total_score, 100.0)  # Cap at 100

    def _determine_compliance_level(self, score: float) -> VerifactuComplianceLevel:
        """Determine compliance level based on score."""
        if score >= 85:
            return VerifactuComplianceLevel.COMPLIANT
        elif score >= 60:
            return VerifactuComplianceLevel.WARNING
        else:
            return VerifactuComplianceLevel.NON_COMPLIANT

    def _generate_compliance_alerts(self, qr_result, phrase_result, format_result, aeat_result) -> List[VerifactuAlert]:
        """Generate compliance alerts based on validation results."""
        alerts = []

        # QR alerts
        if qr_result:
            if not qr_result.qr_present:
                alerts.append(VerifactuAlert(
                    level="critical",
                    message="Código QR obligatorio no detectado",
                    field="qr_code",
                    suggestion="Añadir código QR VERIFACTU válido",
                    auto_correctable=True
                ))
            elif not qr_result.aeat_url_valid:
                alerts.append(VerifactuAlert(
                    level="critical",
                    message="Código QR no contiene URL válida de AEAT",
                    field="qr_code",
                    suggestion="Corregir URL del código QR",
                    auto_correctable=True
                ))
            elif not qr_result.invoice_data_match:
                alerts.append(VerifactuAlert(
                    level="medium",
                    message="Datos del QR no coinciden con la factura",
                    field="qr_code",
                    suggestion="Verificar datos en código QR",
                    auto_correctable=False
                ))

        # Phrase alerts
        if phrase_result:
            if not phrase_result.phrase_present:
                alerts.append(VerifactuAlert(
                    level="critical",
                    message="Frase obligatoria VERIFACTU no encontrada",
                    field="verifactu_phrase",
                    suggestion="Añadir frase 'VERIFACTU' o 'Factura verificable en la sede electrónica de la AEAT'",
                    auto_correctable=True
                ))
            elif not phrase_result.exact_match and phrase_result.confidence < 0.8:
                alerts.append(VerifactuAlert(
                    level="medium",
                    message="Frase VERIFACTU detectada pero con errores",
                    field="verifactu_phrase",
                    suggestion=f"Corregir a: {phrase_result.suggested_correction}",
                    auto_correctable=True
                ))

        # Format alerts
        if format_result:
            if not format_result.has_required_fields:
                alerts.append(VerifactuAlert(
                    level="critical",
                    message=f"Faltan campos obligatorios: {', '.join(format_result.missing_fields)}",
                    field="required_fields",
                    suggestion="Completar todos los campos obligatorios",
                    auto_correctable=False
                ))

            if format_result.invalid_fields:
                alerts.append(VerifactuAlert(
                    level="medium",
                    message=f"Campos con formato inválido: {len(format_result.invalid_fields)}",
                    field="field_format",
                    suggestion="Corregir formato de campos",
                    auto_correctable=False
                ))

        # AEAT alerts
        if aeat_result:
            if not aeat_result.issuer_registered:
                alerts.append(VerifactuAlert(
                    level="critical",
                    message="Emisor no registrado en sistema VERIFACTU",
                    field="issuer_registration",
                    suggestion="Registrar emisor en AEAT VERIFACTU",
                    auto_correctable=False
                ))
            elif not aeat_result.issuer_active:
                alerts.append(VerifactuAlert(
                    level="medium",
                    message="Emisor registrado pero no activo en VERIFACTU",
                    field="issuer_status",
                    suggestion="Activar emisor en sistema VERIFACTU",
                    auto_correctable=False
                ))

        return alerts

    def _identify_auto_corrections(self, qr_result, phrase_result, format_result, invoice_data) -> List[VerifactuCorrection]:
        """Identify possible automatic corrections."""
        corrections = []

        # QR code corrections
        if qr_result and not qr_result.qr_present:
            suggested_qr = self.qr_validator.generate_missing_qr_suggestion(invoice_data)
            if suggested_qr:
                corrections.append(VerifactuCorrection(
                    field="qr_code",
                    current_value=None,
                    suggested_value=suggested_qr,
                    confidence=0.9,
                    correction_type="qr_generation"
                ))

        # Phrase corrections
        if phrase_result and not phrase_result.phrase_present:
            corrections.append(VerifactuCorrection(
                field="verifactu_phrase",
                current_value=None,
                suggested_value="VERIFACTU",
                confidence=1.0,
                correction_type="phrase_insertion"
            ))
        elif phrase_result and phrase_result.suggested_correction:
            corrections.append(VerifactuCorrection(
                field="verifactu_phrase",
                current_value=phrase_result.found_phrase,
                suggested_value=phrase_result.suggested_correction,
                confidence=phrase_result.confidence,
                correction_type="phrase_correction"
            ))

        return corrections

    async def generate_dashboard_stats(self, invoices_data: List[Dict[str, Any]]) -> VerifactuDashboardStats:
        """
        Generate dashboard statistics for multiple invoices.

        Args:
            invoices_data: List of invoice data dictionaries

        Returns:
            Dashboard statistics
        """
        logger.info(f"Generating VERIFACTU dashboard stats for {len(invoices_data)} invoices")

        total_invoices = len(invoices_data)
        compliant_count = 0
        warning_count = 0
        non_compliant_count = 0
        critical_alerts = 0
        medium_alerts = 0
        low_alerts = 0
        unregistered_issuers = set()

        # Process each invoice (simplified validation for dashboard)
        for invoice_data in invoices_data:
            try:
                # Quick validation for stats (no document bytes or text)
                format_result = self.format_validator.validate_verifactu_format(invoice_data)

                # Estimate compliance based on format validation
                if format_result.has_required_fields and format_result.structure_valid:
                    compliant_count += 1
                elif format_result.has_required_fields:
                    warning_count += 1
                else:
                    non_compliant_count += 1

                # Count missing fields as critical alerts
                critical_alerts += len(format_result.missing_fields)
                medium_alerts += len(format_result.invalid_fields)

                # Track unregistered issuers
                vendor = invoice_data.get('parties', {}).get('vendor', {})
                nif = vendor.get('tax_id')
                if nif:
                    unregistered_issuers.add(nif)

            except Exception as e:
                logger.warning(f"Error processing invoice for stats: {e}")
                non_compliant_count += 1
                critical_alerts += 1

        compliance_percentage = (compliant_count / total_invoices * 100) if total_invoices > 0 else 0

        # Estimate invoices that will fail in 2026 (simplified)
        invoices_failing_2026 = non_compliant_count + int(warning_count * 0.5)

        return VerifactuDashboardStats(
            total_invoices=total_invoices,
            compliant_invoices=compliant_count,
            warning_invoices=warning_count,
            non_compliant_invoices=non_compliant_count,
            compliance_percentage=compliance_percentage,
            invoices_failing_2026=invoices_failing_2026,
            unregistered_issuers=len(unregistered_issuers),
            critical_alerts=critical_alerts,
            medium_alerts=medium_alerts,
            low_alerts=low_alerts
        )

    async def get_issuer_compliance_summary(self, nif: str) -> Dict[str, Any]:
        """Get compliance summary for a specific issuer."""
        try:
            issuer_status = await self.aeat_integration.check_issuer_verifactu_status(nif)

            return {
                'nif': nif,
                'registered_in_verifactu': issuer_status.get('registered', False),
                'active_in_verifactu': issuer_status.get('active', False),
                'registration_date': issuer_status.get('registration_date'),
                'compliance_level': 'compliant' if issuer_status.get('active') else 'non_compliant',
                'requires_action': not issuer_status.get('registered', False),
                'action_needed': 'Registrar en VERIFACTU' if not issuer_status.get('registered') else None
            }

        except Exception as e:
            logger.error(f"Error getting issuer compliance summary: {e}")
            return {
                'nif': nif,
                'registered_in_verifactu': False,
                'active_in_verifactu': False,
                'compliance_level': 'unknown',
                'requires_action': True,
                'action_needed': 'Verificar estado manualmente',
                'error': str(e)
            }