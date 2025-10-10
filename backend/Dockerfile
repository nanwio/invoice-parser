# Use a specific version of the builder image for reproducibility
ARG PYTHON_VERSION=3.12
ARG DEBIAN_VERSION=bookworm

# ---- Builder Stage ----
# This stage prepares the dependencies using the official Poetry installer.
FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} AS builder

# Set environment variables for the build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    # Add the poetry bin directory to the PATH. This is where the official installer places it.
    PATH="/root/.local/bin:$PATH"

# Install system build dependencies and curl.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential curl && \
    rm -rf /var/lib/apt/lists/*

# Use the official installer to install Poetry. This is the most reliable method.
RUN curl -sSL https://install.python-poetry.org | python3 -

# Set the working directory
WORKDIR /app

# Copy dependency definition files
COPY backend/pyproject.toml backend/poetry.lock* ./

# Export dependencies. The poetry command will now be found in the PATH.
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
