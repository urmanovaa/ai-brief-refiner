# =====================================================
# AI Brief Refiner - Dockerfile
# =====================================================
# Multi-stage build for smaller image size

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# =====================================================
# Production stage
# =====================================================
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash botuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/botuser/.local

# Set PATH
ENV PATH=/home/botuser/.local/bin:$PATH

# Copy application code
COPY --chown=botuser:botuser . .

# Create necessary directories
RUN mkdir -p /app/data /app/chroma_db /app/temp \
    && chown -R botuser:botuser /app

# Switch to non-root user
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0 if os.path.exists('/app/main.py') else 1)"

# Run the bot
CMD ["python", "main.py"]

