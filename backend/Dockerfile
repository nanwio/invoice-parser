# Use a single-stage build for simplicity and to avoid symlink issues.
FROM ghcr.io/astral-sh/uv:debian-slim

# Create a non-root user and group
RUN groupadd --system --gid 1001 appuser && \
    useradd --system --create-home --uid 1001 --gid 1001 appuser

# Install system dependencies required by the application
RUN apt-get update && \
    apt-get install -y --no-install-recommends poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Set up the working directory and permissions
WORKDIR /app
RUN chown appuser:appuser /app

# Switch to the non-root user
USER appuser

# Copy application files
COPY --chown=appuser:appuser pyproject.toml uv.lock ./
COPY --chown=appuser:appuser *.py ./
COPY --chown=appuser:appuser api ./api
COPY --chown=appuser:appuser configuration ./configuration
COPY --chown=appuser:appuser invoice_processing ./invoice_processing

# Install dependencies into a virtual environment
RUN uv venv && \
    uv sync --frozen --no-dev

# Expose the port the app runs on
EXPOSE 8000

# Start server with basic configuration for debugging
CMD ["/bin/bash", "-c", "source .venv/bin/activate && uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} --log-level debug"]
