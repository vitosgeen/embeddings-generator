# 🧪 Test Suite Documentation

This document provides an overview of the comprehensive test suite for the Embeddings Service.

## 📊 Test Coverage Summary

- **Total Tests**: 61 tests
- **Coverage**: 86.07% (exceeds 80% requirement)
- **Test Types**: Unit tests (32) + Integration tests (29)

## 🏗️ Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Common fixtures and mock implementations
├── unit/                       # Unit tests (32 tests)
│   ├── test_domain.py         # Domain model tests
│   ├── test_infrastructure.py # Infrastructure adapter tests  
│   └── test_usecases.py       # Use case business logic tests
└── integration/               # Integration tests (29 tests)
    ├── test_grpc_api.py       # gRPC service integration tests
    └── test_rest_api.py       # REST API integration tests
```

## 🎯 Test Categories

### Unit Tests (32 tests)

#### Domain Layer Tests (`test_domain.py`)
- ✅ **EmbeddingVector model** (8 tests)
  - Creation with various data types
  - Immutability (frozen dataclass)
  - Hashability for use as dict keys
  - Equality comparison
  - Edge cases (empty, large dimensions)

#### Infrastructure Layer Tests (`test_infrastructure.py`)
- ✅ **SentenceEncoder adapter** (11 tests)
  - Initialization with different configurations
  - Device selection (CUDA, CPU, MPS)
  - Text preprocessing and prefixes
  - Mocked SentenceTransformer integration
  - Batch processing and encoding
  - Error handling scenarios

#### Use Case Layer Tests (`test_usecases.py`)
- ✅ **GenerateEmbeddingUC business logic** (13 tests)
  - Single text embedding
  - Batch text embedding
  - Empty batch handling
  - Different task types (passage, query)
  - Normalization options
  - Health checks
  - Error propagation
  - Data consistency across operations

### Integration Tests (29 tests)

#### REST API Integration (`test_rest_api.py`)
- ✅ **FastAPI endpoints** (16 tests)
  - `/health` endpoint functionality
  - `/embed` POST endpoint variations
  - Input validation and error handling
  - Edge cases (empty, whitespace, special chars)
  - Large text processing
  - Batch processing
  - Content-type handling
  - JSON validation

#### gRPC API Integration (`test_grpc_api.py`)
- ✅ **gRPC service methods** (13 tests)
  - `Embed` single text method
  - `EmbedBatch` multiple texts method
  - `Health` check method
  - Protocol buffer message handling
  - Default parameter behavior
  - Large payload processing
  - Unicode and special characters
  - Cross-method consistency

## 🔧 Test Infrastructure

### Mock Implementation (`conftest.py`)
- **MockEncoder**: Deterministic encoder for predictable test results
- **Fixtures**: Reusable test data and configurations
- **Sample Data**: Various text samples for comprehensive testing

### Test Configuration (`pyproject.toml`)
- **Async Mode**: Automatic async test detection
- **Markers**: Categorization of test types
- **Coverage**: Source tracking and reporting
- **Filtering**: Warning suppression for cleaner output

## 🚀 Running Tests

### Basic Test Commands
```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests  
make test-integration

# Run with coverage reporting
make test-coverage

# Run tests in watch mode (auto-rerun on changes)
make test-watch
```

### Advanced pytest Commands
```bash
# Run specific test file
pytest tests/unit/test_domain.py -v

# Run specific test class
pytest tests/unit/test_domain.py::TestEmbeddingVector -v

# Run specific test method
pytest tests/unit/test_domain.py::TestEmbeddingVector::test_create_embedding_vector -v

# Run tests matching pattern
pytest -k "embed_single" -v

# Run with coverage and generate HTML report
pytest --cov=app --cov-report=html
```

## 📈 Coverage Details

### Well-Covered Areas (90-100%)
- ✅ Domain models (`EmbeddingVector`)
- ✅ Use cases (`GenerateEmbeddingUC`) 
- ✅ REST API (`fastapi_app.py`)
- ✅ Infrastructure (`SentenceEncoder`)
- ✅ Ports/Interfaces

### Areas with Lower Coverage
- ⚠️ `app/bootstrap.py` (0% - dependency injection setup)
- ⚠️ `app/config.py` (0% - configuration constants)
- ⚠️ `app/adapters/grpc/server.py` (80% - some async server setup code)

> **Note**: The uncovered areas are primarily initialization and configuration code that doesn't contain business logic.

## 🧪 Test Strategy

### Unit Test Philosophy
- **Isolation**: Each unit test focuses on a single component
- **Mocking**: External dependencies are mocked for predictable behavior
- **Edge Cases**: Comprehensive testing of boundary conditions
- **Fast Execution**: Unit tests run quickly without external dependencies

### Integration Test Philosophy  
- **Real Interactions**: Tests actual API endpoints and protocols
- **End-to-End Flows**: Complete request/response cycles
- **Error Scenarios**: Network-level error handling
- **Protocol Compliance**: Proper HTTP and gRPC behavior

### Test Data Strategy
- **Deterministic**: Mock encoder produces predictable embeddings
- **Varied**: Different text types, lengths, and encodings
- **Edge Cases**: Empty inputs, whitespace, special characters
- **Performance**: Large batches and long texts

## 🔍 Quality Assurance

### Automated Checks
- ✅ **Linting**: Code style and quality checks
- ✅ **Type Hints**: Static type checking with mypy-compatible annotations  
- ✅ **Coverage**: Minimum 80% coverage requirement (currently 86.07%)
- ✅ **CI/CD Ready**: Tests designed for automated pipeline integration

### Best Practices Applied
- **AAA Pattern**: Arrange, Act, Assert test structure
- **Descriptive Names**: Clear test method and class names
- **Single Responsibility**: One assertion per test concept
- **Fixture Reuse**: DRY principle with shared test data
- **Async Support**: Proper async/await testing patterns

## 🚦 Continuous Integration

The test suite is designed to integrate with CI/CD pipelines:

```yaml
# Example GitHub Actions usage
- name: Run Tests
  run: |
    make deps
    make test-coverage
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

## 📝 Adding New Tests

### For New Features
1. **Start with failing tests** (TDD approach)
2. **Write unit tests first** for business logic
3. **Add integration tests** for API endpoints
4. **Update fixtures** if needed for new test data
5. **Verify coverage** meets requirements

### Test Naming Conventions
- **Classes**: `TestComponentName`
- **Methods**: `test_specific_behavior_description`
- **Fixtures**: `descriptive_name` (no test_ prefix)

### Example Test Structure
```python
class TestNewFeature:
    """Test cases for new feature functionality."""
    
    @pytest.fixture
    def sample_data(self):
        """Provide test data for new feature."""
        return {"key": "value"}
    
    def test_feature_with_valid_input(self, sample_data):
        """Test new feature with valid input data."""
        # Arrange
        setup_code()
        
        # Act  
        result = feature_function(sample_data)
        
        # Assert
        assert result == expected_value
```

This comprehensive test suite ensures the reliability, maintainability, and robustness of the Embeddings Service across all its components and interfaces.