# 🧠 Embeddings Service

[![CI/CD Pipeline](https://github.com/vitosgeen/embeddings-generator/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/vitosgeen/embeddings-generator/actions/workflows/ci-cd.yml)
[![codecov](https://codecov.io/gh/vitosgeen/embeddings-generator/branch/main/graph/badge.svg)](https://codecov.io/gh/vitosgeen/embeddings-generator)

A lightweight **REST + gRPC microservice** for generating **text embeddings** using [Sentence Transformers](https://www.sbert.net/).  
Implements a clean modular structure and can run locally or via Docker Compose.

---

## ⚙️ Description

This service accepts text input and returns vector embeddings.  
It’s designed for internal company usage — other systems can call it via REST or gRPC.

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


## 🌐 REST API Usage

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

