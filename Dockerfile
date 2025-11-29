# HRV Analysis Platform - Docker Image
# Author: Dr. Diego Malpica, MD - Aerospace Medicine Specialist
#
# Multi-stage build for optimized production image
# Base: Python 3.11 slim

# ---------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# ---------------------------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel \
    && pip install --no-cache-dir -r requirements.txt

# Install additional database dependencies
RUN pip install --no-cache-dir \
    psycopg2-binary \
    sqlalchemy \
    alembic \
    redis

# ---------------------------------------------------------------------------
# Stage 2: Runtime - Production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim as runtime

# Labels
LABEL maintainer="Dr. Diego Malpica <dmalpica@example.com>"
LABEL description="HRV Analysis Platform - Physiological Monitoring and Analysis"
LABEL version="1.0.0"

# Create non-root user for security
RUN groupadd --gid 1000 hrvuser \
    && useradd --uid 1000 --gid hrvuser --shell /bin/bash --create-home hrvuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=hrvuser:hrvuser app/ ./app/
COPY --chown=hrvuser:hrvuser docs/ ./docs/
COPY --chown=hrvuser:hrvuser README.md ./
COPY --chown=hrvuser:hrvuser CHANGELOG.md ./

# Create data directories
RUN mkdir -p /app/data /app/logs \
    && chown -R hrvuser:hrvuser /app

# Switch to non-root user
USER hrvuser

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    DATA_PATH=/app/data

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Entry point
ENTRYPOINT ["streamlit", "run"]
CMD ["app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

