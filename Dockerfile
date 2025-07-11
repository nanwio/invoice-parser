# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:debian-slim

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Install dependencies
# Update GPG keys and install poppler-utils
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    gnupg \
    && apt-key adv --refresh-keys --keyserver keyserver.ubuntu.com \
    && apt-get update \
    && apt-get install -y --no-install-recommends poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD app /app/app
ADD pyproject.toml /app
ADD uv.lock /app
ADD README.md /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT []

EXPOSE 8000

# Start the server
CMD ["uv", "run", "python", "app/server.py"]
