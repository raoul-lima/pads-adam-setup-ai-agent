# Optimized Dockerfile for Google Cloud Run
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Cloud Run specific: Use PORT environment variable
ENV PORT=8000

# Install system dependencies (minimal for Cloud Run)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy uv installation script
COPY install-uv.sh .

# Install uv using the script
RUN chmod +x install-uv.sh && ./install-uv.sh

# Set PATH for uv
ENV PATH="/root/.cargo/bin:/root/.local/bin:$PATH"

# Copy dependency files first (better caching)
COPY pyproject.toml uv.lock* ./

# Install Python dependencies with uv
RUN (uv sync --frozen || uv sync) && \
    uv pip list

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p local_data logs

# Remove VOLUME directive (Cloud Run doesn't support volumes)
# VOLUME /app/local_data  # REMOVED for Cloud Run

# Cloud Run uses PORT environment variable
EXPOSE 8000

# Health check (note: Cloud Run uses its own health checks)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# IMPORTANT: Single worker for Cloud Run (it handles scaling)
# Use uvicorn directly with proper settings
CMD exec uv run uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --timeout-keep-alive 65 \
    --timeout-graceful-shutdown 10 \
    --log-level info

