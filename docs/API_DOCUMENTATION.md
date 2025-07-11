# Invoice Parser API Documentation

## Overview

The Invoice Parser API is a REST service that extracts structured data from PDF invoices using Machine Learning.
The API provides intelligent document classification, high-accuracy data extraction, and automatic caching for improved 
performance.

## Authentication

The API uses JWT Bearer token authentication. All requests to protected endpoints must include an Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### POST /api/v1/parse

Extracts structured data from a PDF invoice.

**Authentication:** Required

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body Parameter:
  - `invoice` (file, required): PDF file to parse (maximum 10MB)

**Response Codes:**
- `200 OK`: Invoice successfully parsed
- `400 Bad Request`: Processing error or invalid file
- `401 Unauthorized`: Invalid or missing authentication token
- `413 Payload Too Large`: File exceeds 10MB limit
- `422 Unprocessable Entity`: Document is not an invoice

**Response Body (200 OK):**

```json
{
  "document": {
    "hash": "string",
    "num_pages": "integer",
    "page_size": {
      "width": "integer",
      "height": "integer"
    }
  },
  "job": {
    "job_id": "uuid",
    "job_time": "ISO 8601 duration",
    "requested_by": "string",
    "requested_at": "ISO 8601 datetime"
  },
  "result": {
    "metadata": {
      "invoice_number": "string | null",
      "issue_date": "YYYY-MM-DD | null",
      "due_date": "YYYY-MM-DD | null",
      "order_number": "string | null"
    },
    "notes": "string | null",
    "parties": {
      "vendor": {
        "name": "string",
        "tax_id": "string | null",
        "contact": {
          "email": "string | null",
          "phone": "string | null",
          "fax": "string | null"
        },
        "address": {
          "street": "string | null",
          "city": "string | null",
          "state": "string | null",
          "postal_code": "string | null",
          "country": "string | null"
        }
      },
      "customer": {
        "name": "string",
        "tax_id": "string | null",
        "contact": "object | null",
        "address": "object | null"
      }
    },
    "financial_details": {
      "currency": "ISO 4217 code | null",
      "subtotal": "number",
      "tax": {
        "type": "IGIC | IVA | OTHER | EXEMPT",
        "rate": "number",
        "amount": "number"
      },
      "total_amount": "number",
      "payment": {
        "method": "BANK_TRANSFER | BANK_DEPOSIT | CARD | CASH | OTHER",
        "number": "string | null"
      }
    },
    "items": [
      {
        "item_id": "string | null",
        "description": "string | null",
        "quantity": "integer",
        "unit_price": "number",
        "line_total": "number"
      }
    ]
  }
}
```

**Error Response Format:**

```json
{
  "detail": "string"
}
```

### GET /api/v1/metrics

Returns basic API metrics.

**Authentication:** Not required

**Response Codes:**
- `200 OK`: Success

**Response Body:**

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

## Data Types

### Tax Types
- `IGIC`: Impuesto General Indirecto Canario
- `IVA`: Impuesto sobre el Valor Añadido
- `OTHER`: Other tax types
- `EXEMPT`: Tax-exempt

### Payment Methods
- `BANK_TRANSFER`: Wire transfer or bank transfer
- `BANK_DEPOSIT`: Direct bank deposit
- `CARD`: Credit or debit card
- `CASH`: Cash payment
- `OTHER`: Other payment methods

### Date Format
All dates use ISO format: `YYYY-MM-DD`

### Currency
ISO 4217 three-letter currency codes (e.g., EUR, USD, GBP)

## Limitations

- Only PDF files are supported
- Maximum file size: 10MB