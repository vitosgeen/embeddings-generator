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
