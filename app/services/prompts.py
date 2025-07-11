EXTRACTION_PROMPT = """
Extract all information from this invoice.

- Parse dates using European format (DD/MM/YYYY) and convert to ISO8601
- Look for tax_id in fields like NIF, CIF, VAT number
- For Spanish invoices, "referencia" means item_id
- If tax rate is 0, use tax type EXEMPT or OTHER
- Leave fields as null if not found
- Extract ALL line items found in the invoice

Focus on accuracy and completeness.
"""

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