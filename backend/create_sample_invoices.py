#!/usr/bin/env python3
"""
Create sample invoices for VERIFACTU testing.

This script generates PDF invoices with and without VERIFACTU compliance
to test the validation system.
"""

import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from io import BytesIO
import base64
from datetime import datetime


def create_compliant_invoice():
    """Create a VERIFACTU-compliant invoice."""
    filename = "factura_verifactu_compliant.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Invoice header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "FACTURA")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, "Número: FAC-2024-001")
    c.drawString(50, height - 100, "Fecha: 15/01/2024")

    # Vendor data
    c.drawString(50, height - 140, "EMISOR:")
    c.drawString(50, height - 160, "Empresa Ejemplo S.L.")
    c.drawString(50, height - 180, "NIF: B12345678")
    c.drawString(50, height - 200, "Calle Ejemplo, 123")
    c.drawString(50, height - 220, "28001 Madrid")

    # Customer data
    c.drawString(300, height - 140, "CLIENTE:")
    c.drawString(300, height - 160, "Cliente Prueba S.A.")
    c.drawString(300, height - 180, "NIF: A87654321")
    c.drawString(300, height - 200, "Avenida Test, 456")
    c.drawString(300, height - 220, "28002 Madrid")

    # Line items
    c.drawString(50, height - 280, "CONCEPTO")
    c.drawString(300, height - 280, "CANTIDAD")
    c.drawString(400, height - 280, "PRECIO")
    c.drawString(480, height - 280, "TOTAL")

    c.line(50, height - 290, 550, height - 290)

    c.drawString(50, height - 310, "Servicio de consultoría")
    c.drawString(320, height - 310, "1")
    c.drawString(400, height - 310, "100,00 €")
    c.drawString(480, height - 310, "100,00 €")

    # Totals
    c.line(400, height - 340, 550, height - 340)
    c.drawString(400, height - 360, "Base imponible:")
    c.drawString(480, height - 360, "100,00 €")

    c.drawString(400, height - 380, "IVA (21%):")
    c.drawString(480, height - 380, "21,00 €")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, height - 400, "TOTAL:")
    c.drawString(480, height - 400, "121,00 €")

    # VERIFACTU mandatory phrase
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 450, "VERIFACTU")

    c.setFont("Helvetica", 8)
    c.drawString(50, height - 470, "Factura verificable en la sede electrónica de la AEAT")

    # Generate QR code
    qr_data = (
        "https://sede.agenciatributaria.gob.es/Sede/verificafactura?"
        "nif=B12345678&num=FAC-2024-001&fecha=2024-01-15&importe=121.00"
    )

    qr = qrcode.QRCode(version=1, box_size=3, border=1)
    qr.add_data(qr_data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Save QR to temporary buffer and add to PDF
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)

    # Add QR to PDF (simplified - in real implementation you'd embed the image)
    c.drawString(400, height - 470, "Código QR VERIFACTU →")
    c.rect(450, height - 520, 50, 50)  # QR placeholder
    c.drawString(460, height - 495, "QR")

    # Hash criptográfico (simplified)
    c.setFont("Helvetica", 6)
    c.drawString(50, height - 520, "Hash: SHA256:a1b2c3d4e5f6789...")
    c.drawString(50, height - 535, "Registro: VF2024001234567")

    c.save()
    print(f"✅ Created compliant invoice: {filename}")
    return filename


def create_non_compliant_invoice():
    """Create a non-VERIFACTU-compliant invoice."""
    filename = "factura_non_compliant.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Invoice header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "FACTURA")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, "Número: FAC-2024-002")
    c.drawString(50, height - 100, "Fecha: 16/01/2024")

    # Vendor data (missing some required fields)
    c.drawString(50, height - 140, "EMISOR:")
    c.drawString(50, height - 160, "Empresa Sin VERIFACTU")
    c.drawString(50, height - 180, "NIF: C98765432")
    # Missing address

    # Customer data
    c.drawString(300, height - 140, "CLIENTE:")
    c.drawString(300, height - 160, "Cliente Test")
    # Missing NIF and address

    # Line items
    c.drawString(50, height - 280, "CONCEPTO")
    c.drawString(400, height - 280, "TOTAL")

    c.line(50, height - 290, 550, height - 290)

    c.drawString(50, height - 310, "Producto ejemplo")
    c.drawString(480, height - 310, "50,00 €")

    # Totals (missing tax breakdown)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, height - 360, "TOTAL:")
    c.drawString(480, height - 360, "50,00 €")

    # NO VERIFACTU phrase
    # NO QR code
    # NO hash

    c.setFont("Helvetica", 8)
    c.drawString(50, height - 450, "Factura tradicional sin VERIFACTU")

    c.save()
    print(f"❌ Created non-compliant invoice: {filename}")
    return filename


def create_partial_compliant_invoice():
    """Create a partially VERIFACTU-compliant invoice."""
    filename = "factura_partial_compliant.pdf"
    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # Invoice header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "FACTURA")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, "Número: FAC-2024-003")
    c.drawString(50, height - 100, "Fecha: 17/01/2024")

    # Complete vendor data
    c.drawString(50, height - 140, "EMISOR:")
    c.drawString(50, height - 160, "Empresa Parcial S.L.")
    c.drawString(50, height - 180, "NIF: D11223344")
    c.drawString(50, height - 200, "Plaza Parcial, 789")
    c.drawString(50, height - 220, "28003 Madrid")

    # Complete customer data
    c.drawString(300, height - 140, "CLIENTE:")
    c.drawString(300, height - 160, "Cliente Completo S.L.")
    c.drawString(300, height - 180, "NIF: E55667788")
    c.drawString(300, height - 200, "Calle Completa, 321")
    c.drawString(300, height - 220, "28004 Madrid")

    # Line items with complete breakdown
    c.drawString(50, height - 280, "CONCEPTO")
    c.drawString(300, height - 280, "CANTIDAD")
    c.drawString(400, height - 280, "PRECIO")
    c.drawString(480, height - 280, "TOTAL")

    c.line(50, height - 290, 550, height - 290)

    c.drawString(50, height - 310, "Servicio desarrollo")
    c.drawString(320, height - 310, "5")
    c.drawString(400, height - 310, "40,00 €")
    c.drawString(480, height - 310, "200,00 €")

    # Complete totals
    c.line(400, height - 340, 550, height - 340)
    c.drawString(400, height - 360, "Base imponible:")
    c.drawString(480, height - 360, "200,00 €")

    c.drawString(400, height - 380, "IVA (21%):")
    c.drawString(480, height - 380, "42,00 €")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(400, height - 400, "TOTAL:")
    c.drawString(480, height - 400, "242,00 €")

    # HAS VERIFACTU phrase (good!)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, height - 450, "VERIFACTU")

    # NO QR code (missing!)
    c.setFont("Helvetica", 8)
    c.drawString(50, height - 470, "Falta código QR - No completamente conforme")

    # NO hash (missing!)

    c.save()
    print(f"⚠️  Created partially compliant invoice: {filename}")
    return filename


def create_test_invoices():
    """Create all test invoices."""
    print("🏭 Creando facturas de prueba para VERIFACTU...")

    compliant = create_compliant_invoice()
    non_compliant = create_non_compliant_invoice()
    partial = create_partial_compliant_invoice()

    print("\n📋 Facturas creadas:")
    print(f"✅ Conforme VERIFACTU: {compliant}")
    print(f"❌ No conforme: {non_compliant}")
    print(f"⚠️  Parcialmente conforme: {partial}")

    print("\n🧪 Para probar:")
    print("1. Arranca el servidor: uv run uvicorn app.server:app --host 0.0.0.0 --port 8000")
    print("2. Genera token: uv run python -c \"from app.services.security.token import TokenService; print(TokenService().generate_token('test'))\"")
    print("3. Prueba validación VERIFACTU con estas facturas")
    print("4. Ve a http://localhost:8000/docs para API interactiva")

    return [compliant, non_compliant, partial]


if __name__ == "__main__":
    try:
        create_test_invoices()
    except ImportError as e:
        print(f"❌ Error: Falta dependencia {e}")
        print("Instala con: pip install reportlab qrcode[pil]")
    except Exception as e:
        print(f"❌ Error creando facturas: {e}")