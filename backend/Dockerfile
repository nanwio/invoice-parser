# Single-stage build for simplicity and reliability
FROM python:3.12-slim-bookworm

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

# Upgrade pip and install build tools compatible with Python 3.12
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Copy ONLY pyproject.toml first for better caching
COPY backend/pyproject.toml ./

# Install numpy and other binary packages FIRST (ensures wheels are used)
RUN pip install --no-cache-dir --only-binary=:all: \
    numpy==1.26.4 \
    pillow==10.4.0 \
    pillow-heif==1.1.1 \
    pandas==2.1.4

# Install paddlepaddle and paddleocr
RUN pip install --no-cache-dir \
    paddlepaddle==2.6.0 \
    paddleocr==2.7.3 \
    opencv-python-headless==4.8.1.78

# Install remaining dependencies
RUN pip install --no-cache-dir \
    fastapi==0.115.6 \
    uvicorn==0.32.1 \
    gunicorn==21.0.0 \
    pydantic==2.10.2 \
    pydantic-settings==2.10.0 \
    redis==5.0.0 \
    loguru==0.7.2 \
    "python-jose[cryptography]==3.3.0" \
    "passlib[bcrypt]==1.7.4" \
    python-multipart==0.0.19 \
    google-generativeai==0.8.5 \
    pdf2image==1.17.0 \
    instructor==1.3.0 \
    openvino==2024.5.0 \
    "fastapi-jwt[authlib]==0.3.0" \
    pyjwt==2.10.1 \
    pypdf==3.17.4 && \
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
