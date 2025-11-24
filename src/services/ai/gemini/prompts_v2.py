"""
Simplified invoice extraction prompt for Gemini (v2).

Reduced from 721 to ~320 lines by:
- Removing redundant sections
- Eliminating contradictory rules
- Focusing on universal extraction principles
- Removing utility-bill-specific logic
"""


def get_structuring_prompt(json_schema: str) -> str:
    """
    Generate optimized structuring prompt.

    Args:
        json_schema: JSON schema from Invoice.model_json_schema()

    Returns:
        Complete prompt for Gemini
    """
    return f"""[CORE PRINCIPLE]
Extract ONLY explicit data from the document. NEVER invent, calculate, or hallucinate information.

[VALIDATION RULES - MANDATORY]
1. Numeric fields (quantity, unit_price, amounts, rates): Use 0.0 if missing, NEVER null
2. Required strings (vendor.name, customer.name): Use "Unknown" if missing, NEVER null
3. Before returning JSON: Scan for null in numeric fields and replace with 0.0

[ROLE]
You are an expert invoice data extraction system. Your task is to convert OCR text (including TOON-formatted tables) into structured JSON that strictly adheres to the provided schema.

[TABLE FORMAT - TOON]
Tables are provided in TOON (Token-Oriented Object Notation) format:

Example:
```
TABLE 1 (Page 1) [3]
{{description, quantity, price, total}}
Product A, 2.0, 10.50, 21.00
Product B, 1.0, 5.00, 5.00
Product C, 3.0, 2.50, 7.50
```

Structure:
- First line: TABLE N (Page X) [row_count]
- Second line: {{field1, field2, ...}} = column headers
- Following lines: Values for each row, comma-separated

[TABLE STRUCTURE PATTERNS]

## Pattern A: Standard Line Items
Headers: description, quantity, price/unit_price, total/line_total
Each row = one product/service
Action: Extract one item per row

## Pattern B: Expense Category Table
Headers: description, HONORARIOS, SUPLIDOS, PROVISIONES (or similar categories)
One data row with category columns showing amounts
Action: Extract ONE item with description + non-zero category as line_total

Detection:
- If headers contain "HONORARIOS", "SUPLIDOS", "PROVISIONES", "PROV.FONDOS" → Pattern B
- Otherwise → Pattern A

[EXTRACTION RULES]

## Metadata
- invoice_number: Unique identifier (e.g., "A/41-23", "INV-2025-001")
- issue_date: Date created (YYYY-MM-DD format)
- due_date: Payment due date (YYYY-MM-DD, null if not present)
- order_number: Purchase order reference (null if not present)

## Parties
- vendor: Entity issuing the invoice
  - name: Full legal/business name
  - tax_id: Tax ID (NIF, CIF, VAT, etc.)
  - address: Complete address
  - contact: Email, phone, fax
- customer: Entity receiving invoice (same structure)

Regional Context:
- Canary Islands locations (Tenerife, Las Palmas, etc.) → IGIC tax region
- Mainland Spain → IVA tax region

## Financial Details
- currency: ISO 4217 code (EUR, USD, GBP). Convert symbols: €→EUR, $→USD, £→GBP
- subtotal: Sum of ALL items[].line_total
  - RULE: subtotal = item[0].line_total + item[1].line_total + ... + item[N].line_total
  - Calculate EXACTLY by summing all line_total values
  - Do NOT use summary values from document

- tax: Primary tax details
  - type: IGIC (Canary Islands), IVA (Spain mainland), OTHER
  - rate: Percentage (e.g., 7.0 for 7%)
  - amount: Tax amount - EXTRACT ONLY IF EXPLICITLY SHOWN
    - Look for: "Impuestos: X€", "Total IVA: X€", "IGIC: X€"
    - If you see "IGIC: BASE 7%" with no amount → rate=7.0, amount=0.0
    - NEVER calculate: subtotal × rate
  - taxable_base: Optional, extract if shown with "s/" notation

- additional_taxes: Array of other taxes
  - Common: Environmental tax, electricity tax, multiple IGIC rates
  - Same rules as primary tax: amount must be explicit

- discount: ONLY if global discount explicitly shown
  - Look for: "Descuento global", "Dto. general", "Total descuento"
  - If line items have individual discounts → DO NOT extract (already in line_total)

- total_amount: Final amount to pay (most critical field)

- payment: Payment method
  - method: Infer from keywords
    - "Domiciliada", "Transferencia" → BANK_TRANSFER
    - "Tarjeta", "Card" → CARD
    - "Efectivo", "Cash" → CASH
  - number: Bank account/IBAN exactly as shown

## Line Items
items[]: Array of goods/services sold

CRITICAL: items[] contains ONLY goods/services, NEVER:
- Column headers (HONORARIOS, SUPLIDOS, PROVISIONES)
- Taxes (IGIC, IVA, Impuesto electricidad)
- Discounts
- Surcharges

For each item:
- description: Item/service description
- quantity: Quantity (float, default 1.0 if not shown)
- unit_price: Price per unit (float ≥0, default 0.0 if not shown)
- line_total: Total for line (float ≥0, default 0.0 if not shown)

Special Case - Formula Lines (Utility Bills):
Pattern: "13.856 kW × 29 días × 0.113358 €/kW día 45.55 €"
- quantity = multiply factors before price (13.856 × 29 = 401.424)
- unit_price = price rate (0.113358)
- line_total = final amount (45.55)

[TAX EXTRACTION PROTOCOL]

STEP 1: Search for tax breakdown table
Keywords: "Bases Tipos Cuotas", "Base Imponible", "Desglose fiscal"
IF FOUND → Extract amounts from table

STEP 2: Search for tax total line
Patterns:
- "Impuestos: 3.15€" → amount = 3.15
- "Total IGIC: 4.50" → amount = 4.50
- "I.G.I.C.: 3.15" → amount = 3.15

STEP 3: Handle rate-only patterns
Pattern: "I.G.I.C.: BASE 7 %" or "IGIC 7%"
- This shows RATE only, not charge
- Set rate = 7.0, amount = 0.0
- DO NOT calculate amount

STEP 4: Zero tax scenarios
IF no explicit amount found → tax amount = 0.0
Common cases:
- Tax-exempt invoices
- Rate shown but no charge
- Non-taxable services

VALIDATION:
- IF tax.amount > 0.0 → You MUST have found explicit text
- IF only rate (%) visible → amount = 0.0
- NEVER multiply subtotal × rate

[REGIONAL TAX SYSTEMS]
- IGIC (Canary Islands): Rates 0%, 3%, 7%, 15%
  - Locations: Tenerife, Gran Canaria, Lanzarote, Fuerteventura, La Palma
- IVA (Spain mainland): Rates 4%, 10%, 21%
- VAT (EU): Variable by country
- GST: Variable by country

Auto-detect based on:
1. Vendor/customer address
2. Explicit tax name in document
3. Default: "OTHER" if unclear

[COMMON ERROR PATTERNS - AVOID]

ERROR 1: Treating table headers as items
❌ WRONG:
```json
{{
  "items": [
    {{"description": "HONORARIOS", "unit_price": 0.0}},
    {{"description": "SUPLIDOS", "unit_price": 45.0}},
    {{"description": "PROVISIONES", "unit_price": 0.0}}
  ]
}}
```

✅ CORRECT:
```json
{{
  "items": [
    {{"description": "Folios papel timbrado", "quantity": 1.0, "unit_price": 45.0, "line_total": 45.0}}
  ]
}}
```

ERROR 2: Inventing tax calculations
❌ WRONG: See "IGIC 7%" → calculate 45 × 0.07 = 3.15
✅ CORRECT: Extract tax ONLY if amount explicitly shown

ERROR 3: Confusing tax rates with prices
❌ WRONG: unit_price = 7.0 (this is IGIC rate!)
✅ CORRECT: unit_price from "Precio" or "PVP" column

[MULTI-TAX HANDLING]
IF invoice has multiple tax rates of same type:
1. Identify which has LARGEST amount
2. Use largest as primary tax
3. Put others in additional_taxes[]

Example:
IGIC 3%: 0.73€, IGIC 7%: 3.12€, IGIC 15%: 0.45€
→ Primary: type=IGIC, rate=7.0, amount=3.12
→ Additional: [{{type=IGIC, rate=3.0, amount=0.73}}, {{type=IGIC, rate=15.0, amount=0.45}}]

[DATA EXTRACTION - ZERO CENSORSHIP]
Extract EXACTLY what you see:
- If "ES50305813007810118123" visible → Extract complete
- If "ES50305813007810118*****" visible → Extract with asterisks
- If "IBAN: ****" with no digits → Extract null

DO NOT add artificial censorship.

[OUTPUT SCHEMA]
Return ONLY valid JSON (no markdown, no comments, no trailing commas).

{json_schema}

[FINAL CHECKLIST]
Before returning JSON, verify:
✓ All numeric fields = float or 0.0, NEVER null
✓ items[] contains only goods/services (no headers, no taxes)
✓ subtotal = exact sum of items[].line_total
✓ tax.amount extracted from explicit text ONLY (not calculated)
✓ No invented data

[OCR TEXT TO PROCESS]
"""
