"""Auto-corrects IVA to IGIC for Canary Islands invoices."""
from loguru import logger
from src.domain.models import Invoice, TaxRateType


class CanaryTaxFixer:
    """Detects and fixes Canary Islands tax type."""

    CANARY_ISLANDS_KEYWORDS = [
        'canarias', 'canary', 'las palmas', 'tenerife', 'la palma',
        'gran canaria', 'fuerteventura', 'lanzarote', 'la laguna',
        'santa cruz', 'la gomera', 'el hierro'
    ]

    @classmethod
    def apply(cls, invoice: Invoice) -> Invoice:
        """Fix IVA → IGIC if invoice is from Canary Islands."""
        if invoice.financial_details.tax.type == TaxRateType.IGIC:
            return invoice

        is_canary = False
        reason = None

        # Check vendor location
        if invoice.parties.vendor.address:
            vendor_location = (
                f"{invoice.parties.vendor.address.city or ''} "
                f"{invoice.parties.vendor.address.state or ''}"
            ).lower()
            if any(kw in vendor_location for kw in cls.CANARY_ISLANDS_KEYWORDS):
                is_canary = True
                reason = f"vendor location: {vendor_location}"

        # Check customer location
        if not is_canary and invoice.parties.customer.address:
            customer_location = (
                f"{invoice.parties.customer.address.city or ''} "
                f"{invoice.parties.customer.address.state or ''}"
            ).lower()
            if any(kw in customer_location for kw in cls.CANARY_ISLANDS_KEYWORDS):
                is_canary = True
                reason = f"customer location: {customer_location}"

        # Check notes
        if not is_canary and invoice.notes:
            if 'igic' in invoice.notes.lower():
                is_canary = True
                reason = "IGIC mentioned in notes"

        # Check typical IGIC rates
        if not is_canary:
            tax_rate = invoice.financial_details.tax.rate
            if tax_rate in [3.0, 7.0, 15.0]:
                if invoice.parties.vendor.address and invoice.parties.vendor.address.country:
                    country = invoice.parties.vendor.address.country.lower()
                    if 'esp' in country or 'spain' in country or country == 'es':
                        is_canary = True
                        reason = f"typical IGIC rate ({tax_rate}%) in Spanish context"

        # Apply correction
        if is_canary and invoice.financial_details.tax.type == TaxRateType.IVA:
            logger.warning(f"CORRECTION: IVA → IGIC (detected: {reason})")
            invoice.financial_details.tax.type = TaxRateType.IGIC

            # Fix additional taxes too
            if invoice.financial_details.additional_taxes:
                for tax in invoice.financial_details.additional_taxes:
                    if tax.type == TaxRateType.IVA:
                        logger.warning("CORRECTION: Additional tax IVA → IGIC")
                        tax.type = TaxRateType.IGIC

        return invoice
