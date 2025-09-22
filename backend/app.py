# Copyright 2024 Artificial Intelligence Labs, SL

"""
Main FastAPI application - SIMPLE and MINIMAL
One responsibility: bootstrap the API server
"""

from fastapi import FastAPI
from api.health import router as health_router
from api.invoice_endpoints.upload_and_parse import router as invoice_router

# Create FastAPI app
app = FastAPI(
    title="Invoice Processing API",
    description="Simple AI-powered invoice processing",
    version="1.0.0"
)

# Add routes
app.include_router(health_router, tags=["Health"])
app.include_router(invoice_router, prefix="/api/v1", tags=["Invoices"])


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