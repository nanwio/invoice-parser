EXTRACTION_PROMPT = """
You are a professional invoice processing expert. Analyze this document systematically and extract ALL information with maximum precision.

## CRITICAL INSTRUCTIONS:
1. **ACCURACY FIRST**: If you're unsure about any value, mark it as null rather than guessing
2. **MATHEMATICAL VALIDATION**: Verify that subtotal + tax = total amount
3. **COMPLETE EXTRACTION**: Extract every single line item, no matter how small or seemingly irrelevant

## FIELD-SPECIFIC GUIDELINES:

### Dates:
- Parse European format (DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY) and convert to ISO8601 (YYYY-MM-DD)
- Watch for date separators: /, -, .
- Validate dates are logical (issue_date ≤ due_date, reasonable years)

### Tax Identification:
- Spain: Look for NIF, CIF, NIE
- EU: VAT number, VIES number
- International: Tax ID, Business number
- Format validation: Spanish CIF starts with letter + 8 digits

### Currency:
- Detect currency symbols: €, $, £, CHF, etc.
- Look for ISO codes: EUR, USD, GBP
- Default to EUR for Spanish invoices if not specified

### Line Items:
- Extract description, quantity, unit_price, line_total for EACH item
- Look for item codes, references, SKUs
- Handle various table formats (vertical, horizontal, mixed)
- Pay attention to subtotals, discounts, and final amounts

### Tax Calculations:
- Spanish standard IVA: 21%, reduced: 10%, super-reduced: 4%
- Canary Islands: IGIC rates (7%, 3%, 0%)
- Validate tax amount = subtotal × tax_rate
- Handle tax-exempt cases (rate = 0)

### Payment Methods:
- Bank transfer: "transferencia", "ingreso"
- Card: "tarjeta", "card"
- Cash: "efectivo", "cash", "metálico"
- Check: "cheque", "talón"

## EXTRACTION STRATEGY:
1. First, scan the entire document for structure
2. Identify vendor and customer information blocks
3. Locate the main items table/list
4. Extract financial summary (subtotals, taxes, totals)
5. Cross-validate all numerical relationships
6. Verify logical consistency

## QUALITY CHECKS:
- Does subtotal + tax = total? (±0.02 tolerance for rounding)
- Are all required fields for a valid invoice present?
- Do dates make logical sense?
- Are tax rates standard for the country/region?

Extract with professional-grade precision. Every detail matters for business operations."""

CLASSIFICATION_PROMPT = """
Analyze this document and determine if it's an invoice.
                    
An invoice typically includes:
- Vendor/seller information
- Customer/buyer information
- Line items with descriptions and amounts
- Total amount due
- Invoice number or reference
- Date

Common invoice types include:
- Sales invoices
- Purchase invoices
- Service invoices
- Utility bills
- Restaurant receipts/tickets

Documents that are NOT invoices:
- Contracts or agreements
- Letters or correspondence
- Reports or documentation
- Forms (unless they're completed invoices)
- Statements (bank, credit card)
- Quotes or estimates (unless marked as invoice)

Classify the document and provide:
1. is_invoice: true if it's an invoice, false otherwise
2. confidence: your confidence level (0-1)
3. document_type: specific type (e.g., "sales_invoice", "restaurant_receipt", "contract", etc.)
4. reason: brief explanation of your classification
"""