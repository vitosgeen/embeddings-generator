# 🚀 Quick Start Guide - Embeddings Service

## TL;DR - Get Running in 2 Minutes

```bash
# One-liner installation
git clone https://github.com/vitosgeen/embeddings-generator.git && \
cd embeddings-generator && \
echo "API_KEYS=admin:sk-admin-secret123" > .env && \
make setup
```

Then open: http://localhost:8000

---

## Step-by-Step (3 minutes)

### 1. Clone Repository
```bash
git clone https://github.com/vitosgeen/embeddings-generator.git
cd embeddings-generator
```

### 2. Setup Everything (installs deps + generates proto files)
```bash
make setup
```

**What this does:**
- Creates Python virtual environment
- Installs all dependencies (including pandas for DB Explorer)
- Generates gRPC protocol buffer files
- Verifies everything is ready

### 3. Configure API Key
```bash
echo "API_KEYS=admin:sk-admin-secret123" > .env
```

### 4. Start Service
```bash
make run
```

### 5. Test It
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

## 🔍 Quick Start: Database Explorer (New!)

### What is it?
Visual tool to explore your sharded vector database through an intuitive web interface.

### Access in 3 Steps

**Step 1**: Login to admin dashboard
```
http://localhost:8000/admin/login
Username: admin
Password: admin123
```

**Step 2**: Click "🔍 DB Explorer" in the navigation menu

**Step 3**: Start exploring! Three ways to browse your data:

#### Method 1: Quick Browse (Fastest - 2 clicks)
```
Projects tab → Click any collection button → See rows instantly
Example: Click "faq_docs" button → Browse tab auto-opens with data
```

#### Method 2: Visual Exploration (3 clicks)
```
Projects tab → Click project card → Click "📋 Browse Rows" on any collection
Example: Click "ChatBot" project → Modal opens → Click "Browse Rows" on "faq_docs"
```

#### Method 3: Browse by Shard (Advanced)
```
Projects tab → Click project → See shard distribution → Click green shard box
Example: Click project → Modal shows "Shard 3: 156 docs" → Click box → Rows load
```

### Example: Create & Browse Data in 2 Minutes

```bash
# 1. Create a project with sample data
curl -X POST http://localhost:8000/vdb/documents/batch \
  -H "Authorization: Bearer sk-admin-secret123" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "my_faq",
    "collection": "questions",
    "documents": [
      {
        "id": "q1",
        "document": "How do I reset my password?",
        "metadata": {"category": "auth", "priority": "high"}
      },
      {
        "id": "q2", 
        "document": "What are your business hours?",
        "metadata": {"category": "general", "priority": "medium"}
      },
      {
        "id": "q3",
        "document": "How can I delete my account?",
        "metadata": {"category": "account", "priority": "high"}
      }
    ]
  }'

# 2. Open explorer
# http://localhost:8000/admin/explorer

# 3. Click "questions" button next to "my_faq" project
# → Browse tab opens automatically
# → See your 3 documents in a table
# → Click "View" to see full vector data (384 dimensions)
```

### Explorer Features

**4 Powerful Tabs**:
1. **Projects** - List all projects with quick browse buttons
2. **Browse Rows** - Table view of actual vector data
3. **Search Vector** - Look up documents by ID
4. **Auth Database** - View users and API usage stats

**What You Can See**:
- Document IDs and text content
- Metadata (JSON format)
- Vector dimensions (384 for default model)
- Created timestamps
- Shard distribution (visual grid showing data spread)
- Collection statistics (document count per collection)

**Smart Features**:
- Auto-fill forms when navigating from projects
- Form highlighting (blue ring) shows where you landed
- Clickable shards auto-load rows
- Truncated text with hover to see full content
- Row details modal for full vector inspection
- Real-time stats on Auth tab

### CLI Tools (Alternative)

Prefer command line? Use the interactive explorer:

```bash
python scripts/db_explorer.py
```

Menu options:
```
1. List all projects
2. Show project collections
3. List vectors in collection
4. Get vector by ID
5. Search similar vectors
6. Collection statistics
7. List shards for collection
8. View Auth Database users
9. View API usage tracking
10. Generate usage report
```

---

## Next Steps

1. **Read the Full README**: [README.md](README.md)
2. **Explore API Docs**: http://localhost:8000/docs
3. **Database Explorer Guides**:
   - Quick Start: [docs/EXPLORER_QUICK_START.md](docs/EXPLORER_QUICK_START.md)
   - Visual Guide: [docs/EXPLORER_VISUAL_GUIDE.md](docs/EXPLORER_VISUAL_GUIDE.md)
   - Navigation Flow: [docs/EXPLORER_NAVIGATION_FLOW.md](docs/EXPLORER_NAVIGATION_FLOW.md)
4. **Try Vector Search**: See "Vector Database API Usage" in README
5. **Configure for Production**: Check "Configuration" section in README

---

## Troubleshooting

### Service Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill existing process
make stop
# Try again
make run
```

### Can't Access Admin Dashboard
```bash
# Reset admin password
python -c "from app.bootstrap_auth import bootstrap_auth; bootstrap_auth()"
# Default credentials: admin / admin123
```

### Database Explorer Shows No Data
```bash
# Check if database files exist
ls -lh data/*.db

# Verify your data is stored
curl http://localhost:8000/vdb/projects \
  -H "Authorization: Bearer sk-admin-secret123"

# If empty, insert sample data (see example above)
```

### Vector Dimensions Don't Match
```bash
# Check your model in config
grep SENTENCE_TRANSFORMER .env
# Default: all-MiniLM-L6-v2 (384 dimensions)

# If you changed models, ensure all documents use the same model
```

---

## Need Help?

- **Troubleshooting**: See "Troubleshooting" section in README.md
- **Issues**: https://github.com/vitosgeen/embeddings-generator/issues
- **Documentation**: Full API docs available at `/docs` endpoint
- **Explorer Docs**: See `docs/EXPLORER_*.md` files for detailed guides
