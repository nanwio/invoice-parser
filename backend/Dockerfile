# Single-stage build for simplicity and reliability
FROM python:3.12-slim-bookworm

# Install build tools
RUN pip install poetry

# Ensure essential build tools are present for packages like numpy
RUN pip install --upgrade setuptools wheel

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install ALL system dependencies (build + runtime)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependencies and install AS ROOT
COPY backend/pyproject.toml backend/poetry.lock* ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --without dev && \
    echo "=== Verifying gunicorn ===" && \
    gunicorn --version && \
    echo "=== gunicorn OK ==="

# Copy application code
COPY backend/*.py ./
COPY backend/api ./api
COPY backend/configuration ./configuration
COPY backend/invoice_processing ./invoice_processing

# Pre-cache PaddleOCR models (optional but recommended)
COPY backend/scripts/cache_models.py ./scripts/
RUN python scripts/cache_models.py || echo "Model caching skipped"

# NOW create non-root user and change ownership
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser && \
    mkdir -p /home/appuser/.paddleocr && \
    chown -R appuser:appuser /app /home/appuser/.paddleocr

# Switch to non-root user for runtime
USER appuser

# The PATH is already set to include /home/appuser/.local/bin
# ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Start with gunicorn - shell form to expand $PORT from Cloud Run
CMD gunicorn -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 120 --chdir /app app:app
