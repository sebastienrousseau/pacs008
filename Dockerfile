FROM python:3.12-slim AS base

LABEL maintainer="Sebastien Rousseau <sebastian.rousseau@gmail.com>"
LABEL description="Pacs008 ISO 20022 pacs.008 XML Generation API"

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy dependency files first (layer caching)
COPY pyproject.toml ./

# Install dependencies without dev deps
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --only main --no-root

# Copy application code
COPY pacs008/ ./pacs008/

# Install the package itself
RUN poetry install --no-interaction --only-root

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Run the API server
CMD ["python", "-m", "uvicorn", "pacs008.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
