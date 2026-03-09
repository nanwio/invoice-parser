# Utility Scripts

## Setup

Before running these scripts, ensure dependencies are installed:

```bash
poetry install
```

## Available Scripts

### `clear_cache.py`

Clears all cached invoices from Redis.

**When to use:** After updating prompts or validation rules to force re-processing with new logic.

**Usage:**
```bash
poetry run python scripts/clear_cache.py
```

**Output:**
```
✅ Cache cleared: 42 invoice(s) removed
```

---

### `generate_token.py`

Generates a JWT token for local API testing.

**When to use:** Testing API endpoints locally without authentication setup.

**Usage:**
```bash
poetry run python scripts/generate_token.py
```

**Output:**
```
--- Tu token JWT para pruebas ---
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Cópialo y úsalo en el comando curl.
```

**Example curl with token:**
```bash
TOKEN=$(poetry run python scripts/generate_token.py | tail -3 | head -1)

curl -X POST "http://localhost:8000/api/v1/invoice/parse" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@invoice.pdf"
```

## Troubleshooting

If you get `ModuleNotFoundError`, reinstall dependencies:

```bash
poetry install
```

If that fails due to build errors, try:

```bash
rm -rf .venv poetry.lock
poetry install
```
