# ==============================================================================
# CPU-only Dockerfile for invoice-parser with PaddleOCR
# TFG Edition - Simplified deployment without GPU requirements
# ==============================================================================

# Use Python 3.12 slim on Debian 12 (bookworm) for stable package names
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    # PDF processing (required by pdf2image)
    poppler-utils \
    # OpenCV dependencies
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    # Build tools (for some pip packages)
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install numpy <2 first (paddleocr + imgaug require numpy 1.x)
RUN pip install --no-cache-dir "numpy<2"

# Install PaddlePaddle CPU
# 3.2.1 is required for performant inference on Apple Silicon hosts (M-series).
# 2.6.2 ships OpenBLAS 0.3.13 (2022, pre-Apple-Silicon) and is ~100x slower on M-series CPUs.
RUN pip install --no-cache-dir paddlepaddle==3.2.1

# Install PaddleOCR runtime dependencies first (avoids pulling PyMuPDF, which fails to build on arm64)
# All deps are pinned with "numpy<2" already in the environment to avoid upgrading numpy to 2.x
RUN pip install --no-cache-dir \
    "numpy<2" \
    opencv-python-headless==4.10.0.84 \
    shapely \
    "scikit-image<0.23" \
    pyclipper \
    lmdb \
    tqdm \
    rapidfuzz \
    cython \
    pyyaml \
    beautifulsoup4 \
    fonttools \
    fire \
    requests \
    premailer \
    openpyxl \
    attrdict \
    "imgaug==0.4.0"

# Install PaddleOCR without dependencies (PyMuPDF would be pulled otherwise and lacks arm64 wheels)
RUN pip install --no-cache-dir --no-deps paddleocr==2.7.0.3

# Install remaining application dependencies
RUN pip install --no-cache-dir \
    fastapi==0.115.6 \
    "uvicorn[standard]==0.34.0" \
    gunicorn==23.0.0 \
    pydantic==2.10.5 \
    pydantic-settings==2.7.1 \
    redis==5.2.1 \
    loguru==0.7.3 \
    "python-jose[cryptography]==3.3.0" \
    "passlib[bcrypt]==1.7.4" \
    python-multipart==0.0.20 \
    google-generativeai==0.8.6 \
    pillow==11.1.0 \
    pillow-heif==0.21.0 \
    pdf2image==1.17.0 \
    pyjwt==2.10.1 \
    pypdf==5.1.0 \
    pandas==2.2.3 \
    fastapi-jwt==0.3.0 \
    python-dotenv==1.0.1

# Copy application code
COPY app.py ./
COPY src ./src
COPY scripts ./scripts

# Create non-root user for security
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Create directories for model downloads
RUN mkdir -p /home/appuser/.paddleocr

# Set environment variables
ENV HOME=/home/appuser
ENV PADDLEOCR_HOME=/home/appuser/.paddleocr

# Expose port
EXPOSE 8000

# Run with gunicorn (can use multiple workers on CPU)
# 2 workers for better concurrency on multi-core CPUs
CMD ["python", "-m", "gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "300", "--chdir", "/app", "app:app"]
