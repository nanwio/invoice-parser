# Use a specific version of the builder image for reproducibility
ARG PYTHON_VERSION=3.12
ARG DEBIAN_VERSION=bookworm

# ---- Builder Stage ----
# This stage prepares the dependencies using the standard pip installation method.
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS builder

# Set environment variables for the build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system build dependencies.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Use the image's native pip to install poetry. Executables will be in /usr/local/bin.
RUN pip install --upgrade pip poetry

# DIAGNOSTIC STEP: Find the exact location of the poetry executable
RUN find / -name "poetry" -type f

# Set the working directory
WORKDIR /app

# Copy dependency definition files
COPY backend/pyproject.toml backend/poetry.lock* ./

# Export dependencies. /usr/local/bin is in the PATH by default.
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --without dev

# Install the dependencies using pip into a self-contained directory
RUN pip install --no-cache-dir --prefix="/opt/venv" -r requirements.txt


# ---- Final Stage ----
# This stage creates the final, lean production image.
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS final

# Set environment variables for runtime, including the path to our installed packages
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/opt/venv/lib/python${PYTHON_VERSION}/site-packages" \
    PATH="/opt/venv/bin:$PATH"

# Install only runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for secure application execution
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser

# Copy the installed Python environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Set the working directory
WORKDIR /app

# Copy the application code
COPY backend/ ./

# Pre-cache PaddleOCR models and create necessary directory
RUN mkdir -p /home/appuser/.paddleocr && \
    python scripts/cache_models.py || echo "Model caching skipped"

# Grant ownership of the app and home directory to the non-root user
RUN chown -R appuser:appuser /app /home/appuser

# Switch to the non-root user
USER appuser

# Expose the application port
EXPOSE 8000

# Set the final command to run the application
CMD ["gunicorn", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:${PORT:-8000}", "--timeout", "120", "--chdir", "/app", "app:app"]
