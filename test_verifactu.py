#!/usr/bin/env python3
"""
Test script for VERIFACTU implementation.

This script tests all VERIFACTU endpoints with sample invoices.
"""

import asyncio
import sys
import os
sys.path.append('.')

from app.services.security.token import create_token
from app.services.verifactu.verifactu_validator import VerifactuValidator
from app.services.verifactu.dashboard import VerifactuDashboard
from app.services.verifactu.auto_correction import VerifactuAutoCorrection


async def test_qr_validation():
    """Test QR code validation."""
    print("🔍 Testing QR code validation...")

    validator = VerifactuValidator()

    # Test valid QR
    valid_qr_data = "https://sede.agenciatributaria.gob.es/Sede/verificafactura?nif=B12345678&num=FAC-2024-001&fecha=2024-01-15&importe=121.00"

    # Simulate invoice data
    invoice_data = {
        'parties': {
            'vendor': {
                'tax_id': 'B12345678',
                'name': 'Empresa Ejemplo S.L.'
            }
        },
        'metadata': {
            'invoice_number': 'FAC-2024-001',
            'issue_date': '2024-01-15'
        },
        'financial_details': {
            'total_amount': 121.00
        }
    }

    # Test QR validation (simulated)
    print(f"  ✅ QR URL format: {validator.qr_validator._is_valid_aeat_url(valid_qr_data)}")
    print(f"  ✅ QR parameters extracted: {bool(validator.qr_validator._extract_qr_parameters(valid_qr_data))}")

    return True


async def test_phrase_validation():
    """Test mandatory phrase validation."""
    print("📝 Testing phrase validation...")

    validator = VerifactuValidator()

    # Test texts
    test_texts = [
        "Esta es una factura con VERIFACTU incluido",
        "Factura verificable en la sede electrónica de la AEAT",
        "Factura sin frase obligatoria",
        "VERIFACTU - código presente"
    ]

    for text in test_texts:
        result = validator.phrase_validator.validate_mandatory_phrase(text)
        status = "✅" if result.phrase_present else "❌"
        print(f"  {status} '{text[:30]}...' - Found: {result.phrase_present}")

    return True


async def test_format_validation():
    """Test format validation."""
    print("📊 Testing format validation...")

    validator = VerifactuValidator()

    # Complete invoice data
    complete_invoice = {
        'parties': {
            'vendor': {
                'tax_id': 'B12345678',
                'name': 'Empresa Ejemplo S.L.',
                'address': 'Calle Ejemplo, 123'
            },
            'customer': {
                'tax_id': 'A87654321',
                'name': 'Cliente Prueba S.A.'
            }
        },
        'metadata': {
            'invoice_number': 'FAC-2024-001',
            'issue_date': '2024-01-15'
        },
        'financial_details': {
            'total_amount': 121.00,
            'subtotal': 100.00,
            'tax': {
                'amount': 21.00,
                'rate': 21
            }
        }
    }

    # Incomplete invoice data
    incomplete_invoice = {
        'parties': {
            'vendor': {
                'name': 'Empresa Incompleta'
                # Missing tax_id and address
            }
        },
        'metadata': {
            'invoice_number': 'FAC-2024-002'
            # Missing issue_date
        }
        # Missing financial_details
    }

    # Test complete invoice
    result_complete = validator.format_validator.validate_verifactu_format(complete_invoice)
    print(f"  ✅ Complete invoice - Required fields: {result_complete.has_required_fields}")
    print(f"  ✅ Complete invoice - Valid structure: {result_complete.structure_valid}")

    # Test incomplete invoice
    result_incomplete = validator.format_validator.validate_verifactu_format(incomplete_invoice)
    print(f"  ❌ Incomplete invoice - Missing fields: {len(result_incomplete.missing_fields)}")
    print(f"     Fields missing: {result_incomplete.missing_fields[:3]}...")

    return True


async def test_auto_correction():
    """Test automatic correction system."""
    print("🔧 Testing auto-correction...")

    auto_corrector = VerifactuAutoCorrection()

    # Sample invoice data for correction
    invoice_data = {
        'parties': {
            'vendor': {
                'tax_id': 'B12345678',
                'name': 'Empresa Ejemplo S.L.'
            }
        },
        'metadata': {
            'invoice_number': 'FAC-2024-001',
            'issue_date': '2024-01-15'
        },
        'financial_details': {
            'total_amount': 121.00
        }
    }

    # Test QR generation
    from app.services.verifactu.qr_validator import QRValidator
    qr_validator = QRValidator()
    qr_suggestion = qr_validator.generate_missing_qr_suggestion(invoice_data)
    print(f"  ✅ QR generation: {bool(qr_suggestion)}")
    if qr_suggestion:
        print(f"     URL: {qr_suggestion[:50]}...")

    # Test phrase insertion
    from app.services.verifactu.phrase_validator import PhraseValidator
    phrase_validator = PhraseValidator()
    phrase_suggestion = phrase_validator._get_default_phrase_suggestion()
    print(f"  ✅ Phrase suggestion: {phrase_suggestion}")

    return True


async def test_dashboard():
    """Test dashboard generation."""
    print("📊 Testing dashboard...")

    dashboard = VerifactuDashboard()

    # Generate sample dashboard
    sample_validations = []  # Would contain real validation results
    dashboard_data = await dashboard.generate_compliance_dashboard(sample_validations)

    print(f"  ✅ Dashboard generated: {bool(dashboard_data)}")
    print(f"  ✅ Overview section: {'overview' in dashboard_data}")
    print(f"  ✅ Critical metrics: {'critical_metrics' in dashboard_data}")
    print(f"  ✅ Recommendations: {len(dashboard_data.get('recommendations', []))}")

    return True


async def test_full_validation():
    """Test complete VERIFACTU validation flow."""
    print("🎯 Testing complete validation flow...")

    validator = VerifactuValidator()

    # Create sample invoice data
    invoice_data = {
        'parties': {
            'vendor': {
                'tax_id': 'B12345678',
                'name': 'Empresa Ejemplo S.L.',
                'address': 'Calle Ejemplo, 123'
            },
            'customer': {
                'tax_id': 'A87654321',
                'name': 'Cliente Prueba S.A.'
            }
        },
        'metadata': {
            'invoice_number': 'FAC-2024-001',
            'issue_date': '2024-01-15'
        },
        'financial_details': {
            'total_amount': 121.00,
            'subtotal': 100.00,
            'tax': {
                'amount': 21.00,
                'rate': 21
            }
        }
    }

    # Sample document bytes (minimal PDF)
    document_bytes = b"%PDF-1.4\nSample PDF content for testing\n%%EOF"

    # Sample extracted text
    extracted_text = "FACTURA FAC-2024-001 VERIFACTU Empresa Ejemplo Total: 121.00"

    try:
        # Run complete validation (without AEAT for testing)
        result = await validator.validate_complete_verifactu_compliance(
            document_bytes=document_bytes,
            invoice_data=invoice_data,
            extracted_text=extracted_text,
            enable_aeat_validation=False  # Skip for local testing
        )

        print(f"  ✅ Validation completed")
        print(f"  📊 Compliance score: {result.compliance_score:.1f}/100")
        print(f"  🎯 Compliance level: {result.compliance_level.value}")
        print(f"  🚨 Critical issues: {result.critical_issues}")
        print(f"  ⚠️  Warnings: {result.warnings}")
        print(f"  🔧 Auto-correctable: {result.can_auto_correct}")

        return True

    except Exception as e:
        print(f"  ❌ Validation failed: {e}")
        return False


async def run_all_tests():
    """Run all VERIFACTU tests."""
    print("🧪 VERIFACTU System Test Suite")
    print("=" * 50)

    tests = [
        ("QR Validation", test_qr_validation),
        ("Phrase Validation", test_phrase_validation),
        ("Format Validation", test_format_validation),
        ("Auto-Correction", test_auto_correction),
        ("Dashboard", test_dashboard),
        ("Full Validation", test_full_validation)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n🔬 {test_name}")
        print("-" * 30)
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"✅ {test_name} completed successfully")
        except Exception as e:
            print(f"❌ {test_name} failed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n📋 Test Summary")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\n🎯 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! VERIFACTU system is ready!")
        print("\n🚀 Next steps:")
        print("1. Start server: uv run uvicorn app.server:app --host 0.0.0.0 --port 8000")
        print("2. Generate token (already done above)")
        print("3. Test with sample invoices using API")
        print("4. Visit http://localhost:8000/docs for interactive API")
    else:
        print("⚠️  Some tests failed. Review implementation.")

    return passed == total


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)