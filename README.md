# 🧠 Embeddings Service

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

#### 🔹 Single text

```bash
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Artificial intelligence is amazing"
  }'

#### 🔹 Multiple texts (batch mode)
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Artificial intelligence is amazing",
      "Large language models are powerful"
    ]
  }'

