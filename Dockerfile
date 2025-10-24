FROM python:3.11-slim AS builder
WORKDIR /app

COPY requirements.txt ./
COPY proto ./proto

# Install system deps + grpcio-tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential protobuf-compiler python3-dev \
 && pip install --no-cache-dir grpcio-tools \
 && rm -rf /var/lib/apt/lists/*

# Run proto generation
RUN mkdir -p app/adapters/grpc/generated && \
    python -m grpc_tools.protoc -I proto \
      --python_out=app/adapters/grpc/generated \
      --grpc_python_out=app/adapters/grpc/generated \
      proto/embeddings.proto

# Production stage
FROM python:3.11-slim AS production

# Add labels for better image identification
LABEL org.opencontainers.image.source="https://github.com/vitosgeen/embeddings-generator"
LABEL org.opencontainers.image.description="Embeddings Service - REST + gRPC microservice for text embeddings"
LABEL org.opencontainers.image.version="1.0.0"

WORKDIR /app

# Install runtime dependencies only
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
 && rm requirements.txt

# Copy application code
COPY app ./app
COPY main.py ./

# Copy generated proto files from builder stage
COPY --from=builder /app/app/adapters/grpc/generated ./proto/

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser \
 && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Expose ports
EXPOSE 8000 50051

# Run the service
CMD ["python", "main.py"]
