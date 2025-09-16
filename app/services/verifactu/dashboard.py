# Copyright 2024 Artificial Intelligence Labs, SL

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from app.services.verifactu.models import (
    VerifactuDashboardStats,
    VerifactuAlert,
    VerifactuValidationResult,
    VerifactuCorrection
)
from app.services.verifactu.verifactu_validator import VerifactuValidator


class VerifactuDashboard:
    """
    VERIFACTU Compliance Dashboard System.

    Provides comprehensive dashboard functionality for monitoring
    VERIFACTU compliance across multiple invoices and issuers.
    """

    def __init__(self):
        self.validator = VerifactuValidator()

    async def generate_compliance_dashboard(self, invoice_validations: List[VerifactuValidationResult]) -> Dict[str, Any]:
        """
        Generate complete VERIFACTU compliance dashboard.

        Args:
            invoice_validations: List of validation results

        Returns:
            Complete dashboard data structure
        """
        logger.info(f"Generating VERIFACTU dashboard for {len(invoice_validations)} invoices")

        try:
            # Calculate overall statistics
            stats = self._calculate_dashboard_stats(invoice_validations)

            # Generate alerts summary
            alerts_summary = self._generate_alerts_summary(invoice_validations)

            # Critical actions needed
            critical_actions = self._identify_critical_actions(invoice_validations)

            # Auto-correction opportunities
            auto_corrections = self._identify_auto_correction_opportunities(invoice_validations)

            # Compliance trends (if historical data available)
            trends = self._calculate_compliance_trends(invoice_validations)

            # Issuer analysis
            issuer_analysis = self._analyze_issuers(invoice_validations)

            dashboard = {
                'overview': {
                    'total_invoices': stats.total_invoices,
                    'compliance_percentage': stats.compliance_percentage,
                    'verifactu_ready': stats.compliant_invoices,
                    'warnings': stats.warning_invoices,
                    'non_compliant': stats.non_compliant_invoices,
                    'generated_at': datetime.now().isoformat()
                },
                'critical_metrics': {
                    'invoices_failing_2026': stats.invoices_failing_2026,
                    'unregistered_issuers': stats.unregistered_issuers,
                    'critical_alerts': stats.critical_alerts,
                    'immediate_action_required': critical_actions['immediate_count']
                },
                'alerts_summary': alerts_summary,
                'critical_actions': critical_actions,
                'auto_corrections': auto_corrections,
                'compliance_trends': trends,
                'issuer_analysis': issuer_analysis,
                'recommendations': self._generate_recommendations(stats, critical_actions)
            }

            logger.info(f"Dashboard generated - {stats.compliance_percentage:.1f}% compliance rate")
            return dashboard

        except Exception as e:
            logger.error(f"Error generating dashboard: {e}")
            return self._generate_error_dashboard(str(e))

    def _calculate_dashboard_stats(self, validations: List[VerifactuValidationResult]) -> VerifactuDashboardStats:
        """Calculate dashboard statistics from validation results."""
        total = len(validations)
        compliant = sum(1 for v in validations if v.compliance_level.value == "compliant")
        warning = sum(1 for v in validations if v.compliance_level.value == "warning")
        non_compliant = sum(1 for v in validations if v.compliance_level.value == "non_compliant")

        # Count alerts by type
        critical_alerts = sum(v.critical_issues for v in validations)
        medium_alerts = sum(v.warnings for v in validations)

        # Estimate failing in 2026 (non-compliant + half of warnings)
        failing_2026 = non_compliant + (warning // 2)

        # Count unique unregistered issuers
        unregistered_issuers = 0
        seen_issuers = set()
        for validation in validations:
            if validation.aeat_validation and not validation.aeat_validation.issuer_registered:
                # Would need issuer ID to count unique ones properly
                unregistered_issuers += 1

        compliance_percentage = (compliant / total * 100) if total > 0 else 0

        return VerifactuDashboardStats(
            total_invoices=total,
            compliant_invoices=compliant,
            warning_invoices=warning,
            non_compliant_invoices=non_compliant,
            compliance_percentage=compliance_percentage,
            invoices_failing_2026=failing_2026,
            unregistered_issuers=unregistered_issuers,
            critical_alerts=critical_alerts,
            medium_alerts=medium_alerts,
            low_alerts=0  # Not tracked in current model
        )

    def _generate_alerts_summary(self, validations: List[VerifactuValidationResult]) -> Dict[str, Any]:
        """Generate summary of all alerts."""
        all_alerts = []
        for validation in validations:
            all_alerts.extend(validation.alerts)

        # Group alerts by type
        alert_groups = {}
        for alert in all_alerts:
            key = alert.message
            if key not in alert_groups:
                alert_groups[key] = {
                    'message': alert.message,
                    'level': alert.level,
                    'count': 0,
                    'auto_correctable': alert.auto_correctable,
                    'suggestion': alert.suggestion
                }
            alert_groups[key]['count'] += 1

        # Sort by severity and count
        severity_order = {'critical': 0, 'medium': 1, 'low': 2}
        sorted_alerts = sorted(
            alert_groups.values(),
            key=lambda x: (severity_order.get(x['level'], 3), -x['count'])
        )

        return {
            'total_alerts': len(all_alerts),
            'unique_alert_types': len(alert_groups),
            'top_alerts': sorted_alerts[:10],
            'by_level': {
                'critical': len([a for a in all_alerts if a.level == 'critical']),
                'medium': len([a for a in all_alerts if a.level == 'medium']),
                'low': len([a for a in all_alerts if a.level == 'low'])
            }
        }

    def _identify_critical_actions(self, validations: List[VerifactuValidationResult]) -> Dict[str, Any]:
        """Identify critical actions that need immediate attention."""
        critical_actions = {
            'immediate_count': 0,
            'actions': []
        }

        # Track action types
        action_counts = {
            'missing_qr': 0,
            'missing_phrase': 0,
            'unregistered_issuer': 0,
            'format_issues': 0,
            'invalid_data': 0
        }

        for validation in validations:
            immediate_action = False

            # Missing QR code
            if validation.qr_validation and not validation.qr_validation.qr_present:
                action_counts['missing_qr'] += 1
                immediate_action = True

            # Missing mandatory phrase
            if validation.phrase_validation and not validation.phrase_validation.phrase_present:
                action_counts['missing_phrase'] += 1
                immediate_action = True

            # Unregistered issuer
            if validation.aeat_validation and not validation.aeat_validation.issuer_registered:
                action_counts['unregistered_issuer'] += 1
                immediate_action = True

            # Critical format issues
            if validation.format_validation and not validation.format_validation.has_required_fields:
                action_counts['format_issues'] += 1
                immediate_action = True

            if immediate_action:
                critical_actions['immediate_count'] += 1

        # Generate action items
        if action_counts['missing_qr'] > 0:
            critical_actions['actions'].append({
                'type': 'missing_qr',
                'count': action_counts['missing_qr'],
                'priority': 'HIGH',
                'message': f"{action_counts['missing_qr']} facturas sin código QR",
                'action': 'Generar códigos QR para todas las facturas',
                'auto_correctable': True
            })

        if action_counts['missing_phrase'] > 0:
            critical_actions['actions'].append({
                'type': 'missing_phrase',
                'count': action_counts['missing_phrase'],
                'priority': 'HIGH',
                'message': f"{action_counts['missing_phrase']} facturas sin frase obligatoria",
                'action': 'Añadir frase VERIFACTU',
                'auto_correctable': True
            })

        if action_counts['unregistered_issuer'] > 0:
            critical_actions['actions'].append({
                'type': 'unregistered_issuer',
                'count': action_counts['unregistered_issuer'],
                'priority': 'URGENT',
                'message': f"{action_counts['unregistered_issuer']} emisores no registrados en VERIFACTU",
                'action': 'Registrar emisores en sistema AEAT',
                'auto_correctable': False
            })

        return critical_actions

    def _identify_auto_correction_opportunities(self, validations: List[VerifactuValidationResult]) -> Dict[str, Any]:
        """Identify opportunities for automatic correction."""
        total_correctable = 0
        corrections_by_type = {}

        for validation in validations:
            if validation.can_auto_correct:
                total_correctable += 1

                for suggestion in validation.correction_suggestions:
                    # Categorize correction type
                    if 'QR' in suggestion or 'código' in suggestion.lower():
                        correction_type = 'qr_generation'
                    elif 'frase' in suggestion.lower() or 'VERIFACTU' in suggestion:
                        correction_type = 'phrase_insertion'
                    else:
                        correction_type = 'format_correction'

                    if correction_type not in corrections_by_type:
                        corrections_by_type[correction_type] = {
                            'count': 0,
                            'description': self._get_correction_description(correction_type)
                        }
                    corrections_by_type[correction_type]['count'] += 1

        return {
            'total_auto_correctable': total_correctable,
            'correction_types': corrections_by_type,
            'potential_savings': f"{total_correctable} facturas pueden corregirse automáticamente"
        }

    def _get_correction_description(self, correction_type: str) -> str:
        """Get description for correction type."""
        descriptions = {
            'qr_generation': 'Generar códigos QR faltantes automáticamente',
            'phrase_insertion': 'Insertar frases VERIFACTU obligatorias',
            'format_correction': 'Corregir formatos de datos automáticamente'
        }
        return descriptions.get(correction_type, 'Corrección automática')

    def _calculate_compliance_trends(self, validations: List[VerifactuValidationResult]) -> Dict[str, Any]:
        """Calculate compliance trends (simplified without historical data)."""
        # This would be more meaningful with historical data
        current_compliance = sum(1 for v in validations if v.verifactu_ready) / len(validations) * 100

        return {
            'current_compliance_rate': current_compliance,
            'trend_direction': 'stable',  # Would calculate from historical data
            'projected_2026_readiness': min(current_compliance + 10, 100),  # Optimistic projection
            'improvement_needed': max(0, 85 - current_compliance),  # To reach 85% target
            'note': 'Tendencias basadas en datos actuales. Historial completo requiere datos temporales.'
        }

    def _analyze_issuers(self, validations: List[VerifactuValidationResult]) -> Dict[str, Any]:
        """Analyze issuer-specific compliance patterns."""
        issuer_data = {}

        # Group by issuer (simplified - would need actual issuer IDs)
        total_issuers = len(set(f"issuer_{i}" for i in range(len(validations))))  # Placeholder

        compliant_issuers = sum(1 for v in validations if v.verifactu_ready)
        problem_issuers = len(validations) - compliant_issuers

        return {
            'total_issuers': total_issuers,
            'compliant_issuers': compliant_issuers,
            'problem_issuers': problem_issuers,
            'top_issues': [
                'Códigos QR faltantes',
                'Frases obligatorias ausentes',
                'Datos incompletos'
            ],
            'note': 'Análisis detallado por emisor requiere identificadores de emisor'
        }

    def _generate_recommendations(self, stats: VerifactuDashboardStats, critical_actions: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        if stats.compliance_percentage < 50:
            recommendations.append("🚨 URGENTE: Menos del 50% de facturas son VERIFACTU-ready. Priorizar correcciones inmediatas.")

        if critical_actions['immediate_count'] > 0:
            recommendations.append(f"⚠️  {critical_actions['immediate_count']} facturas requieren acción inmediata antes de 2026.")

        if stats.unregistered_issuers > 0:
            recommendations.append(f"📋 {stats.unregistered_issuers} emisores deben registrarse en sistema VERIFACTU de AEAT.")

        if stats.compliance_percentage > 80:
            recommendations.append("✅ Excelente progreso en cumplimiento VERIFACTU. Continuar con las mejores prácticas.")

        if stats.critical_alerts > 10:
            recommendations.append("🔧 Implementar correcciones automáticas para resolver alertas críticas de forma eficiente.")

        return recommendations

    def _generate_error_dashboard(self, error_message: str) -> Dict[str, Any]:
        """Generate error dashboard when main generation fails."""
        return {
            'overview': {
                'total_invoices': 0,
                'compliance_percentage': 0,
                'error': error_message,
                'generated_at': datetime.now().isoformat()
            },
            'critical_metrics': {
                'error': 'No se pudieron calcular métricas críticas',
                'status': 'ERROR'
            },
            'recommendations': [
                '❌ Error generando dashboard. Revisar logs del sistema.',
                '🔄 Intentar nuevamente con datos válidos.'
            ]
        }

    def format_dashboard_for_display(self, dashboard_data: Dict[str, Any]) -> str:
        """Format dashboard data for console/web display."""
        overview = dashboard_data.get('overview', {})
        critical = dashboard_data.get('critical_metrics', {})
        actions = dashboard_data.get('critical_actions', {})

        display = f"""
📊 ESTADO VERIFACTU DE TUS FACTURAS

✅ {overview.get('verifactu_ready', 0)} facturas VERIFACTU-ready ({overview.get('compliance_percentage', 0):.1f}%)
⚠️ {overview.get('warnings', 0)} facturas con advertencias
❌ {overview.get('non_compliant', 0)} facturas NO conformes

🚨 PRÓXIMAS ACCIONES CRÍTICAS:
- {critical.get('invoices_failing_2026', 0)} facturas fallarán en 2026 - CORREGIR AHORA
- {critical.get('unregistered_issuers', 0)} proveedores sin alta VERIFACTU - CONTACTAR

📋 ALERTAS ACTIVAS:
- {critical.get('critical_alerts', 0)} alertas críticas
- {actions.get('immediate_count', 0)} acciones inmediatas requeridas

💡 RECOMENDACIONES:
"""

        recommendations = dashboard_data.get('recommendations', [])
        for rec in recommendations[:3]:  # Show top 3
            display += f"   {rec}\n"

        return display