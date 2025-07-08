FROM python:3.12-alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    curl \
    postgresql-client \
    libpq-dev

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY .env.example .env
COPY docker-entrypoint.sh ./

# Make entrypoint executable
RUN chmod +x /app/docker-entrypoint.sh

# Set environment variables
ENV PYTHONPATH=/app/src

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application with entrypoint script
ENTRYPOINT ["/app/docker-entrypoint.sh"]