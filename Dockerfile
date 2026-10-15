# ShowUp - Local-first No-Show Reduction Desktop Web App
FROM python:3.12-slim

# System setup
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    DO_NOT_TRACK=1 \
    TRANSFORMERS_OFFLINE=1 \
    SHOWUP_DATA_DIR=/data

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project specification and install dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy source tree and assets
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY docs/ ./docs/

# Create data volume directory
RUN mkdir -p /data && chmod 700 /data
VOLUME /data

# Streamlit port
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

ENTRYPOINT ["streamlit", "run", "src/showup/ui/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
