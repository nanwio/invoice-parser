# Copyright 2024 Artificial Intelligence Labs, SL

import uvicorn
import gradio as gr

from loguru import logger
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.settings import settings
from app.rest.router import router
from app.services.cache import cache_service
from app.ui.app import create_gradio_interface


@asynccontextmanager
async def lifespan(app: FastAPI): # noqa

    # Startup
    logger.info("🚀 Starting InvoiceParser API with LIGHTNING optimizations...")

    # Initialize Redis connection
    if settings.CACHE_ENABLED:
        redis_connected = await cache_service.connect()
        if redis_connected:
            logger.info("Redis cache initialized successfully")
        else:
            logger.warning("Redis cache initialization failed - running without cache")

    # CRITICAL: Pre-warm Lightning parser for sub-second performance
    try:
        from app.services.parser.lightning_parser import startup_lightning_parser
        await startup_lightning_parser()
        logger.info("⚡ Lightning parser pre-warmed and ready!")
    except Exception as e:
        logger.error(f"Lightning parser warmup failed: {e}")

    yield
    
    # Shutdown
    logger.info("Shutting down InvoiceParser API...")
    if settings.CACHE_ENABLED:
        await cache_service.disconnect()

    logger.info("Cleanup completed")


app = FastAPI(
    title="ai-labs invoice parser",
    openapi_url=f"/api/v1/openapi.json",
    description="Extract structured data from PDF invoices and tickets using ML.",
    version="1.0.1",
    contact={
        "name": "Artificial Intelligence Labs, SL",
        "email": "contact@ai-labs.es",
    },
    lifespan=lifespan
)
app.add_middleware(
    CORSMiddleware,  # noqa
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.include_router(router, prefix="/api/v1")

# Mount Gradio app for web UI
gradio_app = create_gradio_interface()
app = gr.mount_gradio_app(
    app,
    gradio_app,
    path="/ui"
)

if __name__ == "__main__":
    logger.info("Starting InvoiceParser server")
    logger.info("API docs available at: http://localhost:8000/docs")
    logger.info("Web UI available at: http://localhost:8000/ui")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None
    )
