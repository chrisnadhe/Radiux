# ===========================================================================
# Dockerfile — Radiux App (FastAPI + uv)
# Multi-stage build: builder (install deps) → runtime (minimal image)
# ===========================================================================

# ---------------------------------------------------------------------------
# Stage 1: builder — install dependencies via uv
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS builder

# Hindari interaksi debconf saat install package
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies minimal yang dibutuhkan psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY --from=ghcr.io/astral-sh/uv:latest /uvx /usr/local/bin/uvx

WORKDIR /build

# Copy dependency files dulu (layer caching — rebuild hanya jika ini berubah)
COPY pyproject.toml ./
# Buat uv.lock kosong jika belum ada agar uv tidak error
RUN touch uv.lock

# Install production dependencies ke virtual environment
RUN uv sync --no-dev --frozen --no-install-project

# ---------------------------------------------------------------------------
# Stage 2: runtime — image minimal untuk production
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# Runtime dependencies (libpq untuk psycopg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Non-root user untuk keamanan
RUN groupadd --gid 1001 radiux \
    && useradd --uid 1001 --gid radiux --shell /bin/bash --create-home radiux

WORKDIR /app

# Copy virtual environment dari builder
COPY --from=builder /build/.venv ./.venv

# Copy source code
COPY --chown=radiux:radiux . .

USER radiux

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Production: uvicorn tanpa --reload
# Development: di-override via docker-compose.override.yml dengan --reload
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
