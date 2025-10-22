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
cd backend
poetry install

# Run the application locally with auto-reload
cd backend
poetry run python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Generate an authentication token for testing
poetry run python generate_token.py
```

### Environment Setup
- Create a `.env` file inside the `backend/` directory.
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

### Key Modules (`backend/invoice_processing/`)

#### `ai_services/`
- **`paddle_ocr/`**: Self-contained package for OCR operations (OCR mode only).
  - `processor.py`: Main OCR orchestrator with lazy initialization
  - `config.py`: Optimized PaddleOCR configuration (MKLDNN enabled for Linux)
  - `image_handler.py`: PDF-to-image conversion and preprocessing
  - `ocr_executor.py`: Parallelized, asynchronous OCR execution
  - **Models:** Pre-cached during Docker build for instant startup

- **`gemini_processor.py`**: Dual-mode Gemini API communication
  - `structure_invoice_data_from_text()`: OCR mode - processes extracted text
  - `structure_invoice_data_from_images()`: Vision mode - processes PDF images
  - `gemini/prompts.py`: Centralized prompt with multi-tax handling

#### `parsing/invoice_pipeline.py`
Main pipeline orchestrator. Routes requests to OCR or Vision mode based on `?mode=` parameter.

#### Other Key Modules
- **`caching/`**: Contains the Redis cache logic.
- **`classification/`**: (Currently Unused) Contains logic for document classification, which can be re-integrated if needed.
- **`models/`**: Defines the Pydantic data structures for invoices.
- **`validation/`**: Contains the logic for validating the final extracted data.
- **`configuration/`**: Manages application settings via `dotenv` and the `.env` file.