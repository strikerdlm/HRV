# Author: Dr Diego Malpica MD
#
# Dockerfile for Reflex v2 frontend (nginx + static export)
#
# This builds the frontend as static files and serves them via nginx.
# The nginx reverse proxy handles WebSocket upgrades for /_event/.
#
# Reference: https://reflex.dev/blog/2024-10-8-self-hosting-reflex-with-docker/

# Stage 1: Build the Reflex frontend
FROM python:3.12-slim AS builder

WORKDIR /app

# System dependencies for build
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements_reflex.txt /app/requirements_reflex.txt
RUN pip install --no-cache-dir --upgrade pip wheel \
    && pip install --no-cache-dir -r /app/requirements_reflex.txt

# Copy app code
COPY app/ /app/app/
COPY reflex_app/ /app/reflex_app/
COPY README.md /app/README.md
COPY CHANGELOG.md /app/CHANGELOG.md
COPY docs/ /app/docs/

# Set environment for build
ENV PYTHONPATH=/app

# API_URL for the frontend build:
# When using nginx reverse proxy, the WebSocket connections go through nginx,
# so API_URL should point to the nginx server (same origin as frontend).
# This gets baked into the static JS files at build time.
#
# For local Docker: http://localhost:3001 (nginx frontend port)
# For production: your domain (e.g., https://hrv.example.com)
ARG API_URL=http://localhost:3001
ENV API_URL=${API_URL}

# Disable SSR to avoid prerendering crashes during export
ENV REFLEX_SSR=false

# Build the frontend static files
WORKDIR /app/reflex_app
RUN reflex export --frontend-only --no-zip

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy static files from builder
# Note: Reflex export outputs to .web/build/client/ (not _static)
COPY --from=builder /app/reflex_app/.web/build/client /usr/share/nginx/html

# Copy nginx configuration
COPY reflex_app/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
