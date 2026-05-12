# Build stage: install Python dependencies with uv
# Build from repo root: docker build -f backend/Dockerfile .
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests first so layer is cached when only source changes
COPY backend/pyproject.toml backend/uv.lock ./

# Install runtime dependencies into an isolated virtual environment
RUN uv sync --frozen --no-dev

# Runtime stage: lean image with only what the app needs
FROM python:3.11-slim AS runtime

# curl is required for smoke-testing endpoints from inside the container
# per development.md — do not remove
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY backend/src/ ./src/

# Copy baked data artifacts — pool, Chroma index, and exclusion log
# These are committed to the repo and built once at dataset-prep time (T01)
COPY data/pool/ ./data/pool/
COPY data/chroma/ ./data/chroma/
COPY data/exclusions.json ./data/exclusions.json

# DATA_DIR is resolved at runtime by vectorstore/chroma.py.
# The default (repo root data/) works locally; this override points to the
# baked artifacts inside the container image.
ENV DATA_DIR=/app/data
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/dataset || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
