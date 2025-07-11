# Copyright 2024 Artificial Intelligence Labs, SL

INVOICE_PARSING_RESULT_EXAMPLE = {
    "document": {
        "hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "num_pages": 1,
        "page_size": {
            "width": 595,
            "height": 842
        }
    },
    "job": {
        "job_id": "123e4567-e89b-12d3-a456-426614174000",
        "job_time": "PT0.23S",
        "requested_by": "username",
        "requested_at": "2024-05-08T12:34:56Z"
    },
    "result": {
        "metadata": {
            "invoice_number": "INV76123",
            "issue_date": "2024-05-08",
            "due_date": "2024-05-22",
            "order_number": "FUN-16455"
        },
        "notes": "This is a note found in an example invoice.",
        "parties": {
            "vendor": {
                "name": "Artificial Intelligence Labs, SL",
                "tax_id": "B61881201",
                "contact": {
                    "email": "hola@ai-labs.es",
                    "phone": None
                },
                "address": {
                    "street": None,
                    "city": "Oviedo",
                    "state": None,
                    "postal_code": "33003",
                    "country": "Spain"
                }
            },
            "customer": {
                "name": "Cliente Excelente, SA",
                "tax_id": None,
                "contact": None,
                "address": {
                    "street": "Calle Fabulosa, 33",
                    "city": "La Palma",
                    "state": None,
                    "postal_code": "38780 TIJARAFE",
                    "country": "Spain"
                }
            }
        },
        "financial_details": {
            "currency": "EUR",
            "subtotal": "228",
            "tax": {
                "type": "OTHER",
                "rate": "0",
                "amount": "0"
            },
            "total_amount": "228",
            "payment": None
        },
        "items": [
            {
                "item_id": "01",
                "description": "Mantenimiento de Infraestructura durante un mes",
                "quantity": 12,
                "unit_price": "19",
                "line_total": "228"
            }
        ]
    }
}
