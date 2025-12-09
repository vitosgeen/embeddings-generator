# =============================
# Embeddings Service Makefile
# =============================

PYTHON := python3
VENV := .venv
VENV_BIN := $(VENV)/bin
PROTO_DIR := proto
GEN_DIR := proto
MAIN := main.py

.DEFAULT_GOAL := help

# -----------------------------
# 📖 Help
# -----------------------------

.PHONY: help
help:
	@echo "🚀 Embeddings Service - Available Commands"
	@echo "=========================================="
	@echo ""
	@echo "🔧 Setup & Installation:"
	@echo "  make setup         - Complete setup (recommended for first-time)"
	@echo "  make deps          - Install dependencies + generate proto"
	@echo "  make venv          - Create virtual environment only"
	@echo "  make proto         - Generate gRPC files"
	@echo "  make check-deps    - Verify all dependencies installed"
	@echo ""
	@echo "🚀 Running:"
	@echo "  make run           - Start the service (REST + gRPC)"
	@echo "  make dev           - Regenerate proto + run"
	@echo ""
	@echo "🛑 Stopping:"
	@echo "  make stop          - Stop all services"
	@echo "  make stop-rest     - Stop REST API only"
	@echo "  make stop-grpc     - Stop gRPC server only"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-coverage - Run tests with coverage"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean         - Remove venv and generated files"
	@echo "  make vdb-clean     - Clean vector database data"
	@echo ""
	@echo "ℹ️  Quick Start:"
	@echo "  1. make setup"
	@echo "  2. echo 'API_KEYS=admin:sk-admin-secret123' > .env"
	@echo "  3. make run"
	@echo ""

# -----------------------------
# 🧱 Virtualenv & dependencies
# -----------------------------

.PHONY: venv
venv:
	@echo "📦 Creating virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "✅ venv created."

.PHONY: deps
deps: venv
	@echo "📚 Installing dependencies..."
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -r requirements.txt
	@echo "✅ Dependencies installed."
	@echo "⚙️  Generating gRPC stubs..."
	@$(MAKE) proto-silent
	@echo "✅ Setup complete! Run 'make run' to start the service."

.PHONY: setup
setup: deps
	@echo "🎉 All done! Your environment is ready."
	@echo ""
	@echo "Next steps:"
	@echo "  1. Configure: echo 'API_KEYS=admin:sk-admin-secret123' > .env"
	@echo "  2. Start:     make run"
	@echo "  3. Test:      curl http://localhost:8000/health"
	@echo ""

.PHONY: check-deps
check-deps: venv
	@echo "🔍 Checking dependencies..."
	@$(VENV_BIN)/python scripts/check_dependencies.py

# -----------------------------
# ⚙️ Proto generation
# -----------------------------

.PHONY: proto
proto:
	@echo "⚙️  Generating gRPC Python stubs..."
	mkdir -p $(GEN_DIR)
	touch app/__init__.py
	touch app/adapters/__init__.py
	touch app/adapters/grpc/__init__.py
	touch $(GEN_DIR)/__init__.py
	@if [ ! -f "$(PROTO_DIR)/embeddings.proto" ]; then \
		echo "❌ ERROR: $(PROTO_DIR)/embeddings.proto not found!"; \
		exit 1; \
	fi
	PYTHONPATH=. $(VENV_BIN)/python -m grpc_tools.protoc \
		--proto_path=$(PROTO_DIR) \
		--python_out=$(GEN_DIR) \
		--grpc_python_out=$(GEN_DIR) \
		--pyi_out=$(GEN_DIR) \
		embeddings.proto
	@echo "🔧 Fixing imports in generated gRPC file..."
	sed -i 's/import embeddings_pb2 as embeddings__pb2/from . import embeddings_pb2 as embeddings__pb2/' $(GEN_DIR)/embeddings_pb2_grpc.py
	@echo "✅ Proto files generated in $(GEN_DIR)"
	@ls -l $(GEN_DIR) | grep "embeddings" || echo "⚠️  No embeddings_pb2 files found!"

.PHONY: proto-silent
proto-silent:
	@mkdir -p $(GEN_DIR)
	@touch app/__init__.py app/adapters/__init__.py app/adapters/grpc/__init__.py $(GEN_DIR)/__init__.py
	@if [ -f "$(PROTO_DIR)/embeddings.proto" ]; then \
		PYTHONPATH=. $(VENV_BIN)/python -m grpc_tools.protoc \
			--proto_path=$(PROTO_DIR) \
			--python_out=$(GEN_DIR) \
			--grpc_python_out=$(GEN_DIR) \
			--pyi_out=$(GEN_DIR) \
			embeddings.proto 2>/dev/null; \
		sed -i 's/import embeddings_pb2 as embeddings__pb2/from . import embeddings_pb2 as embeddings__pb2/' $(GEN_DIR)/embeddings_pb2_grpc.py 2>/dev/null; \
	fi

# -----------------------------
# 🚀 Run locally (REST + gRPC)
# -----------------------------

.PHONY: run
run:
	@echo "🚀 Starting embeddings service (REST + gRPC)..."
	PYTHONPATH=. $(VENV_BIN)/python $(MAIN)
# 	PYTHONPATH=app/adapters/grpc/generated:$(PYTHONPATH) $(VENV_BIN)/python $(MAIN)

# -----------------------------
# 🔁 Dev mode (auto proto + run)
# -----------------------------

.PHONY: dev
dev: proto run

# -----------------------------
# 🛑 Stop services
# -----------------------------

.PHONY: stop
stop:
	@echo "🛑 Stopping services by port..."
	@echo "Stopping REST API (port 8000)..."
	@lsof -ti:8000 | xargs -r kill -9 2>/dev/null || echo "  ℹ️  No process on port 8000"
	@echo "Stopping gRPC server (port 50051)..."
	@lsof -ti:50051 | xargs -r kill -9 2>/dev/null || echo "  ℹ️  No process on port 50051"
	@echo "✅ Services stopped."

.PHONY: stop-rest
stop-rest:
	@echo "🛑 Stopping REST API (port 8000)..."
	@lsof -ti:8000 | xargs -r kill -9 2>/dev/null && echo "✅ REST API stopped" || echo "ℹ️  No process on port 8000"

.PHONY: stop-grpc
stop-grpc:
	@echo "🛑 Stopping gRPC server (port 50051)..."
	@lsof -ti:50051 | xargs -r kill -9 2>/dev/null && echo "✅ gRPC server stopped" || echo "ℹ️  No process on port 50051"

.PHONY: ps
ps:
	@echo "📋 Checking running services..."
	@echo "REST API (port 8000):"
	@lsof -ti:8000 | xargs -r ps -fp 2>/dev/null || echo "  ℹ️  No process running"
	@echo ""
	@echo "gRPC server (port 50051):"
	@lsof -ti:50051 | xargs -r ps -fp 2>/dev/null || echo "  ℹ️  No process running"

# -----------------------------
# 🗄️ Vector Database
# -----------------------------

.PHONY: vdb-demo
vdb-demo:
	@echo "🎬 Running VDB demo..."
	@if [ ! -f ".env" ]; then \
		echo "⚠️  .env file not found. Creating from .env_example..."; \
		cp .env_example .env; \
		echo "⚠️  Please edit .env and set your API_KEYS before running the demo!"; \
		exit 1; \
	fi
	./scripts/demo_vdb.sh

.PHONY: vdb-clean
vdb-clean:
	@echo "🧹 Cleaning VDB data..."
	rm -rf ./vdb-data
	@echo "✅ VDB data cleaned."

# -----------------------------
# 🧪 Testing
# -----------------------------

.PHONY: test
test: deps
	@echo "🧪 Running all tests..."
	PYTHONPATH=. $(VENV_BIN)/python -m pytest tests/ -v

.PHONY: test-unit
test-unit: deps
	@echo "🔬 Running unit tests..."
	PYTHONPATH=. $(VENV_BIN)/python -m pytest tests/unit/ -v

.PHONY: test-integration
test-integration: deps
	@echo "🔗 Running integration tests..."
	PYTHONPATH=. $(VENV_BIN)/python -m pytest tests/integration/ -v

.PHONY: test-coverage
test-coverage: deps
	@echo "📊 Running tests with coverage..."
	PYTHONPATH=. $(VENV_BIN)/python -m pytest tests/ -v --cov=app --cov-report=html --cov-report=term --cov-report=xml

.PHONY: test-watch
test-watch: deps
	@echo "👀 Running tests in watch mode..."
	PYTHONPATH=. $(VENV_BIN)/python -m pytest tests/ -v --tb=short -f

# -----------------------------
# ✨ Code Quality & Formatting
# -----------------------------

.PHONY: lint
lint: deps
	@echo "🔍 Running linters..."
	$(VENV_BIN)/flake8 app/ tests/ --count --statistics
	$(VENV_BIN)/bandit -r app/ -f json

.PHONY: format
format: deps
	@echo "✨ Formatting code..."
	$(VENV_BIN)/black app/ tests/
	$(VENV_BIN)/isort app/ tests/

.PHONY: format-check
format-check: deps
	@echo "🔍 Checking code format..."
	$(VENV_BIN)/black --check app/ tests/
	$(VENV_BIN)/isort --check-only app/ tests/

.PHONY: security
security: deps
	@echo "🔒 Running security checks..."
	$(VENV_BIN)/safety check --output screen || true
	$(VENV_BIN)/bandit -r app/ --skip B104

.PHONY: quality
quality: format-check lint security
	@echo "✅ All quality checks passed!"

# -----------------------------
# � Clean
# -----------------------------

.PHONY: clean
clean:
	@echo "🧹 Cleaning project..."
	rm -rf $(VENV)
	find $(GEN_DIR) -type f -name "embeddings_pb2*.py" -delete
	@echo "✅ Clean complete."

# -----------------------------
# 🧨 Full clean (caches + init files)
# -----------------------------

.PHONY: clean-all
clean-all:
	@echo "🧨 Full cleanup: removing caches and init files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "__init__.py" -delete
	find app/adapters/grpc/generated -type f -name "embeddings_pb2*.py" -delete
	rm -rf $(VENV)
	@echo "✅ All caches and init files removed."