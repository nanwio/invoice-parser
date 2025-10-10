# Use a specific version of the builder image for reproducibility
ARG PYTHON_VERSION=3.12
ARG DEBIAN_VERSION=bookworm

# ---- Builder Stage ----
# This stage installs all dependencies, including build-time tools.
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    PATH="/home/appuser/.local/bin:$PATH"

# Install system dependencies and Python build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    pip install --upgrade pip setuptools wheel poetry && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser

# Create and set ownership for the app directory
WORKDIR /app
RUN chown appuser:appuser /app

# Switch to the non-root user
USER appuser

# Copy only the dependency files first to leverage Docker cache
COPY --chown=appuser:appuser backend/pyproject.toml backend/poetry.lock* ./

# Install Python dependencies
RUN poetry install --no-root --without dev

# ---- Final Stage ----
# This stage creates the final, lean production image.
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS final

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/home/appuser/.local/bin:$PATH"

# Create a non-root user
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser

# Install only runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create and set ownership for the app directory
WORKDIR /app
RUN chown appuser:appuser /app

# Switch to the non-root user
USER appuser

# Copy installed dependencies from the builder stage
COPY --from=builder /home/appuser/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser backend/ ./

# Pre-cache PaddleOCR models
RUN python scripts/cache_models.py || echo "Model caching skipped"
RUN mkdir -p /home/appuser/.paddleocr

# Expose port and set the command
EXPOSE 8000
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:${PORT:-8000}", "--timeout", "120", "--chdir", "/app", "app:app"]
