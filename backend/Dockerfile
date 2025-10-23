# ==============================================================================
# GPU-enabled multi-stage Dockerfile for invoice-parser with PaddleOCR
# Based on CUDA 12.1.1 for Google Cloud Run GPU (NVIDIA L4)
# ==============================================================================

# ==================== STAGE 1: Builder (install + pre-cache models) ====================
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04 AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.12 (Ubuntu 22.04 ships with 3.10, need to add PPA)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3.12-distutils \
    python3-pip \
    build-essential \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Make Python 3.12 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Upgrade pip for Python 3.12
RUN python3.12 -m pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /app

# Copy pyproject.toml first for better layer caching
COPY backend/pyproject.toml ./

# Install numpy and other binary packages FIRST (ensures wheels are used)
RUN pip install --no-cache-dir --only-binary=:all: \
    numpy==1.26.4 \
    pillow==10.4.0 \
    pillow-heif==0.18.0 \
    pandas==2.1.4

# CRITICAL: Install paddlepaddle-gpu instead of paddlepaddle
# Remove any existing paddlepaddle first to avoid conflicts
RUN pip uninstall -y paddlepaddle paddlepaddle-tiny || true && \
    pip install --no-cache-dir \
    paddlepaddle-gpu==2.6.1 \
    paddleocr==2.7.3 \
    paddleclas==2.5.2 \
    opencv-python-headless==4.8.1.78

# Install remaining application dependencies
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
    pypdf==3.17.4

# Copy application code
COPY backend/*.py ./
COPY backend/api ./api
COPY backend/configuration ./configuration
COPY backend/invoice_processing ./invoice_processing

# Pre-cache PaddleOCR models during build (no GPU available at build time, uses CPU)
# This downloads ~30MB of models so they're ready at runtime
COPY backend/scripts/cache_models.py ./scripts/
RUN python scripts/cache_models.py

# ==================== STAGE 2: Final runtime image ====================
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.12 (runtime only, no dev packages)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.12 \
    python3-pip \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Make Python 3.12 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.12/dist-packages /usr/local/lib/python3.12/dist-packages

# Copy application code from builder
COPY --from=builder /app /app

# Copy pre-cached PaddleOCR models from builder
# IMPORTANT: Models are cached in /root/.paddleocr during build
COPY --from=builder /root/.paddleocr /root/.paddleocr

# Create non-root user and set permissions
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser && \
    chown -R appuser:appuser /app /root/.paddleocr

# Switch to non-root user for runtime
USER appuser

# Expose port
EXPOSE 8000

# CRITICAL: GPU only supports 1 worker (concurrent requests handled by async)
# Use gunicorn with 1 worker, 300s timeout for model loading
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "300", "--chdir", "/app", "app:app"]
