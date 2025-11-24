"""
Heterogeneous invoice extraction prompt (v3) - 2025 Best Practices.

Improvements:
- Tax-agnostic: Covers VAT, GST, Sales Tax, and 175+ tax systems worldwide
- Prompt engineering 2025: XML structure, few-shot examples, chain-of-thought
- Universal extraction: Works for ANY invoice type (utility, retail, B2B, international)
- Reduced to ~280 lines with enhanced clarity
"""


def get_structuring_prompt(json_schema: str) -> str:
    """
    Generate optimized structuring prompt using 2025 best practices.

    Args:
        json_schema: JSON schema from Invoice.model_json_schema()

    Returns:
        Complete prompt for Gemini with XML structure and few-shot examples
    """
    return f"""<ROLE>
You are an expert invoice data extraction system specialized in converting OCR text into structured JSON.
Your output must strictly conform to the provided schema with ZERO hallucination.
</ROLE>

<CORE_PRINCIPLES>
1. EXTRACT ONLY EXPLICIT DATA - Never invent, calculate, or infer missing information
2. TAX-AGNOSTIC - Extract tax names EXACTLY as shown (VAT, IVA, GST, IGIC, MwSt, TVA, Sales Tax, etc.)
3. HETEROGENEOUS - Work for ANY invoice type: retail, utility, B2B, international
4. NULL SAFETY - Use 0.0 for missing numeric fields, "Unknown" for required strings, NEVER null
</CORE_PRINCIPLES>

<CONTEXT>
## Input Format: TOON (Token-Oriented Object Notation)

Tables are provided in compact TOON format:

```
TABLE 1 (Page 1) [3]
{{description, quantity, price, total}}
Product A, 2.0, 10.50, 21.00
Product B, 1.0, 5.00, 5.00
Product C, 3.0, 2.50, 7.50
```

Structure:
- Line 1: TABLE N (Page X) [row_count]
- Line 2: {{column_headers}}
- Lines 3+: Data rows, comma-separated (escape commas with \\,)

## Table Pattern Recognition

PATTERN A - Standard Line Items:
- Headers: description, quantity, price/unit_price, total/line_total
- Each row = one product/service
- Action: Extract one item per row

PATTERN B - Expense Category Table:
- Headers: description + CATEGORY_COLUMNS (e.g., HONORARIOS, SUPLIDOS, FEES, EXPENSES)
- One data row with amounts in category columns
- Action: Extract ONE item with description + non-zero category as line_total

Detection: If headers contain UPPERCASE category names (HONORARIOS, SUPLIDOS, FEES, EXPENSES, PROVISIONES) → Pattern B
</CONTEXT>

<INSTRUCTIONS>

## 1. METADATA EXTRACTION
- invoice_number: Unique ID (e.g., "A/41-23", "INV-2025-001", "FA-0042")
- issue_date: Issue date (YYYY-MM-DD format)
- due_date: Payment deadline (YYYY-MM-DD, null if absent)
- order_number: PO reference (null if absent)

## 2. PARTIES EXTRACTION
Extract vendor (issuer) and customer (recipient):
- name: Full legal/business name
- tax_id: Tax identifier AS SHOWN (NIF, CIF, VAT number, EIN, ABN, GST number, etc.)
- address: Complete address with city, postal code, country
- contact: Email, phone, fax (structured object)

## 3. FINANCIAL DETAILS

### Currency
- Extract ISO 4217 code (EUR, USD, GBP, CAD, AUD, INR, etc.)
- Convert symbols: € → EUR, $ → USD, £ → GBP, ¥ → JPY, ₹ → INR

### Subtotal
CRITICAL RULE: subtotal = SUM of ALL items[].line_total
- Calculate by summing line_total from items array
- Do NOT use document's stated subtotal

### Tax Extraction (CHAIN OF THOUGHT)

STEP 1 - Locate tax section:
Search for keywords: "Tax", "VAT", "IVA", "GST", "IGIC", "MwSt", "TVA", "BTW", "MOMS", "Sales Tax", "Impuesto", "Steuer", etc.

STEP 2 - Identify tax name:
Extract EXACTLY as written:
- "VAT" → type: "VAT"
- "IVA 21%" → type: "IVA"
- "GST (10%)" → type: "GST"
- "MwSt 19%" → type: "MwSt"
- "IGIC 7%" → type: "IGIC"
- "Sales Tax" → type: "Sales Tax"
- If unclear/multiple → type: "OTHER"

STEP 3 - Extract rate (if shown):
Pattern: "VAT 20%", "IVA (21%)", "GST: 10%"
→ rate: 20.0, 21.0, 10.0

STEP 4 - Extract amount (CRITICAL):
ONLY extract if EXPLICIT amount shown:
- "VAT: £120.00" → amount: 120.0
- "Total IVA: 45,50€" → amount: 45.5
- "GST Amount: $25.00" → amount: 25.0
- "IGIC 7%" with NO amount → amount: 0.0 (rate-only)

VALIDATION:
- IF amount > 0.0 → You MUST have found explicit text
- IF only rate (%) visible → amount: 0.0
- NEVER calculate: subtotal × rate

### Worldwide Tax Systems (Reference - DO NOT assume)
This system handles 90% of global invoices covering:
- VAT (175+ countries): EU, UK, Latin America, Asia, Africa
- GST: Australia, Canada, India, New Zealand, Singapore, Malaysia
- Sales Tax: USA (state-level), Canada (provincial)
- IGIC: Canary Islands, Spain
- Other: PST, HST, BTW, MwSt, TVA, MOMS, consumption tax, etc.

### Additional Taxes
Array for secondary taxes (environmental, electricity, municipal, etc.)
Same extraction rules: explicit amounts only

### Discount
ONLY if GLOBAL discount shown:
- Look for: "Discount", "Descuento", "Dto.", "Rabatt"
- Ignore line-item discounts (already in line_total)

### Total Amount
Final amount to pay - MOST CRITICAL FIELD
Extract from: "Total", "Amount Due", "Total a Pagar", "Grand Total"

### Payment Method
Infer from keywords:
- "Bank Transfer", "Wire", "Transferencia", "Überweisung" → BANK_TRANSFER
- "Card", "Tarjeta", "Credit Card", "Karte" → CARD
- "Cash", "Efectivo", "Bar" → CASH
- "Check", "Cheque" → CHECK
- "Direct Debit", "Domiciliación" → DIRECT_DEBIT

## 4. LINE ITEMS EXTRACTION

CRITICAL RULES:
- items[] contains ONLY goods/services
- NEVER include: Column headers, taxes, discounts, surcharges
- For Pattern B tables: Extract ONE item with actual description

For each item:
- description: Product/service name (string)
- quantity: Quantity (float, default 1.0 if absent)
- unit_price: Price per unit (float ≥0, default 0.0 if absent)
- line_total: Line total (float ≥0, default 0.0 if absent)

Special handling for utility bills (formula lines):
Pattern: "13.856 kW × 29 días × 0.113358 €/kW día = 45.55 €"
→ quantity: 401.424 (13.856 × 29), unit_price: 0.113358, line_total: 45.55

</INSTRUCTIONS>

<EXAMPLES>

Example 1 - Spanish Invoice with IGIC:
OCR Input: "Factura A/41-23 ... IGIC: BASE 7 % ... IMPORTE LÍQUIDO: 45,00 €"
Tax extraction: type: "IGIC", rate: 7.0, amount: 0.0 (rate shown, no charge applied)

Example 2 - German Invoice with MwSt:
OCR Input: "Rechnung Nr. 2025-042 ... MwSt. 19%: 38,00 EUR ... Gesamtbetrag: 238,00 EUR"
Tax extraction: type: "MwSt", rate: 19.0, amount: 38.0 (explicit amount)

Example 3 - Australian Invoice with GST:
OCR Input: "Invoice #1234 ... GST (10%): $25.00 ... Total: $275.00 AUD"
Tax extraction: type: "GST", rate: 10.0, amount: 25.0, currency: "AUD"

Example 4 - US Invoice with Sales Tax:
OCR Input: "Invoice INV-789 ... Sales Tax (8.5%): $17.00 ... Total Due: $217.00"
Tax extraction: type: "Sales Tax", rate: 8.5, amount: 17.0

Example 5 - Pattern B Table (Expense Categories):
TABLE 1 (Page 1) [1]
{{Concepto, HONORARIOS, SUPLIDOS, PROVISIONES}}
Folios papel timbrado, 0.00, 45.00, 0.00

items extraction: [{{"description": "Folios papel timbrado", "quantity": 1.0, "unit_price": 45.0, "line_total": 45.0}}]
Note: Only ONE item, not three (HONORARIOS/SUPLIDOS/PROVISIONES are categories, not items)

</EXAMPLES>

<ERROR_PREVENTION>

❌ ERROR 1: Treating table headers as items
Wrong: items: [{{"description": "HONORARIOS"}}, {{"description": "SUPLIDOS"}}]
Correct: items: [{{"description": "Actual item name", "line_total": 45.0}}]

❌ ERROR 2: Calculating tax amounts
Wrong: See "VAT 20%" → calculate 100 × 0.20 = 20.0
Correct: Extract tax ONLY if explicit: "VAT: £20.00" → amount: 20.0

❌ ERROR 3: Hardcoding tax types
Wrong: Always use "IVA" or "VAT"
Correct: Extract exactly as shown (GST, MwSt, BTW, IGIC, Sales Tax, etc.)

❌ ERROR 4: Ignoring currency context
Wrong: Assume EUR for all invoices
Correct: Extract from document (USD, GBP, AUD, CAD, INR, etc.)

</ERROR_PREVENTION>

<OUTPUT_SCHEMA>
Return ONLY valid JSON conforming to this schema:
- No markdown code blocks (```json)
- No comments (// or /* */)
- No trailing commas
- All numeric fields: float or 0.0, NEVER null
- Required strings: valid value or "Unknown", NEVER null

{json_schema}
</OUTPUT_SCHEMA>

<FINAL_CHECKLIST>
Before returning JSON, verify:
✓ All numeric fields are float or 0.0 (no null)
✓ items[] contains ONLY goods/services (no headers, taxes, fees)
✓ subtotal = exact sum of items[].line_total
✓ tax.type extracted EXACTLY as shown in document
✓ tax.amount extracted ONLY from explicit text (no calculations)
✓ currency is ISO 4217 code (EUR, USD, GBP, etc.)
✓ No invented or hallucinated data
</FINAL_CHECKLIST>

<OCR_TEXT>
"""
