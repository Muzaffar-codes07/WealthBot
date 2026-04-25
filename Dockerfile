# =============================================================================
# WealthBot Backend Dockerfile
# Multi-stage build for production-grade deployment
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies.
#
# IMPORTANT: install CPU-only torch FIRST from PyTorch's CPU index. The
# default torch wheel on PyPI (Linux x86_64) declares the nvidia-* CUDA
# packages as required deps and balloons the image by ~3 GB. The +cpu
# variant does not declare those deps. Once torch is installed and meets
# the >=2.9.0 constraint, the next pip install sees it satisfied and
# doesn't reinstall — keeping the image lean.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production Runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Security: Create non-root user
RUN groupadd --gid 1000 wealthbot && \
    useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash wealthbot

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (including alembic for migrations)
COPY --chown=wealthbot:wealthbot . .

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Security: Switch to non-root user
USER wealthbot

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE 8000

# Use entrypoint script: runs migrations then starts uvicorn
ENTRYPOINT ["/app/docker-entrypoint.sh"]
