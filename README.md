# 🧠 Embeddings + Vector Database Service

[![CI/CD Pipeline](https://github.com/vitosgeen/embeddings-generator/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/vitosgeen/embeddings-generator/actions/workflows/ci-cd.yml)
[![codecov](https://codecov.io/gh/vitosgeen/embeddings-generator/branch/main/graph/badge.svg)](https://codecov.io/gh/vitosgeen/embeddings-generator)

A lightweight **REST + gRPC microservice** for generating **text embeddings** and storing/searching **vector data** using [Sentence Transformers](https://www.sbert.net/) and [LanceDB](https://lancedb.com/).  
Implements clean architecture with dual functionality: **embedding generation** and **vector database** operations.

---

## ⚙️ Description

This unified service provides:
- **Embedding Generation**: Convert text to vector embeddings using state-of-the-art transformer models
- **Vector Database**: Store, search, and manage vector embeddings with automatic sharding
- **Multi-tenancy**: Support multiple projects with isolated storage
- **REST + gRPC**: Dual API interfaces for maximum flexibility

## 🎯 Demo

![Embeddings Service Interface](./assets/demo-interface.png)

*The service provides a clean web interface showing API endpoints, current model information, and interactive documentation through Swagger UI.*

---

## 🧰 Makefile Commands

| Command | Description |
|----------|--------------|
| `make venv` | Create a Python virtual environment |
| `make deps` | Install dependencies from `requirements.txt` |
| `make proto` | Generate gRPC Python files from `proto/embeddings.proto` |
| `make run` | Run the service locally (REST + gRPC) |
| `make dev` | Regenerate `.proto` files and run immediately |
| `make clean` | Remove virtual environment and generated gRPC files |

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
make deps

# 2. Generate gRPC stubs
make proto

# 3. Run the service
make run
```

## ⚙️ Configuration

The service uses environment variables for configuration. Copy the example configuration file and customize it:

```bash
# Copy the example configuration
cp .env_example .env

# Edit the configuration file
nano .env  # or use your preferred editor
```

### 🔧 Key Configuration Options

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MODEL_ID` | Sentence Transformer model from Hugging Face | `BAAI/bge-base-en-v1.5` | `sentence-transformers/all-MiniLM-L6-v2` |
| `DEVICE` | Processing device (auto/cpu/cuda/mps) | `auto` | `cuda` |
| `BATCH_SIZE` | Batch size for processing | `32` | `64` |
| `REST_PORT` | REST API port | `8000` | `8080` |
| `GRPC_PORT` | gRPC API port | `50051` | `9090` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `API_KEYS` | Authentication keys (account:key pairs) | Required | `admin:sk-admin-key123` |
| `VDB_STORAGE_PATH` | Vector database storage directory | `./vdb-data` | `/srv/vdb-data` |

### 🔐 Authentication Setup

The service requires API keys for the `/embed` endpoint. Configure them in your `.env` file:

```bash
# Format: account_name:api_key,account_name2:api_key2
API_KEYS=admin:sk-admin-your-secret-key,user1:sk-user1-another-key,monitoring:sk-monitor-key
```

**Security Best Practices:**
- Use strong, unique API keys (32+ characters)
- Rotate keys regularly in production
- Store secrets securely (use secret management systems)
- Use HTTPS/TLS for all communications

### 📋 Model Options

Popular model choices for different use cases:

- **General Purpose**: `BAAI/bge-base-en-v1.5` (768 dim, high quality)
- **Fast & Lightweight**: `sentence-transformers/all-MiniLM-L6-v2` (384 dim)
- **High Quality**: `sentence-transformers/all-mpnet-base-v2` (768 dim)
- **Multilingual**: `intfloat/multilingual-e5-base` (768 dim)


## 🗄️ Vector Database API Usage

The service includes a complete vector database for storing and searching embeddings. Perfect for building semantic search, recommendation systems, and RAG applications.

---

### 🔑 All VDB endpoints require API key authentication

Include your API key in the `Authorization` header for all requests:
```bash
-H "Authorization: Bearer sk-admin-your-secret-key"
```

---

### 📁 Projects and Collections

#### Create a project
```bash
curl -X POST http://localhost:8000/vdb/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{
    "project_id": "my_app",
    "metadata": {"description": "My application vectors"}
  }'
```

#### List all projects
```bash
curl -X GET http://localhost:8000/vdb/projects \
  -H "Authorization: Bearer sk-admin-your-secret-key"
```

#### Create a collection
```bash
curl -X POST http://localhost:8000/vdb/projects/my_app/collections \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{
    "name": "documents",
    "dimension": 768,
    "metric": "cosine",
    "shards": 4,
    "description": "Document embeddings"
  }'
```

**Distance Metrics:**
- `cosine` - Cosine similarity (most common for text)
- `dot` - Dot product similarity
- `L2` - Euclidean distance

#### List collections
```bash
curl -X GET http://localhost:8000/vdb/projects/my_app/collections \
  -H "Authorization: Bearer sk-admin-your-secret-key"
```

---

### ➕ Add Vectors

```bash
curl -X POST http://localhost:8000/vdb/projects/my_app/collections/documents/add \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{
    "id": "doc_001",
    "embedding": [0.1, 0.2, ..., 0.768],
    "metadata": {
      "title": "Introduction to AI",
      "category": "technology"
    },
    "document": "Artificial intelligence is transforming..."
  }'
```

**With debug info:**
```bash
curl -X POST "http://localhost:8000/vdb/projects/my_app/collections/documents/add?include_debug=true" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{...}'
```

---

### 🔍 Search Vectors

```bash
curl -X POST http://localhost:8000/vdb/projects/my_app/collections/documents/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{
    "query_vector": [0.1, 0.2, ..., 0.768],
    "limit": 10
  }'
```

**With debug info** to see shard performance:
```bash
curl -X POST "http://localhost:8000/vdb/projects/my_app/collections/documents/search?include_debug=true" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{...}'
```

---

### 🗑️ Delete Vectors

```bash
curl -X DELETE http://localhost:8000/vdb/projects/my_app/collections/documents/vectors/doc_001 \
  -H "Authorization: Bearer sk-admin-your-secret-key"
```

---

### 🔄 Complete Workflow Example

```bash
# 1. Generate an embedding
EMBEDDING=$(curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{"text": "Introduction to machine learning", "normalize": true}' \
  | jq -r '.embedding')

# 2. Store it in the vector database
curl -X POST http://localhost:8000/vdb/projects/my_app/collections/documents/add \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d "{
    \"id\": \"doc_ml_intro\",
    \"embedding\": $EMBEDDING,
    \"metadata\": {\"title\": \"ML Introduction\", \"category\": \"education\"},
    \"document\": \"Introduction to machine learning\"
  }"

# 3. Search for similar documents
QUERY_EMBEDDING=$(curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{"text": "What is AI?", "task_type": "query", "normalize": true}' \
  | jq -r '.embedding')

curl -X POST http://localhost:8000/vdb/projects/my_app/collections/documents/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d "{\"query_vector\": $QUERY_EMBEDDING, \"limit\": 5}"
```

---

### 🏗️ VDB Storage Architecture

The vector database uses automatic sharding for horizontal scalability:

```
./vdb-data/
└── my_app/                    # Project
    ├── _project.json          # Project metadata
    └── collections/
        └── documents/         # Collection
            ├── _config.json   # Collection config
            ├── shard_0/       # Auto-sharded storage
            ├── shard_1/
            ├── shard_2/
            └── shard_3/
```

**Key Features:**
- **Automatic sharding** based on vector ID hash
- **Parallel search** across all shards
- **Isolated storage** per project
- **LanceDB backend** for efficient vector operations

---

## 🌐 REST API Usage (Embeddings)

The service exposes a REST interface powered by **FastAPI**.  
It allows you to send text or multiple texts and receive their vector embeddings in JSON format.

---

### 🧠 Endpoints

| Method | Endpoint | Description |
|--------|-----------|--------------|
| `GET`  | `/health` | Health check endpoint. Returns model, device, and vector size. |
| `POST` | `/embed`  | Generate embedding(s) for one or multiple texts. |

---

### ⚙️ Request formats

> **🔐 Authentication Required**: All `/embed` requests require a valid API key in the Authorization header.

#### 🔹 Single text

```bash
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{
    "text": "Artificial intelligence is amazing",
    "task_type": "passage",
    "normalize": true
  }'
```

#### 🔹 Multiple texts (batch mode)

```bash
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-your-secret-key" \
  -d '{
    "texts": [
      "Artificial intelligence is amazing",
      "Large language models are powerful"
    ],
    "task_type": "passage",
    "normalize": true
  }'
```

#### 🔹 Health check (no authentication required)

```bash
curl -X GET http://localhost:8000/health
```

#### 📊 Response format

```json
{
  "model_id": "BAAI/bge-base-en-v1.5",
  "dim": 768,
  "embedding": [0.1234, -0.5678, ...],
  "requested_by": "admin"
}
```

---

## 🚀 Deployment

### 🖥️ Local Development
```bash
# Quick start
make deps && make run
```

### 🌐 Production Deployment

Use the provided deployment script for easy setup:

```bash
# Local deployment
./deploy.sh local

# Production deployment (requires sudo)
./deploy.sh production

# Staging deployment
./deploy.sh staging
```

#### 🐍 Manual Python Deployment
```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the service
python main.py
```

#### ☁️ Cloud Deployment Options
- **AWS Lambda**: Serverless functions with API Gateway
- **Google Cloud Functions**: Event-driven serverless execution
- **Azure Functions**: Cloud-native function hosting
- **Kubernetes**: Container orchestration with auto-scaling
- **Cloud Run/Fargate**: Managed container services

> **Note**: Docker removed due to large image size (~6GB) caused by PyTorch and ML dependencies. Python virtual environments provide better performance and lower costs.

