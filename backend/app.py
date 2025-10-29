# Copyright 2024 Artificial Intelligence Labs, SL

"""
Main FastAPI application - SIMPLE and MINIMAL
One responsibility: bootstrap the API server
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from loguru import logger
from api.health import router as health_router
from api.endpoints.upload_and_parse import router as invoice_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    App lifespan manager - runs on startup and shutdown.
    """
    # Startup: Register HEIF format support
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
        logger.info("HEIF/HEIC image format support enabled")
    except ImportError:
        logger.warning("pillow-heif not installed - HEIF/HEIC images not supported")
    except Exception as e:
        logger.warning(f"Failed to register HEIF support: {e}")

    # Startup: Eager initialization of PPStructure engine (used for invoice processing)
    logger.info("Eagerly initializing PPStructure engine on startup...")
    try:
        from invoice_processing.ai_services.paddle_ocr.table_processor import InvoiceTableProcessor
        # This call will trigger the singleton's _initialize() method
        _ = InvoiceTableProcessor()
        logger.success("PPStructure engine has been successfully initialized on startup")
    except Exception as e:
        logger.critical(f"Application startup failed: Could not initialize PPStructure engine. Reason: {e}")
        # The app will run, but OCR endpoints will fail until the issue is resolved.

    yield

    # Shutdown: cleanup if needed
    logger.info("Application shutting down")


# Create FastAPI app
app = FastAPI(
    title="Invoice Processing API",
    description="Simple AI-powered invoice processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add routes
app.include_router(health_router, tags=["Health"])
app.include_router(invoice_router, prefix="/api", tags=["Invoices"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Invoice Processing API",
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
    