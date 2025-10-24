# =============================
# Embeddings Service Makefile
# =============================

PYTHON := python3
VENV := .venv
VENV_BIN := $(VENV)/bin
PROTO_DIR := proto
GEN_DIR := proto
MAIN := main.py

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
# � Testing
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