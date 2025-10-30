# Project "Invoice Parser" Guidance

This document provides a comprehensive overview of the Invoice Parser project, its architecture, and development practices.

## Core Philosophy

The project adheres to a strict **Clean Code** philosophy:
- **Single Responsibility Principle:** Classes are small (typically under 100-130 lines) and have one clear purpose.
- **Modularity:** Logic is organized into cohesive packages (e.g., `paddle_ocr`, `gemini_engines`).
- **Readability:** Code is written to be self-explanatory, with descriptive names and clear structure.
- **High Performance:** The entire pipeline is built with speed and efficiency as a primary goal, using asynchronous operations and parallelism.

## Development Commands

Execute all commands from the **project root directory** (`/invoice-parser`).

### Local Development
```bash
# Install/update dependencies
poetry install

# Run the application locally with auto-reload
poetry run python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Generate an authentication token for testing
poetry run python generate_token.py
```

### Environment Setup
- Create a `.env` file in the project root directory.
- Required variables:
  - `GEMINI_API_KEY`: Your API key for Google Gemini.
  - `REDIS_URL`: The full connection string for your Redis instance (e.g., `redis://:password@host:port/0`).
  - `JWT_SECRET_KEY`: A long, random string for signing tokens.

## Architecture Overview

The system is an asynchronous, multi-stage pipeline designed for high-speed invoice processing with **two processing modes**:

### Processing Modes

#### **OCR Mode (Default)** - Fast & Cost-Effective
```bash
POST /api/v1/invoice/parse?mode=ocr
```
**Flow:**
1. **PDF Upload** → `POST /api/v1/invoice/parse?mode=ocr`
2. **Cache Check** → Redis lookup by PDF hash (instant return if hit)
3. **PaddleOCR Extraction** → Parallel text extraction from PDF (~0.5-1s)
4. **Gemini Text Structuring** → Gemini 2.5 Flash processes OCR text (~1-2s)
5. **Validation** → Business rules verification
6. **Cache & Response** → Result cached and returned

**Performance:** <2 seconds | **Best for:** Standard invoices, high-volume processing

#### **Vision Mode** - Maximum Accuracy
```bash
POST /api/v1/invoice/parse?mode=vision
```
**Flow:**
1. **PDF Upload** → `POST /api/v1/invoice/parse?mode=vision`
2. **Cache Check** → Redis lookup by PDF hash
3. **Image Conversion** → PDF pages to images (~0.4-0.5s per page)
4. **Gemini Vision Multimodal** → Gemini "sees" document layout (~6-9s)
5. **Validation** → Business rules verification
6. **Cache & Response** → Result cached and returned

**Performance:** ~7-13 seconds | **Best for:** Complex layouts, poor quality scans

### When to Use Each Mode

| Scenario | Recommended Mode |
|----------|------------------|
| Standard invoices with clear text | **OCR** (3-5x faster) |
| High-volume batch processing | **OCR** (lower cost) |
| Complex multi-column layouts | **Vision** (better accuracy) |
| Scanned/low-quality documents | **Vision** (sees structure) |
| Real-time user-facing API | **OCR** (sub-2s response) |

### Performance Optimization

**Pre-cached Models:** PaddleOCR models are downloaded during Docker build (not at runtime) for instant cold starts.

**Redis Caching:** Identical PDFs (by hash) return cached results in <50ms, bypassing all processing.

### Project Structure (Clean Code Architecture)

```
/invoice-parser/
├── src/                           # All source code (refactored clean architecture)
│   ├── api/                       # FastAPI routes and endpoints
│   │   ├── endpoints/             # API endpoint handlers
│   │   │   └── upload_and_parse.py  # Main invoice parsing endpoint
│   │   ├── security/              # JWT authentication logic
│   │   └── health.py              # Health check endpoint
│   │
│   ├── core/                      # Core business logic orchestration
│   │   └── pipeline/
│   │       └── invoice_processor.py  # Main pipeline orchestrator
│   │
│   ├── domain/                    # Domain models and business logic
│   │   ├── models/                # Pydantic data models (clean separation)
│   │   │   ├── party.py           # Party, Address, Contact models
│   │   │   ├── financial.py       # Tax, Payment, FinancialDetails models
│   │   │   ├── item.py            # LineItem, Metadata models
│   │   │   └── invoice.py         # Main Invoice model
│   │   ├── corrections/           # Invoice correction strategies
│   │   │   ├── correction_pipeline.py  # Main correction orchestrator
│   │   │   └── strategies/        # Specific correction strategies (future)
│   │   └── validation/            # Validation logic
│   │       ├── invoice_validator.py   # Main validator
│   │       └── rules/             # Validation rules (future)
│   │
│   ├── services/                  # External service integrations
│   │   ├── ai/                    # AI service providers
│   │   │   └── gemini/
│   │   │       ├── text_structurer.py  # Gemini text processing
│   │   │       ├── gemini_client.py    # Gemini API client
│   │   │       └── prompts.py          # Prompt templates
│   │   ├── ocr/                   # OCR service providers
│   │   │   └── paddle/
│   │   │       ├── processor.py         # Main OCR processor
│   │   │       ├── provider.py          # Singleton engine provider
│   │   │       ├── image_handler.py     # PDF conversion & optimization
│   │   │       ├── image_preprocessor.py  # Image enhancement
│   │   │       ├── image_quality_detector.py  # Quality analysis
│   │   │       ├── table_processor.py   # Table extraction
│   │   │       └── config.py            # PaddleOCR configuration
│   │   └── cache/                 # Caching services
│   │       └── redis_repository.py  # Redis cache implementation
│   │
│   ├── config/                    # Application configuration
│   │   └── settings.py            # Environment settings
│   │
│   └── utils/                     # Utility functions
│       └── document_utils.py      # Document hashing, etc.
│
├── app.py                         # FastAPI application entry point
├── pyproject.toml                 # Poetry dependencies
├── Dockerfile                     # GPU-enabled Docker image
└── README.md                      # Project documentation
```

### Key Modules

#### `src/core/pipeline/`
- `invoice_processor.py`: Main pipeline orchestrator. Routes requests to OCR or Vision mode based on `?mode=` parameter.

#### `src/services/ai/gemini/`
- `text_structurer.py`: Dual-mode Gemini API communication
  - `structure_invoice_data_from_text()`: OCR mode - processes extracted text
  - `structure_invoice_data_from_images()`: Vision mode - processes PDF images
- `prompts.py`: Centralized prompt with multi-tax handling and state-of-the-art prompting techniques

#### `src/services/ocr/paddle/`
- Self-contained package for OCR operations (OCR mode only)
- `processor.py`: Main OCR orchestrator with lazy initialization
- `provider.py`: Singleton pattern for PPStructure engine management
- `image_handler.py`: PDF-to-image conversion with smart preprocessing
- `table_processor.py`: Table extraction using PPStructure

#### `src/domain/models/`
- Clean separation of Pydantic models (all files <70 lines)
- `invoice.py`: Main Invoice model following EN16931/UBL pattern
- `party.py`, `financial.py`, `item.py`: Modular model definitions

#### `src/services/cache/`
- `redis_repository.py`: Redis caching with repository pattern

#### `src/config/`
- `settings.py`: Centralized application settings