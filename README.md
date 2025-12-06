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
- **Authentication & Authorization**: Secure API access with role-based permissions
- **Admin Dashboard**: Web-based interface for user and project management

---

## 📋 Prerequisites

Before starting, ensure you have the following installed:

- **Python 3.8+** (Python 3.10+ recommended)
- **pip** (Python package manager)
- **Git** (for cloning the repository)
- **4GB+ RAM** (for running embedding models)
- **Optional**: CUDA-compatible GPU for faster inference

Check your Python version:
```bash
python3 --version  # Should show 3.8 or higher
```

---

## 🚀 Step-by-Step Installation Guide

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/vitosgeen/embeddings-generator.git

# Navigate to the project directory
cd embeddings-generator
```

### Step 2: Set Up Python Environment

```bash
# Create a virtual environment
make venv

# OR manually:
python3 -m venv .venv
```

### Step 3: Install Dependencies

```bash
# Install all required packages
make deps

# OR manually:
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Expected installation time**: 2-5 minutes (depending on your internet connection)

### Step 4: Generate gRPC Protocol Buffers

```bash
# Generate gRPC Python files from proto definitions
make proto

# OR manually:
source .venv/bin/activate
python3 -m grpc_tools.protoc \
    -I proto \
    --python_out=proto \
    --grpc_python_out=proto \
    proto/embeddings.proto
```

### Step 5: Configure Environment Variables

```bash
# Copy the example environment file
cp .env_example .env

# Edit the configuration (optional - defaults work for local development)
nano .env  # or use your preferred editor (vim, code, etc.)
```

**Minimum Required Configuration** (create `.env` file):
```bash
# Authentication (REQUIRED)
API_KEYS=admin:sk-admin-secret123,user:sk-user-secret456

# Admin Dashboard Password (change in production!)
ADMIN_PASSWORD=admin123

# Optional configurations (defaults shown)
MODEL_ID=BAAI/bge-base-en-v1.5  # Embedding model
DEVICE=auto                      # Device: auto/cpu/cuda/mps
REST_PORT=8000                   # REST API port
GRPC_PORT=50051                  # gRPC port
VDB_STORAGE_PATH=./vdb-data      # Vector DB storage
AUTH_DB_PATH=./auth.db           # Authentication database
LOG_LEVEL=INFO                   # Logging level
```

### Step 6: Initialize the Database

```bash
# The database will be automatically created on first run
# OR manually initialize:
source .venv/bin/activate
python3 -c "from app.adapters.infra.auth_storage import AuthDatabase; AuthDatabase('./auth.db').create_tables()"
```

### Step 7: Start the Application

```bash
# Start both REST and gRPC servers
make run

# OR manually:
source .venv/bin/activate
python3 main.py
```

**You should see output like:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     gRPC server started on port 50051
```

### Step 8: Verify Installation

**Open your browser and visit:**
- **Main Interface**: http://localhost:8000 (with quick API key testing)
- **User Documentation**: http://localhost:8000/user-docs (interactive API testing)
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Admin Dashboard**: http://localhost:8000/admin/login (user & key management)
- **Health Check**: http://localhost:8000/health

**Test with curl:**
```bash
# Health check
curl http://localhost:8000/health

# Generate embedding (requires API key)
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-secret123" \
  -d '{"text": "Hello, world!"}'
```

**Expected response:**
```json
{
  "model_id": "BAAI/bge-base-en-v1.5",
  "dim": 768,
  "embedding": [0.123, -0.456, ...],
  "requested_by": "admin",
  "user_role": "admin"
}
```

**Interactive API Testing:**

Visit **http://localhost:8000/user-docs** for a user-friendly interface where you can:
- Enter your API key once and test all endpoints
- Generate single or batch embeddings with live results
- Create and manage vector database projects
- Store and search vectors with semantic similarity
- See real-time request/response data with syntax highlighting
- Copy code examples for your applications

The main page (http://localhost:8000) also includes a quick API key input for convenient testing of basic features.

**Postman Collection:**

Import `Embeddings_Service.postman_collection.json` into Postman for a complete collection of API requests:
- Pre-configured authentication with collection variables
- All REST API endpoints organized by category
- Example requests with realistic payloads
- Complete workflow examples (create project → generate embeddings → store → search)
- Easy testing with environment variables (`base_url`, `api_key`, `project_id`)

---

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
| `make stop` | Force stop services by killing processes on ports 8000 & 50051 |
| `make stop-rest` | Stop only REST API (port 8000) |
| `make stop-grpc` | Stop only gRPC server (port 50051) |
| `make ps` | Show running services on ports 8000 & 50051 |
| `make test` | Run all tests |
| `make test-unit` | Run only unit tests |
| `make test-integration` | Run only integration tests |
| `make test-coverage` | Run tests with coverage report |
| `make clean` | Remove virtual environment and generated gRPC files |
| `make vdb-clean` | Clean vector database data |

---

## 🚀 Quick Start (One-Liner)

For experienced developers:

```bash
git clone https://github.com/vitosgeen/embeddings-generator.git && \
cd embeddings-generator && \
echo "API_KEYS=admin:sk-admin-secret123" > .env && \
make deps && make proto && make run
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
| `MODEL_ID` | Sentence Transformer model from Hugging Face | `intfloat/multilingual-e5-base` | `BAAI/bge-base-en-v1.5` |
| `DEVICE` | Processing device (auto/cpu/cuda/mps) | `auto` | `cuda` |
| `BATCH_SIZE` | Batch size for processing | `32` | `64` |
| `REST_PORT` | REST API port | `8000` | `8080` |
| `GRPC_PORT` | gRPC API port | `50051` | `9090` |
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` |
| `API_KEYS` | Authentication keys (account:key pairs) | Required | `admin:sk-admin-key123` |
| `ADMIN_PASSWORD` | Admin dashboard login password | `admin123` | `MyS3cur3P@ss!` |
| `VDB_STORAGE_PATH` | Vector database storage directory | `./vdb-data` | `/srv/vdb-data` |

### 🔐 Authentication Setup

The service uses two types of authentication:

#### 1. API Keys (for programmatic access)

Configure API keys in your `.env` file for accessing the REST and gRPC APIs:

```bash
# Format: account_name:api_key,account_name2:api_key2
API_KEYS=admin:sk-admin-your-secret-key,user1:sk-user1-another-key,monitoring:sk-monitor-key
```

#### 2. Admin Dashboard Password (for web interface)

Set the password for the admin web dashboard at `/admin/login`:

```bash
# Default is 'admin123' - CHANGE THIS IN PRODUCTION!
ADMIN_PASSWORD=your-secure-password-here
```

**To change the admin password:**

1. **Edit `.env` file**:
   ```bash
   ADMIN_PASSWORD=MyNewSecurePassword123!
   ```

2. **Or use the password setup script**:
   ```bash
   python3 scripts/set_admin_password.py
   ```

3. **Restart the service**:
   ```bash
   make stop && make run
   ```

**Login Credentials:**
- **URL**: http://localhost:8000/admin/login
- **Username**: `admin` (any user with admin role)
- **Password**: Value from `ADMIN_PASSWORD` in `.env`

**Security Best Practices:**
- Change default password immediately in production
- Use strong passwords (12+ characters, mixed case, numbers, symbols)
- Use strong, unique API keys (32+ characters)
- Rotate keys and passwords regularly
- Store secrets securely (use secret management systems)
- Use HTTPS/TLS for all communications
- Never commit `.env` file to version control

### 📋 Model Options

The service supports **dual-model architecture** for different use cases:

**Default Models:**
- **`fast`**: `intfloat/multilingual-e5-base` (768 dims) - Quick responses for support bots, chat, short messages
- **`thinking`**: `intfloat/multilingual-e5-large` (1024 dims) - Deep analysis for long documents, emails, articles

**How to use:**
```bash
# Fast model (default) - for chat/support bots
curl -X POST /embed -d '{"text": "How can I help?", "model": "fast"}'

# Thinking model - for long documents/analysis  
curl -X POST /embed -d '{"text": "Long email content...", "model": "thinking"}'
```

**Alternative Models** (configure in .env):
- **English-only**: `BAAI/bge-base-en-v1.5` (768 dim, English only)
- **Lightweight**: `sentence-transformers/all-MiniLM-L6-v2` (384 dim, fast)
- **Best Quality**: `BAAI/bge-m3` (1024 dim, requires PyTorch 2.6+)

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. **Port Already in Use**

**Problem**: `Address already in use` error when starting the service.

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000  # On Linux/Mac
netstat -ano | findstr :8000  # On Windows

# Kill the process or change the port in .env
echo "REST_PORT=8001" >> .env
```

#### 2. **API Key Authentication Fails**

**Problem**: `401 Unauthorized` or `403 Forbidden` errors.

**Solution**:
```bash
# Verify your .env file has API_KEYS set
cat .env | grep API_KEYS

# Make sure you're using the correct format
echo "API_KEYS=admin:sk-admin-secret123" > .env

# Restart the service after updating
make run
```

#### 3. **Module Import Errors**

**Problem**: `ModuleNotFoundError` or `ImportError`.

**Solution**:
```bash
# Activate virtual environment
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Regenerate proto files
make proto
```

#### 4. **Model Download Issues**

**Problem**: Model fails to download or times out.

**Solution**:
```bash
# Pre-download the model (requires internet)
source .venv/bin/activate
python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-base')"

# Or use a smaller/faster model
echo "MODEL_ID=sentence-transformers/all-MiniLM-L6-v2" >> .env
```

#### 5. **Memory Issues**

**Problem**: Out of memory errors or slow performance.

**Solution**:
```bash
# Reduce batch size in .env
echo "BATCH_SIZE=8" >> .env

# Use a smaller model
echo "MODEL_ID=sentence-transformers/all-MiniLM-L6-v2" >> .env

# Force CPU mode (uses less memory)
echo "DEVICE=cpu" >> .env
```

#### 6. **Tests Failing**

**Problem**: Test failures when running `make test`.

**Solution**:
```bash
# Clean VDB test data before running tests
rm -rf vdb-data/test_* vdb-data/*_test_* vdb-data/*_proj

# Run tests with verbose output
python3 -m pytest tests/ -v

# Run specific test
python3 -m pytest tests/test_auth.py -v
```

#### 7. **Database Lock Issues**

**Problem**: `database is locked` errors.

**Solution**:
```bash
# Stop all running instances
pkill -f "python3 main.py"

# Remove lock files if they exist
rm -f auth.db-shm auth.db-wal

# Restart the service
make run
```

#### 8. **gRPC Connection Errors**

**Problem**: Cannot connect to gRPC server.

**Solution**:
```bash
# Verify gRPC port is not blocked
netstat -tuln | grep 50051

# Check if proto files are generated
ls -la proto/embeddings_pb2*.py

# Regenerate proto files
make proto
```

### Getting Help

If you encounter issues not covered here:

1. **Check Logs**: Look for detailed error messages in the terminal output
2. **Enable Debug Logging**: Set `LOG_LEVEL=DEBUG` in your `.env` file
3. **Search Issues**: Check [GitHub Issues](https://github.com/vitosgeen/embeddings-generator/issues)
4. **Create Issue**: Open a new issue with:
   - Error message
   - Steps to reproduce
   - Python version (`python3 --version`)
   - Operating system

---

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

