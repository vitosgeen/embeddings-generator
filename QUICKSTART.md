# 🚀 Quick Start Guide - Embeddings Service

## TL;DR - Get Running in 2 Minutes

```bash
# One-liner installation
git clone https://github.com/vitosgeen/embeddings-generator.git && \
cd embeddings-generator && \
echo "API_KEYS=admin:sk-admin-secret123" > .env && \
make deps && make proto && make run
```

Then open: http://localhost:8000

---

## Step-by-Step (5 minutes)

### 1. Clone & Setup
```bash
git clone https://github.com/vitosgeen/embeddings-generator.git
cd embeddings-generator
make venv
make deps
```

### 2. Configure
```bash
echo "API_KEYS=admin:sk-admin-secret123" > .env
```

### 3. Build & Run
```bash
make proto
make run
```

### 4. Test It
```bash
# In a new terminal
curl -X POST http://localhost:8000/embed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-admin-secret123" \
  -d '{"text": "Hello, AI world!"}'
```

---

## What You Get

✅ **REST API** on http://localhost:8000
- `/embed` - Generate embeddings
- `/health` - Service health check
- `/docs` - Interactive API documentation
- `/vdb/*` - Vector database operations

✅ **gRPC API** on port 50051
- High-performance binary protocol
- Streaming support

✅ **Vector Database**
- Store and search embeddings
- Multi-project support
- Automatic sharding

✅ **Authentication**
- API key-based security
- Role-based access control
- Admin dashboard at `/admin/login`

---

## Common Commands

```bash
# Start service
make run

# Stop service (force kill by port)
make stop

# Check running services
make ps

# Stop only REST API
make stop-rest

# Stop only gRPC server
make stop-grpc

# Run tests
make test

# Clean everything
make clean

# View logs with debug level
LOG_LEVEL=DEBUG make run
```

---

## Next Steps

1. **Read the Full README**: [README.md](README.md)
2. **Explore API Docs**: http://localhost:8000/docs
3. **Try Vector Database**: See "Vector Database API Usage" in README
4. **Configure for Production**: Check "Configuration" section in README

---

## Need Help?

- **Troubleshooting**: See "Troubleshooting" section in README.md
- **Issues**: https://github.com/vitosgeen/embeddings-generator/issues
- **Documentation**: Full API docs available at `/docs` endpoint
