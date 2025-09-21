# Copyright 2024 Artificial Intelligence Labs, SL

from datetime import datetime
from typing import Dict, List


class VerifactuConfig:
    """
    VERIFACTU Configuration based on official Spanish regulations.

    Implementation dates and requirements according to:
    - Ley 11/2021 de medidas de prevención y lucha contra el fraude fiscal
    - Real Decreto VERIFACTU (pending final approval)
    """

    # Implementation deadlines
    IMPLEMENTATION_DATES = {
        'software_providers': datetime(2025, 7, 1),  # July 2025
        'companies_sociedades': datetime(2026, 1, 1),  # January 1, 2026
        'autonomos_pymes': datetime(2026, 7, 1)  # July 1, 2026
    }

    # Exempt entities
    EXEMPT_ENTITIES = [
        'territorios_forales',  # Basque Country (TicketBAI), Navarra
        'sii_entities',  # Already using SII (Suministro Inmediato de Información)
        'modulos_autonomos',  # Módulos regime
        'recargo_equivalencia'  # Special VAT regime for retailers
    ]

    # Official AEAT endpoints for VERIFACTU
    AEAT_ENDPOINTS = {
        'production': {
            'verify_invoice': 'https://sede.agenciatributaria.gob.es/Sede/verificafactura',
            'registry': 'https://sede.agenciatributaria.gob.es/Sede/procedimientoini/G322.shtml',
            'issuer_check': 'https://www2.agenciatributaria.gob.es/wlpl/BUCV-JDIT/ConsultaEmisores'
        },
        'testing': {
            'verify_invoice': 'https://prewww1.aeat.es/wlpl/TGVI-JDIT/VerificaFactura',
            'registry': 'https://prewww1.aeat.es/wlpl/TGVI-JDIT/RegistroVF',
            'issuer_check': 'https://prewww1.aeat.es/wlpl/TGVI-JDIT/ConsultaEmisores'
        }
    }

    # Mandatory technical requirements
    TECHNICAL_REQUIREMENTS = {
        'inalterability': True,  # Facturas inalterables
        'traceability': True,  # Trazabilidad completa
        'automatic_sending': False,  # Envío automático (opcional)
        'chaining': True,  # Encadenamiento de facturas
        'cancellation_registry': True,  # Registro de anulación
        'cryptographic_hash': True,  # Huella criptográfica
        'digital_signature': True  # Firma electrónica
    }

    # Penalty amounts (euros)
    PENALTIES = {
        'users_per_year': 50000,  # Per fiscal year for non-compliant software
        'software_developers_per_year': 150000,  # Per year for non-compliant developers
        'uncertified_license': 1000  # Per uncertified license
    }

    # QR Code requirements (Official AEAT specifications)
    QR_REQUIREMENTS = {
        'mandatory': True,  # Obligatorio desde entrada en vigor
        'url_pattern': r'https://sede\.agenciatributaria\.gob\.es/Sede/verificafactura\?.*',
        'required_params': ['nif', 'num', 'fecha', 'importe'],
        'purpose_verifactu': 'Validar fiscalmente el contenido de la factura',
        'purpose_no_verifactu': 'Comunicar la factura a las autoridades fiscales',
        'app_recommended': True,  # Uso recomendado de APP AEAT para máxima seguridad
        'applies_to': ['facturas_completas', 'facturas_simplificadas']
    }

    # Mandatory phrase requirements (Official AEAT)
    PHRASE_REQUIREMENTS = {
        'mandatory': True,  # Obligatorio según RD 1007/2023
        'official_phrases': [
            'VERI*FACTU',  # Marca oficial
            'Factura verificable',  # Leyenda oficial
            'factura verificable'  # Variante aceptable
        ],
        'position': 'visible_on_invoice',
        'font_size_min': '8pt',
        'note': 'Incorporación obligatoria en facturas y facturas simplificadas'
    }

    # Hash algorithm specifications
    HASH_SPECIFICATIONS = {
        'algorithm': 'SHA-256',
        'encoding': 'hexadecimal',
        'length': 64,  # characters
        'includes': ['nif_emisor', 'numero_factura', 'fecha_expedicion', 'importe_total']
    }

    # Software certification requirements
    CERTIFICATION_REQUIREMENTS = {
        'declaration_required': True,  # Declaración responsable
        'aeat_collaboration': 'recommended',  # Colaborador social AEAT
        'cloud_compatible': True,
        'erp_integration': True,
        'b2b_b2c_support': True  # Both business and consumer operations
    }

    @classmethod
    def is_implementation_date_passed(cls, entity_type: str) -> bool:
        """Check if implementation deadline has passed for entity type."""
        deadline = cls.IMPLEMENTATION_DATES.get(entity_type)
        if deadline:
            return datetime.now() >= deadline
        return False

    @classmethod
    def days_until_deadline(cls, entity_type: str) -> int:
        """Calculate days until deadline for entity type."""
        deadline = cls.IMPLEMENTATION_DATES.get(entity_type)
        if deadline:
            delta = deadline - datetime.now()
            return max(0, delta.days)
        return 0

    @classmethod
    def get_applicable_deadline(cls, is_sociedad: bool) -> datetime:
        """Get applicable deadline based on entity type."""
        if is_sociedad:
            return cls.IMPLEMENTATION_DATES['companies_sociedades']
        else:
            return cls.IMPLEMENTATION_DATES['autonomos_pymes']

    @classmethod
    def is_entity_exempt(cls, entity_characteristics: Dict[str, bool]) -> tuple[bool, List[str]]:
        """
        Check if entity is exempt from VERIFACTU.

        Args:
            entity_characteristics: Dict with entity characteristics

        Returns:
            Tuple of (is_exempt, reasons)
        """
        exempt_reasons = []

        if entity_characteristics.get('is_territorio_foral', False):
            exempt_reasons.append('Territorio foral (TicketBAI/sistema propio)')

        if entity_characteristics.get('uses_sii', False):
            exempt_reasons.append('Acogido al SII (Suministro Inmediato de Información)')

        if entity_characteristics.get('is_modulos', False):
            exempt_reasons.append('Régimen de módulos')

        if entity_characteristics.get('is_recargo_equivalencia', False):
            exempt_reasons.append('Régimen de recargo de equivalencia')

        return len(exempt_reasons) > 0, exempt_reasons

    @classmethod
    def validate_qr_compliance(cls, qr_data: str) -> Dict[str, bool]:
        """Validate QR code compliance with VERIFACTU requirements."""
        import re
        from urllib.parse import urlparse, parse_qs

        results = {
            'has_valid_url': False,
            'has_required_params': False,
            'url_format_correct': False
        }

        try:
            # Check URL pattern
            if re.match(cls.QR_REQUIREMENTS['url_pattern'], qr_data):
                results['url_format_correct'] = True
                results['has_valid_url'] = True

                # Check required parameters
                parsed = urlparse(qr_data)
                params = parse_qs(parsed.query)

                required_params = cls.QR_REQUIREMENTS['required_params']
                has_all_params = all(param in params for param in required_params)
                results['has_required_params'] = has_all_params

        except Exception:
            pass

        return results

    @classmethod
    def get_compliance_checklist(cls) -> List[Dict[str, str]]:
        """Get VERIFACTU compliance checklist."""
        return [
            {
                'requirement': 'Software de facturación certificado',
                'description': 'Usar programa que cumpla especificaciones VERIFACTU',
                'mandatory': 'Sí',
                'deadline': 'Según tipo de entidad'
            },
            {
                'requirement': 'Código QR obligatorio',
                'description': 'Incluir QR con URL de verificación AEAT',
                'mandatory': 'Sí',
                'deadline': '2026'
            },
            {
                'requirement': 'Frase obligatoria',
                'description': 'Incluir "VERIFACTU" o frase completa',
                'mandatory': 'Sí',
                'deadline': '2026'
            },
            {
                'requirement': 'Hash criptográfico',
                'description': 'Huella digital para trazabilidad',
                'mandatory': 'Sí',
                'deadline': '2026'
            },
            {
                'requirement': 'Encadenamiento de facturas',
                'description': 'Vinculación secuencial para verificación',
                'mandatory': 'Sí',
                'deadline': '2026'
            },
            {
                'requirement': 'Registro en AEAT',
                'description': 'Alta del emisor en sistema VERIFACTU',
                'mandatory': 'Sí',
                'deadline': 'Antes de emisión'
            }
        ]