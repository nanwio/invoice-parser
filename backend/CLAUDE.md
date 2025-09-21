# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
```bash
# Install dependencies with uv package manager
uv sync

# Run the application locally
uv run python app/server.py

# Generate authentication tokens
./scripts/tokens.py generate --username user@example.com --days 365

# Verify existing tokens
./scripts/tokens.py verify TOKEN_HERE
```

### Docker Development
```bash
# Start services with Docker Compose
docker compose up -d

# Build and rebuild containers
docker compose build

# View logs
docker compose logs -f app
```

### Environment Setup
- Copy `.env.example` to `.env`
- Required: `SECRET_KEY` (generate with `openssl rand -hex 32`)
- Required: `GEMINI_API_KEY` for AI-powered parsing
- Optional: `REDIS_URL` for caching (defaults to localhost)

## Architecture Overview

### Core Structure
- **FastAPI Application**: Main REST API with automatic OpenAPI docs at `/docs`
- **Gradio Web UI**: User interface mounted at `/ui` for manual uploads
- **AI Parser**: Uses Google Gemini 2.5 Flash Lite for PDF invoice extraction
- **Caching Layer**: Redis-based caching with pluggable strategies (Redis/Cloudflare KV)
- **JWT Authentication**: Token-based security with role-based access

### Key Modules

#### Services Layer (`app/services/`)
- **Parser** (`parser/`): AI-powered invoice extraction using Instructor + Gemini
- **Cache** (`cache/`): Abstracted caching with Redis and Cloudflare KV strategies
- **Classifier** (`classifier/`): Document type classification
- **Security** (`security/`): JWT token generation and validation

#### REST API (`app/rest/`)
- **Router** (`router.py`): Main API route aggregation
- **Parser endpoints** (`parser/`): Invoice upload and parsing endpoints
- **Models** (`models.py`): Pydantic models for API requests/responses

#### Settings (`app/settings.py`)
Configuration management with Pydantic Settings:
- Model settings (Gemini API, model name)
- Cache configuration (Redis URL, enable/disable)
- File processing limits and allowed types

### Application Flow
1. **PDF Upload**: Via REST API (`/api/v1/parse`) or Web UI (`/ui`)
2. **Cache Check**: Document hash lookup to avoid reprocessing
3. **AI Processing**: Gemini model extracts structured data using Instructor
4. **Response**: Structured invoice data (vendor, amounts, taxes, etc.)

### Authentication
- JWT tokens generated via `scripts/tokens.py`
- Tokens contain username and role claims
- API endpoints protected with FastAPI dependency injection

### Deployment Options
- **Local**: Direct Python execution with `uv run`
- **Docker**: Multi-container setup with Redis
- **Cloudflare Containers**: Production deployment with KV storage

### File Processing
- PDF-only support (`application/pdf`)
- 10MB default size limit (configurable)
- Base64 encoding for AI model processing
- Automatic caching by document hash

### Web Interface
- Gradio-powered UI for manual uploads
- Integrated with main FastAPI app
- Real-time parsing results display

## Professional OCR Enhancements

### Advanced Image Preprocessing (`app/services/preprocessing/`)
- **High-DPI conversion**: PDF to 300 DPI PNG for optimal OCR
- **Noise reduction**: Median filtering and artifact removal
- **Auto-enhancement**: Contrast, sharpness, and brightness optimization
- **Auto-orientation**: EXIF-based rotation correction
- **Border cropping**: Automatic content-focused cropping

### Enhanced AI Prompts
- **Chain-of-thought reasoning**: Systematic document analysis
- **Field-specific validation**: Spanish tax IDs, European dates, currency detection
- **Mathematical verification**: Cross-validation of calculations
- **Quality instructions**: Professional-grade extraction guidelines

### Validation & Quality Assessment (`app/services/validation/`)
- **Mathematical consistency**: Subtotal + tax = total validation
- **Spanish tax ID validation**: NIF, CIF, NIE format checking
- **Date logic validation**: ISO format and chronological consistency
- **Currency format validation**: ISO 4217 codes
- **Quality scoring**: 0-100 completeness and accuracy metrics

### Dual API Endpoints
- **Standard `/parse`**: Backward-compatible, fast processing
- **Enhanced `/parse/enhanced`**: Professional validation with quality metrics
  - Returns validation results and quality scores
  - Configurable preprocessing (can be disabled for speed)
  - Comprehensive error and warning reporting

### Professional Features
- **Fallback processing**: Auto-retry without preprocessing if enhanced fails
- **Confidence scoring**: Quality assessment for business validation
- **Detailed logging**: Professional monitoring and debugging
- **Error categorization**: Errors vs warnings for business rules