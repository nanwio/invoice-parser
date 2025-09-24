#----------------------------------------------------------------
# 1. Builder Stage: To compile dependencies and cache models
#----------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:debian-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies needed for build and model caching
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser

# Set up the working directory
WORKDIR /app
RUN chown appuser:appuser /app

# Switch to the non-root user before creating venv
USER appuser

# Copy dependency files and install them into a virtual environment
COPY --chown=appuser:appuser backend/pyproject.toml backend/uv.lock ./
RUN uv venv && \
    uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

# --- Pre-cache PaddleOCR models ---
# This significantly reduces cold start time in production.
COPY --chown=appuser:appuser backend/scripts/cache_models.py ./scripts/
RUN /app/.venv/bin/python scripts/cache_models.py

#----------------------------------------------------------------
# 2. Final Stage: The lean, production-ready container
#----------------------------------------------------------------
FROM ghcr.io/astral-sh/uv:debian-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Create a non-root user (must match the builder stage)
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser

# Install only the absolute bare-minimum RUNTIME dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set up the working directory and permissions
WORKDIR /app
RUN chown appuser:appuser /app

# Switch to the non-root user
USER appuser

# Copy the venv, application code, and the warmed-up model cache
COPY --from=builder --chown=appuser:appuser /app/.venv ./.venv
COPY --from=builder --chown=appuser:appuser /home/appuser/.paddleocr /home/appuser/.paddleocr
COPY --chown=appuser:appuser backend/*.py ./
COPY --chown=appuser:appuser backend/api ./api
COPY --chown=appuser:appuser backend/configuration ./configuration
COPY --chown=appuser:appuser backend/invoice_processing ./invoice_processing

# Activate the venv for subsequent commands
ENV PATH="/app/.venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE 8000

# Start server. Using gunicorn as it's a more robust production server.
# The --chdir flag solves Python's module path issues when running from root.
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:${PORT:-8000}", "--timeout", "120", "--chdir", "/app", "app:app"]
