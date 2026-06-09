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
5. OCR ERROR TOLERANCE - Recognize common OCR errors and interpret intelligently (see OCR_CORRECTIONS)
</CORE_PRINCIPLES>

<OCR_CORRECTIONS>
## Common OCR Errors to Recognize

The input text comes from OCR which may have errors. Apply these corrections:

### Spanish Date Formats
CRITICAL: Spanish dates use "de" as separator: "1 de 3 de 2023" = March 1, 2023
- Pattern: "[day] de [month] de [year]" where month is 1-12
- "1 de 3 de 2023" → 2023-03-01 (March 1st, NOT January 3rd)
- "15 de 12 de 2024" → 2024-12-15 (December 15th)
- "1.3.2023" or "1/3/2023" in Spanish = 2023-03-01 (day/month/year, NOT month/day/year)

### Common Character Substitutions
- "0" ↔ "O" (zero vs letter O)
- "1" ↔ "l" ↔ "I" (one vs lowercase L vs uppercase i)
- "5" ↔ "S"
- "8" ↔ "B"
- "." ↔ "," (decimal separators)
- "€" may appear as "C" or missing
- "ñ" may appear as "n"
- "á/é/í/ó/ú" may lose accents

### Business Name Corrections
- "ECO" at start usually means "Estanco" (tobacco shop)
- "N°" or "No" or "N" before number = "Número" (Number)
- "Ma" or "M" before name = "María"
- "Tfno" or "Tfno." = "Teléfono" (Phone)
- "D.N.1" should be "D.N.I." (ID document)

### Spanish Invoice Terms
- "FACTURA" = Invoice
- "EXPENDEDURIA" = Licensed tobacco/stamp shop
- "Folios timbrados" = Stamped paper sheets
- "Suplidos" = Disbursements/expenses paid on behalf
- "Honorarios" = Professional fees
</OCR_CORRECTIONS>

<CONTEXT>
## Input Format: Spatial Zone Markers

The OCR text is organized into DOCUMENT ZONES based on spatial position analysis:

### Format A - Spatial Zone Classification (layout mode):
```
[VENDOR_HEADER]
Company name/logo at TOP of document = VENDOR

[CUSTOMER_INFO]
Right-aligned box with address, NIF = CUSTOMER data

[INVOICE_CONTENT]
Main invoice body - dates, items, amounts

[VENDOR_FOOTER]
Bottom of document - legal info, CIF registration = VENDOR's legal info
```

### Format B - Entity Classification (table mode):
```
[VENDOR_INFO - Has contact details]
Entity with email, phone, IBAN = VENDOR (invoice issuer)

[DOCUMENT_CONTENT]
All other content - dates, numbers, items, customer info
```

CRITICAL ZONE RULES:
- [VENDOR_HEADER] or [VENDOR_INFO - Has contact details] → Contains VENDOR information
- [CUSTOMER_INFO] → Contains CUSTOMER information (address, NIF in labeled box)
- [VENDOR_FOOTER] → Contains VENDOR's legal registration (CIF, "inscrita en Registro Mercantil")
- [INVOICE_CONTENT] or [DOCUMENT_CONTENT] → Main invoice data
- The entity with email/phone/IBAN is ALWAYS the VENDOR
- The entity in [CUSTOMER_INFO] box is ALWAYS the CUSTOMER

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

PATTERN C - Item Row With Auxiliary Columns (discount, tax rate):
Spanish wholesale/retail invoices frequently include extra columns between unit_price and the
final amount. Common layouts:
- `Codigo | Descripcion | Cantidad | Precio | Dto.% | Importe | IGIC%`
- `Reference | Description | Qty | Unit Price | Discount | Total | Tax Rate`

When the OCR stream for an item row contains MORE numeric values than {{quantity, unit_price, line_total}},
identify which value is the actual line_total using the following rules:

1. line_total is the value labeled "Importe", "Total", "Subtotal", "Amount", "Importe línea", "Net amount".
2. Values that look like SMALL PERCENTAGES (e.g., 3,0 / 5,0 / 7,0 / 10,00 / 0,00) sitting between
   unit_price and the final amount are almost always a DISCOUNT COLUMN (Dto.%) — IGNORE them.
3. Values that look like SMALL PERCENTAGES sitting AFTER the final amount are tax rate columns
   (IGIC%, IVA%, VAT%) — also IGNORE them when picking line_total.
4. PLAUSIBILITY CHECK: line_total should be ≈ quantity × unit_price × (1 - discount), where
   discount ∈ [0, 0.5]. If your candidate line_total is more than ~50% off from qty × unit_price,
   re-examine the row: a percentage-looking value is probably masquerading as line_total.

Example row (PATTERN C - synthetic):
OCR stream for a row: `SKU-001 Widget A 10,000 2,000 5,00 19,00 21,0`
                       ^id    ^desc     ^qty   ^price ^Dto% ^Total ^Tax%
Correct: {{item_id: "SKU-001", description: "Widget A", quantity: 10.0,
          unit_price: 2.0, line_total: 19.0}}
Wrong:   line_total: 5.0  (that's the discount column, not the total)

Sanity: 10 × 2,00 × 0,95 = 19,00 ✓ — confirms the discount interpretation.
</CONTEXT>

<INSTRUCTIONS>

## 1. METADATA EXTRACTION
- invoice_number: Unique ID (e.g., "A/41-23", "INV-2025-001", "FA-0042")
- issue_date: Issue date (YYYY-MM-DD format)
- due_date: Payment deadline (YYYY-MM-DD, null if absent)
- order_number: PO reference (null if absent)

## 2. PARTIES EXTRACTION

CRITICAL RULE FOR VENDOR vs CUSTOMER IDENTIFICATION:

STEP 1 - Identify the VENDOR (invoice issuer) using EMAIL DOMAIN MATCHING:
- The VENDOR is the company that ISSUES and SIGNS the invoice
- CRITICAL: If you see an email like "name@company.es", the company matching that domain is the VENDOR
- Example: "riveyan@riveyan.es" → Vendor name is "Riveyan" (capitalize the domain name)
- If vendor name is not explicitly found BUT email exists: USE THE EMAIL DOMAIN AS VENDOR NAME
  - "riveyan@riveyan.es" → vendor.name = "Riveyan"
  - "info@acme-corp.com" → vendor.name = "Acme Corp"
- The entity with email, phone, IBAN, or fax contact info is ALWAYS the VENDOR
- Spanish NIFs starting with "B" are companies (S.L., S.A.) - these are often vendors

STEP 2 - Identify the CUSTOMER (invoice recipient):
- The CUSTOMER is who RECEIVES and PAYS the invoice
- The CUSTOMER typically has NO contact details (no email, no phone in their section)
- Look for entities in [DOCUMENT_CONTENT] without associated email/phone
- Spanish NIFs starting with "V" are often "Comunidad de bienes" - can be customers
- Look for labels: "Cliente:", "Datos del cliente:", "Facturar a:" near a name

STEP 3 - Resolve conflicts with these PRIORITY RULES:
1. HEADER/LOGO: The company name at the TOP of the document (logo area) = VENDOR
2. LABELED BOX: Text with "N.I.F:" label followed by ID and address = CUSTOMER
3. EMAIL MATCH: If email domain matches company name → that company is VENDOR
4. CONTACT INFO: Entity with Tel/Email/IBAN = VENDOR
5. REGISTRATION: "inscrita en el Registro Mercantil" + CIF = VENDOR's CIF
6. If TWO company names appear: first one (header) = VENDOR, one in labeled box = CUSTOMER

CRITICAL LAYOUT PATTERN (Spanish invoices):
- TOP: Company logo/name = VENDOR (e.g., "UNIONAUDIT J.Y.E.")
- RIGHT BOX with "N.I.F:" label = CUSTOMER (e.g., "RIVEYAN, SLU" + "N.I.F: B38310322")
- BOTTOM FOOTER with "inscrita en el Registro Mercantil" = VENDOR's legal info
- Do NOT combine vendor name with customer name!

For Spanish invoices specifically:
- "email@company.es" + NIF near it = VENDOR (even if NIF is elsewhere in text)
- "EXPENDEDURIA N° XX" with DNI = VENDOR (self-employed)
- Entity without contact info in document = CUSTOMER
- "AVISO DE PAGO: ESXX..." (IBAN) belongs to the VENDOR (payment to vendor)
- "inscrita en el Registro Mercantil" + CIF = VENDOR's legal registration
- Logo/header company name = VENDOR
- Box with "N.I.F:" label + company name + address = CUSTOMER (labeled customer box)
- "CLIENTE Nº" indicates the following info is about the CUSTOMER

Extract for each party:
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
- Do NOT copy the "TOTAL" / "Total a Pagar" / "Grand Total" value into subtotal — that field is
  the gross total (subtotal + taxes - withholdings). The subtotal is strictly the pre-tax sum of items.
- Even if the OCR text has a bare number near a "Subtotal" label, IGNORE it and recompute from items.

### Tax Extraction (CHAIN OF THOUGHT)

PRIORITY: amount and rate are THE MOST CRITICAL FIELDS. Type is descriptive only.

STEP 1 - Locate tax section:
Search for keywords: "Tax", "VAT", "IVA", "GST", "IGIC", "MwSt", "TVA", "BTW", "MOMS", "Sales Tax", "Impuesto", "Steuer", etc.

STEP 2 - Extract amount (MOST CRITICAL):
ONLY extract if EXPLICIT amount shown:
- "VAT: £120.00" → amount: 120.0
- "Total IVA: 45,50€" → amount: 45.5
- "GST Amount: $25.00" → amount: 25.0
- "Impuesto electricidad: 2,16€" → amount: 2.16
- "IGIC 7%" with NO amount → amount: 0.0 (rate-only)

VALIDATION:
- IF amount > 0.0 → You MUST have found explicit text
- IF only rate (%) visible → amount: 0.0
- NEVER calculate: subtotal × rate

STEP 3 - Extract rate (CRITICAL):
Pattern: "VAT 20%", "IVA (21%)", "GST: 10%"
→ rate: 20.0, 21.0, 10.0

STEP 4 - Identify tax name (descriptive only):
Extract EXACTLY as written in document:
- "VAT" → type: "VAT"
- "IVA 21%" → type: "IVA"
- "Impuesto electricidad" → type: "Impuesto electricidad"
- "GST" → type: "GST"
- "IGIC reducido" → type: "IGIC reducido"

Note: Type can be ANY string - no restrictions. Focus on accuracy of amount and rate.

### Worldwide Tax Systems (Reference - DO NOT assume)
This system handles 90% of global invoices covering:
- VAT (175+ countries): EU, UK, Latin America, Asia, Africa
- GST: Australia, Canada, India, New Zealand, Singapore, Malaysia
- Sales Tax: USA (state-level), Canada (provincial)
- IGIC: Canary Islands, Spain
- Other: PST, HST, BTW, MwSt, TVA, MOMS, consumption tax, etc.

### Additional Taxes
Array for secondary taxes (environmental, electricity, municipal, multiple VAT rates, etc.)
- Extract type EXACTLY as shown: "Impuesto electricidad", "IGIC normal", "Environmental tax", etc.
- Same extraction rules: explicit amounts only, NEVER calculate
- Example: "Impuesto electricidad: 2.16€" → {{type: "Impuesto electricidad", rate: 0.0, amount: 2.16}}

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
- "Direct Debit", "Domiciliación", "Domiciliacion Bancaria" → DIRECT_DEBIT

## 4. LINE ITEMS EXTRACTION

CRITICAL RULES:
- items[] contains ONLY goods/services sold or provided
- NEVER include: Column headers, taxes, discounts, surcharges, fees, rentals, financing charges, or "otros"/"other"
- For Pattern B tables: Extract ONE item with actual description

DISTINCTION FOR UTILITY/COMPLEX INVOICES:
Include in items[]: "Potencia contratada", "Energía consumida", actual products/services
NEVER in items[]: "Recargo" (surcharge), "Alquiler" (rental), "Otros" (other), "Impuesto" (tax), or any fees

For each item:
- description: Product/service name (string)
- quantity: Quantity (float, default 1.0 if absent)
- unit_price: Price per unit (float ≥0, default 0.0 if absent)
- line_total: Line total (float ≥0, default 0.0 if absent)
  - Pick the value from the "Importe" / "Total" / "Amount" column, NOT from a discount or tax-rate column.
  - SANITY CHECK before finalising: line_total must satisfy
    `0.5 × (qty × unit_price) ≤ line_total ≤ 1.05 × (qty × unit_price)` (allows up to 50% line discount).
    If your candidate violates this and another nearby number does satisfy it, switch to that number.

Special handling for utility bills (formula lines):
Pattern: "13.856 kW × 29 días × 0.113358 €/kW día = 45.55 €"
→ quantity: 401.424 (13.856 × 29), unit_price: 0.113358, line_total: 45.55

</INSTRUCTIONS>

<EXAMPLES>

Example 1 - Spanish Invoice with IGIC:
OCR Input: "Factura A/41-23 ... IGIC: BASE 7 % ... IMPORTE LÍQUIDO: 45,00 €"
Tax extraction: type: "IGIC", rate: 7.0, amount: 0.0 (rate shown, no charge applied)

Example 1b - Spanish Expendeduria Invoice (Vendor/Customer identification):
OCR Input:
"Estanco EL GUANCHE
Mª GLORIA MARTÍN PÉREZ
D.N.I. 43 787570 - D
EXPENDEDURÍA Nº 28
Plaza Weyler, 4 - Tfno.: 922 27 25 55
38003 - Santa Cruz de Tenerife

FACTURA Nº 229/23
1 de 3 de 2023

Sr. D. _______________

4500 Folios timbrados 0,03 45,00"

Correct extraction:
- issue_date: "2023-03-01" (1 de marzo, NOT enero)
- vendor.name: "Estanco El Guanche - Mª Gloria Martín Pérez"
- vendor.tax_id: "43787570-D"
- vendor.address: "Plaza Weyler, 4, 38003 Santa Cruz de Tenerife"
- vendor.contact.phone: "922272555"
- customer: null (Sr. D. is empty - no customer info provided)
- items: [{{"description": "Folios timbrados", "quantity": 4500, "unit_price": 0.03, "line_total": 45.0}}]
- total_amount: 45.0

Example 2 - German Invoice with MwSt:
OCR Input: "Rechnung Nr. 2025-042 ... MwSt. 19%: 38,00 EUR ... Gesamtbetrag: 238,00 EUR"
Tax extraction: type: "MwSt", rate: 19.0, amount: 38.0 (explicit amount)

Example 3 - Australian Invoice with GST:
OCR Input: "Invoice #1234 ... GST (10%): $25.00 ... Total: $275.00 AUD"
Tax extraction: type: "GST", rate: 10.0, amount: 25.0, currency: "AUD"

Example 4 - US Invoice with Sales Tax:
OCR Input: "Invoice INV-789 ... Sales Tax (8.5%): $17.00 ... Total Due: $217.00"
Tax extraction: type: "Sales Tax", rate: 8.5, amount: 17.0

Example 6 - Electricity Invoice with Special Taxes:
OCR Input: "Factura C24CON003123634 ... IGIC reducido: 1,34€ ... Impuesto electricidad: 2,16€ ... Total: 46,61€"
Tax extraction:
  - Primary: type: "IGIC reducido", rate: 3.0, amount: 1.34
  - Additional: [{{type: "Impuesto electricidad", rate: 0.0, amount: 2.16}}]
Note: Type can be ANY string - extract exactly as shown

Example 5 - Pattern B Table (Expense Categories):
TABLE 1 (Page 1) [1]
{{Concepto, HONORARIOS, SUPLIDOS, PROVISIONES}}
Folios papel timbrado, 0.00, 45.00, 0.00

items extraction: [{{"description": "Folios papel timbrado", "quantity": 1.0, "unit_price": 45.0, "line_total": 45.0}}]
Note: Only ONE item, not three (HONORARIOS/SUPLIDOS/PROVISIONES are categories, not items)

</EXAMPLES>

<ERROR_PREVENTION>

ERROR 1: Treating table headers as items
Wrong: items: [{{"description": "HONORARIOS"}}, {{"description": "SUPLIDOS"}}]
Correct: items: [{{"description": "Actual item name", "line_total": 45.0}}]

ERROR 2: Calculating tax amounts
Wrong: See "VAT 20%" and calculate 100 × 0.20 = 20.0
Correct: Extract tax ONLY if explicit: "VAT: £20.00" results in amount: 20.0

ERROR 3: Hardcoding tax types
Wrong: Always use "IVA" or "VAT"
Correct: Extract exactly as shown (GST, MwSt, BTW, IGIC, Sales Tax, Impuesto electricidad, etc.)

ERROR 4: Ignoring currency context
Wrong: Assume EUR for all invoices
Correct: Extract from document (USD, GBP, AUD, CAD, INR, etc.)

ERROR 5: Prioritizing type over amount
Wrong: Focus on getting tax type perfect, guess amount if unclear
Correct: AMOUNT and RATE are critical. Type is descriptive only - any string is valid

ERROR 6: Including surcharges/fees in items
Wrong: items: [{{"description": "Recargo del 20%", "line_total": 7.05}}, {{"description": "Alquiler del contador", "line_total": 0.72}}]
Correct: items: [{{"description": "Energía consumida", "line_total": 21.88}}] (surcharges/fees excluded)

ERROR 7: Confusing vendor and customer (simple case)
Wrong: vendor: {{"name": "Estanco El Guanche"}}, customer: {{"name": "Mª Gloria Martín", "tax_id": "43787570-D"}}
Correct: vendor: {{"name": "Estanco El Guanche - Mª Gloria Martín Pérez", "tax_id": "43787570-D"}}, customer: null
Rule: The party with DNI/NIF/CIF and full address is the VENDOR (invoice issuer)

ERROR 9: Mixing vendor and customer names (split layout)
Wrong: vendor.name: "UNIONAUDIT J.Y.E CONSULTORES RIVEYAN SLU" (mixed both companies!)
Correct: vendor.name: "UNIONAUDIT J.Y.E. Consultores", customer.name: "RIVEYAN, SLU"
Rule: NEVER concatenate two different company names. Header/logo company = vendor, boxed company with "N.I.F:" = customer

ERROR 10: Using customer's tax ID for vendor (split layout)
Wrong: vendor.tax_id: "B38310322" (this was in a box labeled "N.I.F:" = customer's ID!)
Correct: vendor.tax_id: "B38247367" (from footer: "CIF B38247367, inscrita en el Registro...")
Rule: Tax ID in footer with legal text = VENDOR. Tax ID in labeled box near address = CUSTOMER

ERROR 8: Misinterpreting Spanish dates
Wrong: "1 de 3 de 2023" → "2023-01-03" (treating as Jan 3)
Correct: "1 de 3 de 2023" → "2023-03-01" (March 1st - day/month/year format)
Rule: Spanish dates are DAY de MONTH de YEAR

ERROR 11: Picking discount or tax-rate column as line_total
Wrong: row `Widget B 4,000 12,500 10,00 45,00 21,0` → line_total: 10.0  (that's Dto.%)
Correct: line_total: 45.0  (the printed total column)
Rule: When more numeric values appear than {{qty, unit_price, line_total}}, the small percentage-shaped
values (≤ 20, often 0,00 / 3,0 / 5,00 / 7,0 / 10,00) between unit_price and the printed total are
the DISCOUNT column. Apply the plausibility check qty × unit_price ≈ line_total (within ±50%).

ERROR 12: Putting the document TOTAL into the subtotal field
Wrong: financial_details.subtotal: 121.00  (taken from "TOTAL: 121,00€")
Correct: subtotal = sum of items[].line_total (e.g., 100.00); tax: 21.00; total_amount: 121.00
Rule: subtotal is PRE-TAX. Never reuse the TOTAL line as subtotal even when no explicit
"Subtotal" label is present.

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
Before returning JSON, verify (in priority order):
[CRITICAL] tax.amount extracted ONLY from explicit text (no calculations)
[CRITICAL] tax.rate extracted accurately
[CRITICAL] subtotal = exact sum of items[].line_total
[CRITICAL] total_amount matches document
All numeric fields are float or 0.0 (no null)
items[] contains ONLY goods/services (no headers, taxes, fees, surcharges, rentals)
currency is ISO 4217 code (EUR, USD, GBP, etc.)
tax.type extracted exactly as shown (descriptive only)
No invented or hallucinated data
</FINAL_CHECKLIST>

<OCR_TEXT>
"""
