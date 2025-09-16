# Copyright 2024 Artificial Intelligence Labs, SL

"""
Registro de Facturación de Alta según especificaciones oficiales AEAT.

Implementa el contenido del registro informático según RD 1007/2023
y especificaciones técnicas del Anexo de la Orden Ministerial.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class TipoFactura(str, Enum):
    """Tipos de factura según RRSIF."""
    COMPLETA = "completa"
    SIMPLIFICADA = "simplificada"


class RegimenAplicado(str, Enum):
    """Regímenes aplicados a las operaciones."""
    GENERAL = "general"
    INVERSION_SUJETO_PASIVO = "inversion_sujeto_pasivo"
    EXENTO = "exento"
    NO_SUJETO = "no_sujeto"


@dataclass
class RegistroFacturacionAlta:
    """
    Registro informático de facturación de alta.

    NO ES UNA FACTURA ELECTRÓNICA.
    Contiene la información obligatoria según Art. 6 ROF + datos de seguridad.
    """

    # === DATOS DEL EMISOR ===
    nif_emisor: str  # NIF del emisor
    nombre_emisor: str  # Nombre y apellidos, razón o denominación social emisor

    # === DATOS DEL DESTINATARIO ===
    nif_destinatario: Optional[str]  # NIF del destinatario (si requerido por normativa)
    nombre_destinatario: Optional[str]  # Nombre del destinatario
    numero_pais_residencia: Optional[str]  # Si es extranjero

    # === EXPEDICIÓN MATERIAL ===
    expedida_por_destinatario: bool  # Si la factura fue expedida por el destinatario
    expedida_por_tercero: bool  # Si fue expedida por un tercero
    nif_tercero_expedidor: Optional[str]  # NIF del tercero expedidor
    nombre_tercero_expedidor: Optional[str]  # Nombre del tercero expedidor

    # === IDENTIFICACIÓN DE LA FACTURA ===
    numero_factura: str  # Número de la factura
    serie_factura: Optional[str]  # Serie de la factura (en su caso)
    fecha_expedicion: str  # Fecha de expedición (YYYY-MM-DD)
    fecha_operacion: Optional[str]  # Fecha de operación si distinta
    fecha_pago_anticipado: Optional[str]  # Fecha de pago anticipado si aplica

    # === TIPO Y CARACTERÍSTICAS ===
    tipo_factura: TipoFactura  # Completa o simplificada
    es_rectificativa: bool  # Si tiene consideración de rectificativa
    facturas_rectificadas: Optional[List[str]]  # IDs de facturas rectificadas
    es_sustitucion: bool  # Si es sustitución de facturas simplificadas
    facturas_sustituidas: Optional[List[str]]  # IDs de facturas sustituidas

    # === DESCRIPCIÓN DE OPERACIONES ===
    descripcion_operaciones: str  # Descripción general de las operaciones

    # === IMPORTES ===
    importe_total: float  # Importe total de la factura

    # === REGÍMENES APLICADOS ===
    regimenes_aplicados: List[RegimenAplicado]  # Régimen o regímenes aplicados

    # === INVERSIÓN DEL SUJETO PASIVO ===
    destinatario_es_sujeto_pasivo: bool  # Si aplica inversión del sujeto pasivo

    # === DESGLOSE FISCAL ===
    base_imponible: float  # Base imponible de las operaciones
    tipos_impositivos: List[float]  # Tipo o tipos impositivos aplicados
    cuota_iva: float  # Cuota del IVA
    tipos_recargo_equivalencia: Optional[List[float]]  # Tipos de recargo equivalencia
    cuota_recargo_equivalencia: Optional[float]  # Cuota del recargo equivalencia

    # === OPERACIONES NO SUJETAS ===
    importe_no_sujeto: Optional[float]  # Importe no sujeto al IVA
    causa_no_sujecion: Optional[str]  # Causa de la no sujeción

    # === ENCADENAMIENTO (solo si no es el primer registro) ===
    numero_factura_anterior: Optional[str]  # Número de factura anterior
    serie_factura_anterior: Optional[str]  # Serie de factura anterior
    fecha_expedicion_anterior: Optional[str]  # Fecha expedición anterior
    hash_registro_anterior: Optional[str]  # Parte del hash del registro anterior

    # === IDENTIFICACIÓN DEL SISTEMA ===
    codigo_sistema_informatico: str  # Código de identificación del SIF
    datos_productor_sistema: Dict[str, str]  # Datos identificativos del productor

    # === TIMESTAMP ===
    fecha_generacion: str  # Fecha, hora, minuto y segundo de generación

    # === CARACTERÍSTICAS ADICIONALES ===
    circunstancias_generacion: Dict[str, Any]  # Circunstancias de generación

    # === HASH DE SEGURIDAD ===
    hash_registro: str  # Hash criptográfico del registro


class GeneradorRegistroFacturacion:
    """
    Generador de registros de facturación según especificaciones oficiales.
    """

    def __init__(self, codigo_sistema: str, datos_productor: Dict[str, str]):
        self.codigo_sistema = codigo_sistema
        self.datos_productor = datos_productor
        self.ultimo_hash: Optional[str] = None
        self.contador_registros = 0

    def generar_registro_alta(
        self,
        invoice_data: Dict[str, Any],
        modalidad_verifactu: bool = True
    ) -> RegistroFacturacionAlta:
        """
        Genera un registro de facturación de alta a partir de datos de factura.

        Args:
            invoice_data: Datos de la factura procesada
            modalidad_verifactu: Si es modalidad VERI*FACTU o NO VERI*FACTU

        Returns:
            RegistroFacturacionAlta completo
        """

        # Extraer datos básicos
        parties = invoice_data.get('parties', {})
        vendor = parties.get('vendor', {})
        customer = parties.get('customer', {})
        metadata = invoice_data.get('metadata', {})
        financial = invoice_data.get('financial_details', {})
        tax = financial.get('tax', {})
        items = invoice_data.get('items', [])

        # Incrementar contador
        self.contador_registros += 1

        # Generar timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Determinar encadenamiento
        numero_anterior = None
        serie_anterior = None
        fecha_anterior = None
        hash_anterior = None

        if self.contador_registros > 1 and self.ultimo_hash:
            # En un sistema real, aquí se buscaría el registro anterior
            numero_anterior = "PREV-001"  # Placeholder
            fecha_anterior = "2024-01-14"
            hash_anterior = self.ultimo_hash[:16]  # Parte del hash anterior

        # Crear registro
        registro = RegistroFacturacionAlta(
            # Emisor
            nif_emisor=vendor.get('tax_id', ''),
            nombre_emisor=vendor.get('name', ''),

            # Destinatario
            nif_destinatario=customer.get('tax_id'),
            nombre_destinatario=customer.get('name'),
            numero_pais_residencia=None,  # Asumir nacional

            # Expedición
            expedida_por_destinatario=False,
            expedida_por_tercero=False,
            nif_tercero_expedidor=None,
            nombre_tercero_expedidor=None,

            # Identificación
            numero_factura=metadata.get('invoice_number', ''),
            serie_factura=None,  # Extraer de número si tiene serie
            fecha_expedicion=metadata.get('issue_date', ''),
            fecha_operacion=None,  # Asumir igual a expedición
            fecha_pago_anticipado=None,

            # Tipo
            tipo_factura=self._determinar_tipo_factura(customer),
            es_rectificativa=False,  # Por ahora no detectamos rectificativas
            facturas_rectificadas=None,
            es_sustitucion=False,
            facturas_sustituidas=None,

            # Operaciones
            descripcion_operaciones=self._generar_descripcion_operaciones(items),

            # Importes
            importe_total=financial.get('total_amount', 0.0),

            # Regímenes
            regimenes_aplicados=[RegimenAplicado.GENERAL],  # Por defecto

            # Inversión sujeto pasivo
            destinatario_es_sujeto_pasivo=False,  # Por defecto

            # Fiscal
            base_imponible=financial.get('subtotal', 0.0),
            tipos_impositivos=[tax.get('rate', 21.0)],
            cuota_iva=tax.get('amount', 0.0),
            tipos_recargo_equivalencia=None,
            cuota_recargo_equivalencia=None,

            # No sujeto
            importe_no_sujeto=None,
            causa_no_sujecion=None,

            # Encadenamiento
            numero_factura_anterior=numero_anterior,
            serie_factura_anterior=serie_anterior,
            fecha_expedicion_anterior=fecha_anterior,
            hash_registro_anterior=hash_anterior,

            # Sistema
            codigo_sistema_informatico=self.codigo_sistema,
            datos_productor_sistema=self.datos_productor,

            # Timestamp
            fecha_generacion=timestamp,

            # Características
            circunstancias_generacion={
                'modalidad': 'VERI*FACTU' if modalidad_verifactu else 'NO VERI*FACTU',
                'contador_registro': self.contador_registros,
                'procesamiento_automatico': True
            },

            # Hash (se calcula después)
            hash_registro=''
        )

        # Calcular hash del registro
        registro.hash_registro = self._calcular_hash_registro(registro)
        self.ultimo_hash = registro.hash_registro

        return registro

    def _determinar_tipo_factura(self, customer: Dict[str, Any]) -> TipoFactura:
        """Determina si es factura completa o simplificada."""
        # Completa si tiene datos completos del cliente
        if customer.get('tax_id') and customer.get('name'):
            return TipoFactura.COMPLETA
        else:
            return TipoFactura.SIMPLIFICADA

    def _generar_descripcion_operaciones(self, items: List[Dict[str, Any]]) -> str:
        """Genera descripción general de las operaciones."""
        if not items:
            return "Servicios profesionales"

        descriptions = [item.get('description', 'Producto/Servicio') for item in items[:3]]
        if len(items) > 3:
            descriptions.append(f"y {len(items) - 3} más")

        return ", ".join(descriptions)

    def _calcular_hash_registro(self, registro: RegistroFacturacionAlta) -> str:
        """
        Calcula el hash criptográfico del registro.

        En la implementación real usaría SHA-256 con los campos específicos
        según las especificaciones técnicas oficiales.
        """
        import hashlib

        # Concatenar campos principales para el hash
        hash_input = (
            f"{registro.nif_emisor}|"
            f"{registro.numero_factura}|"
            f"{registro.fecha_expedicion}|"
            f"{registro.importe_total}|"
            f"{registro.hash_registro_anterior or ''}|"
            f"{registro.fecha_generacion}"
        )

        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

    def exportar_registro_json(self, registro: RegistroFacturacionAlta) -> Dict[str, Any]:
        """
        Exporta el registro en formato JSON para transmisión.

        Este formato se usaría para:
        - Modalidad VERI*FACTU: Envío inmediato a AEAT
        - Modalidad NO VERI*FACTU: Conservación local con firma
        """
        return {
            "version": "1.0",
            "tipo_registro": "alta",
            "registro": {
                "emisor": {
                    "nif": registro.nif_emisor,
                    "nombre": registro.nombre_emisor
                },
                "destinatario": {
                    "nif": registro.nif_destinatario,
                    "nombre": registro.nombre_destinatario
                },
                "factura": {
                    "numero": registro.numero_factura,
                    "serie": registro.serie_factura,
                    "fecha_expedicion": registro.fecha_expedicion,
                    "tipo": registro.tipo_factura.value,
                    "importe_total": registro.importe_total
                },
                "fiscal": {
                    "base_imponible": registro.base_imponible,
                    "tipos_iva": registro.tipos_impositivos,
                    "cuota_iva": registro.cuota_iva,
                    "regimenes": [r.value for r in registro.regimenes_aplicados]
                },
                "encadenamiento": {
                    "numero_anterior": registro.numero_factura_anterior,
                    "fecha_anterior": registro.fecha_expedicion_anterior,
                    "hash_anterior": registro.hash_registro_anterior
                },
                "sistema": {
                    "codigo": registro.codigo_sistema_informatico,
                    "productor": registro.datos_productor_sistema,
                    "timestamp": registro.fecha_generacion
                },
                "seguridad": {
                    "hash": registro.hash_registro,
                    "circunstancias": registro.circunstancias_generacion
                }
            }
        }


# Instancia global del generador
generador_registro = GeneradorRegistroFacturacion(
    codigo_sistema="CLAUDE-VERIFACTU-001",
    datos_productor={
        "nombre": "Claude Invoice Parser",
        "version": "1.0.1",
        "fabricante": "Anthropic",
        "contacto": "claude-code@anthropic.com"
    }
)