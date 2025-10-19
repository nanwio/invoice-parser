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

The system is an asynchronous, multi-stage pipeline designed for high-speed invoice processing.

### High-Level Flow
1.  **PDF Upload**: A request hits the single `POST /api/v1/invoice/parse` endpoint.
2.  **Cache Check**: The system checks Redis for a result using the PDF's hash. If found, returns it instantly.
3.  **Optimized OCR**: The PDF is processed by a highly optimized, parallelized `PaddleOCR` engine running on the CPU.
4.  **AI Structuring**: The raw text from the OCR is sent to `Gemini 2.5 Flash` with a robust prompt to be structured into a clean JSON format.
5.  **Validation**: The structured data is validated against a set of business rules (e.g., totals must match).
6.  **Cache & Response**: The final result is cached in Redis and returned to the user.

### Performance Focus
The system is now built around a **single, highly-optimized performance mode** designed for maximum speed on CPU. All parameters for OCR and image processing have been fine-tuned for a sub-2-second target, removing the complexity of multiple performance profiles.

### Key Modules (`backend/invoice_processing/`)

#### `ai_services/`
- **`paddle_ocr/`**: A self-contained package for all OCR operations.
  - `processor.py`: The main orchestrator.
  - `config.py`: Manages the single, ultra-fast configuration.
  - `image_handler.py`: Handles PDF-to-image conversion and pre-processing.
  - `ocr_executor.py`: Runs the core OCR engine in a parallelized, asynchronous manner.
- **`gemini_processor.py`**: Manages all communication with the Gemini API for structuring data.
  - `gemini_engines/prompts.py`: Contains the robust, centralized prompt for data extraction.

#### `parsing/invoice_pipeline.py`
The main orchestrator for the entire process. It coordinates calls to the cache, OCR engine, and Gemini processor.

#### Other Key Modules
- **`caching/`**: Contains the Redis cache logic.
- **`classification/`**: (Currently Unused) Contains logic for document classification, which can be re-integrated if needed.
- **`models/`**: Defines the Pydantic data structures for invoices.
- **`validation/`**: Contains the logic for validating the final extracted data.
- **`configuration/`**: Manages application settings via `dotenv` and the `.env` file.