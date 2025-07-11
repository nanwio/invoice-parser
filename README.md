# Invoice Parser API

AI-powered service that extracts structured data from PDF invoices. Built with FastAPI and featuring intelligent caching
and document classification.

## Quick Start

### Using Docker Compose

```bash
# Clone and setup
git clone <repository-url>
cd invoice-parsing
cp .env.example .env

# Edit .env with your API keys
# - SECRET_KEY: Generate with `openssl rand -hex 32`
# - GEMINI_API_KEY: Your AI API key

# Start services
docker compose up -d

# Generate authentication token
./scripts/tokens.py generate --username user@example.com --days 365
```

### Access Points

- API: `http://localhost:8000/api/v1/`
- Web UI: `http://localhost:8000/ui`
- API Docs: `http://localhost:8000/docs`

## Local Development

```bash
# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Run the application
uv run python app/server.py
```

## Documentation

- [API Documentation](docs/API_DOCUMENTATION.md) - Endpoint reference and data structures
- [Token Management](docs/TOKEN_MANAGEMENT.md) - Authentication and token generation

## Basic Usage

### Generate Token

```bash
./scripts/tokens.py generate --username client@example.com --days 30
```

### Parse Invoice

```bash
curl -X POST http://localhost:8000/api/v1/parse \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "invoice=@invoice.pdf"
```

## Configuration

Key environment variables in `.env`:

```env
# Required
SECRET_KEY=your-secret-key
GEMINI_API_KEY=your-api-key

# Optional
REDIS_URL=redis://localhost:6379/0
CACHE_ENABLED=true
MAX_FILE_SIZE_MB=10
```

## Features

- PDF invoice parsing with AI-powered extraction
- Automatic document classification
- Redis caching for duplicate invoices
- REST API with JWT authentication
- Web interface for manual uploads
- Support for multiple tax types (IVA, IGIC, etc.)
- Multi-currency support

## Deploying to Cloudflare Containers

### Prerequisites

1. Install Wrangler CLI:
```bash
npm install -g wrangler
```

2. Authenticate with Cloudflare:
```bash
wrangler login
```

### Full Deployment Guide

#### 1. Create KV Namespace (for caching)
```bash
# Create production KV namespace
wrangler kv:namespace create INVOICE_CACHE

# Note the ID from output, update wrangler.jsonc with it
```

#### 2. Update Configuration
Edit `wrangler.jsonc` and replace placeholders:
- `YOUR_KV_NAMESPACE_ID` with the ID from step 1
- Add your custom domain in the routes section (see below)

#### 3. Build and Push Container
```bash
# Build the container image
docker build -f Dockerfile.cloudflare -t invoice-parsing:latest .

# Push to Cloudflare Container Registry
wrangler container-image push invoice-parsing:latest
```

#### 4. Set Environment Secrets
```bash
# Required secrets (set these via CLI only)
wrangler secret put SECRET_KEY
wrangler secret put GEMINI_API_KEY

# For KV cache strategy
wrangler secret put CF_ACCOUNT_ID
wrangler secret put CF_API_TOKEN
wrangler secret put KV_NAMESPACE_ID

# Optional: External Redis (if not using KV)
wrangler secret put REDIS_URL
```

For local development, create a `.dev.vars` file:
```bash
cp .dev.vars.example .dev.vars
# Edit .dev.vars with your development secrets
```

#### 5. Deploy the Application
```bash
# Deploy to production
wrangler deploy --env production
```

### Custom Domain Setup

1. Add your domain to Cloudflare (if not already added)

2. Update `wrangler.jsonc` to include routes:
```jsonc
{
  "name": "invoice-parsing",
  "routes": [
    {
      "pattern": "api.yourdomain.com/*",
      "custom_domain": true
    }
  ],
  // ... rest of config
}
```

3. Deploy with the domain:
```bash
wrangler deploy --env production
```

4. The container will be accessible at:
   - `https://api.yourdomain.com/api/v1/`
   - `https://api.yourdomain.com/docs`
   - `https://api.yourdomain.com/ui`

### Production Checklist

- [ ] Generate strong SECRET_KEY: `openssl rand -hex 32`
- [ ] Create KV namespace and update config
- [ ] Set all required environment variables
- [ ] Configure custom domain in Cloudflare dashboard
- [ ] Update CORS settings if needed
- [ ] Test the deployment with a sample invoice


## Requirements

- Python 3.12+
- Redis 7+ (optional, for caching)
- Docker & Docker Compose (for containerized deployment)

## License

Copyright 2024 Artificial Intelligence Labs, SL. 