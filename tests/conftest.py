"""Shared fixtures for the test suite."""
import pytest

from src.domain.models import Invoice
from src.domain.models.party import Address, Contact, InvoiceParties, Party
from src.domain.models.item import LineItem, Metadata
from src.domain.models.financial import (
    FinancialDetails,
    Tax,
    Withholding,
    Discount,
    Surcharge,
    Payment,
    BankPaymentMethod,
)


def _build_invoice(
    items: list[LineItem],
    subtotal: float,
    tax_amount: float,
    total: float,
    *,
    discount: Discount | None = None,
    withholding: Withholding | None = None,
    surcharges: list[Surcharge] | None = None,
    vendor_name: str = "Empresa Emisora S.L.",
    customer_name: str = "Cliente Receptor S.A.",
) -> Invoice:
    """Build an Invoice instance from minimal parameters."""
    vendor = Party(
        name=vendor_name,
        tax_id="B12345678",
        address=Address(street="Calle Mayor 1", city="Oviedo", country="ES"),
        contact=Contact(email="emisor@example.com"),
    )
    customer = Party(name=customer_name, tax_id="A87654321")
    return Invoice(
        metadata=Metadata(
            invoice_number="2025/001",
            issue_date="2025-01-15",
        ),
        parties=InvoiceParties(vendor=vendor, customer=customer),
        items=items,
        financial_details=FinancialDetails(
            currency="EUR",
            subtotal=subtotal,
            tax=Tax(type="IVA", rate=21.0, amount=tax_amount),
            discount=discount,
            withholding=withholding,
            surcharges=surcharges or [],
            total_amount=total,
            payment=Payment(method=BankPaymentMethod.BANK_TRANSFER),
        ),
    )


@pytest.fixture
def valid_invoice() -> Invoice:
    """A consistent invoice: subtotal = sum(items), total = subtotal + tax."""
    items = [
        LineItem(description="Servicio A", quantity=1, unit_price=100.0, line_total=100.0),
        LineItem(description="Servicio B", quantity=2, unit_price=50.0, line_total=100.0),
    ]
    return _build_invoice(items=items, subtotal=200.0, tax_amount=42.0, total=242.0)


@pytest.fixture
def invoice_with_subtotal_mismatch() -> Invoice:
    """Items sum to 200 but subtotal declared as 195 (within auto-correction range)."""
    items = [
        LineItem(description="Servicio A", quantity=1, unit_price=100.0, line_total=100.0),
        LineItem(description="Servicio B", quantity=2, unit_price=50.0, line_total=100.0),
    ]
    return _build_invoice(items=items, subtotal=195.0, tax_amount=42.0, total=242.0)


@pytest.fixture
def invoice_with_total_mismatch() -> Invoice:
    """Subtotal matches items but total does not match subtotal + tax."""
    items = [
        LineItem(description="Servicio A", quantity=1, unit_price=100.0, line_total=100.0),
    ]
    return _build_invoice(items=items, subtotal=100.0, tax_amount=21.0, total=150.0)


@pytest.fixture
def invoice_missing_vendor_name() -> Invoice:
    """Invoice with an empty vendor name (should trigger required-field error)."""
    items = [
        LineItem(description="Servicio A", quantity=1, unit_price=100.0, line_total=100.0),
    ]
    invoice = _build_invoice(items=items, subtotal=100.0, tax_amount=21.0, total=121.0)
    invoice.parties.vendor.name = ""
    return invoice


@pytest.fixture
def invoice_zero_total() -> Invoice:
    """Invoice with total_amount = 0 (should trigger required-field error)."""
    items = [
        LineItem(description="Servicio gratuito", quantity=1, unit_price=0.0, line_total=0.0),
    ]
    return _build_invoice(items=items, subtotal=0.0, tax_amount=0.0, total=0.0)
