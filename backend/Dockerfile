# Single-stage build for simplicity and reliability
FROM python:3.12-slim-bookworm

# Install uv for dependency management
RUN pip install uv

# Force Python 3.12 for PaddlePaddle compatibility - No longer needed, image is 3.12
# ENV UV_PYTHON=python3.12
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Create non-root user
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser

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
RUN chown appuser:appuser /app

# Switch to non-root user
USER appuser

# Copy dependencies and install
COPY --chown=appuser:appuser backend/pyproject.toml backend/poetry.lock* ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-root --no-dev && \
    echo "=== Verifying gunicorn ===" && \
    gunicorn --version && \
    echo "=== gunicorn OK ==="

# Copy application code
COPY --chown=appuser:appuser backend/*.py ./
COPY --chown=appuser:appuser backend/api ./api
COPY --chown=appuser:appuser backend/configuration ./configuration
COPY --chown=appuser:appuser backend/invoice_processing ./invoice_processing

# Pre-cache PaddleOCR models (optional but recommended)
COPY --chown=appuser:appuser backend/scripts/cache_models.py ./scripts/
RUN /app/.venv/bin/python scripts/cache_models.py || echo "Model caching skipped"

# Create paddleocr directory
RUN mkdir -p /home/appuser/.paddleocr

# Set PATH to use venv
ENV PATH="/app/.venv/bin:$PATH"

# Expose port
EXPOSE 8000

# Start with gunicorn - shell form to expand $PORT from Cloud Run
CMD /app/.venv/bin/gunicorn -w 2 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 120 --chdir /app app:app
