# Dockerfile for Evaluation API Service
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8001

# Cloud Run specific: Use PORT environment variable
ENV ADAM_API_URL=http://adam-api:8000

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
# Remove empty/invalid uv.lock file if it exists (uv will generate a new one)
RUN if [ -f uv.lock ] && ([ ! -s uv.lock ] || ! head -n 1 uv.lock 2>/dev/null | grep -q "version"); then \
        echo "Removing invalid/empty uv.lock file"; \
        rm -f uv.lock; \
    fi && \
    if [ -f uv.lock ]; then \
        uv sync --frozen || (echo "Lock file invalid, regenerating..." && rm -f uv.lock && uv sync); \
    else \
        echo "No lock file, generating new one..."; \
        uv sync; \
    fi && \
    uv pip list

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8001}/health || exit 1

# Run the application
CMD exec uv run uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8001} \
    --workers 1 \
    --timeout-keep-alive 65 \
    --timeout-graceful-shutdown 10 \
    --log-level info

