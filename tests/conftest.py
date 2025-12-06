"""Common test fixtures and mock implementations."""

import os
from typing import List
from unittest.mock import Mock
import tempfile
import shutil

import pytest

from app.ports.encoder_port import EncoderPort
from app.adapters.infra.auth_storage import AuthDatabase, UserStorage, APIKeyStorage, ProjectStorage
from app.domain.auth import APIKeyManager

# Mock encoder default values
DEFAULT_MOCK_MODEL_ID = "mock-model"
DEFAULT_MOCK_DEVICE = "cpu"
DEFAULT_MOCK_DIM = 384
LARGE_MOCK_DIM = 768
LARGE_MOCK_MODEL_ID = "large-mock-model"

# Mock embedding generation constants
HASH_MODULO = 100
EMBEDDING_SCALE = 100.0


class MockEncoder:
    """Mock implementation of EncoderPort for testing."""

    def __init__(
        self, model_id: str = DEFAULT_MOCK_MODEL_ID, device: str = DEFAULT_MOCK_DEVICE, dim: int = DEFAULT_MOCK_DIM
    ):
        self._model_id = model_id
        self._device = device
        self._dim = dim

    def encode(
        self, texts: List[str], task_type: str = "passage", normalize: bool = True
    ) -> List[List[float]]:
        """Generate predictable mock embeddings based on text content."""
        embeddings = []
        for i, text in enumerate(texts):
            # Create a simple deterministic embedding based on text hash and index
            hash_value = hash(text) % HASH_MODULO
            embedding = [float(hash_value + j + i) / EMBEDDING_SCALE for j in range(self._dim)]
            embeddings.append(embedding)
        return embeddings

    def dim(self) -> int:
        return self._dim

    def device(self) -> str:
        return self._device

    def model_id(self) -> str:
        return self._model_id


@pytest.fixture
def mock_encoder():
    """Fixture providing a mock encoder instance."""
    return MockEncoder()


@pytest.fixture
def large_mock_encoder():
    """Fixture providing a mock encoder with larger dimension."""
    return MockEncoder(model_id=LARGE_MOCK_MODEL_ID, dim=LARGE_MOCK_DIM)


@pytest.fixture
def sample_texts():
    """Fixture providing sample texts for testing."""
    return [
        "Artificial intelligence is transforming the world",
        "Machine learning algorithms are powerful tools",
        "Natural language processing enables text understanding",
        "Deep learning models can process complex patterns",
    ]


@pytest.fixture
def single_text():
    """Fixture providing a single text sample."""
    return "This is a test document for embedding generation."


@pytest.fixture(scope="function")
def test_auth_db():
    """Fixture providing a test authentication database."""
    # Create temp database file
    db_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
    db_path = db_file.name
    db_file.close()
    
    # Initialize database
    db = AuthDatabase(db_path)
    user_storage = UserStorage(db)
    key_storage = APIKeyStorage(db)
    project_storage = ProjectStorage(db)
    
    # Initialize schema
    db.create_tables()
    
    # Create test users with API keys
    key_manager = APIKeyManager()
    
    # Admin user
    admin_user = user_storage.create_user(
        username="test_admin",
        role="admin",
        email="admin@test.com"
    )
    admin_key = key_manager.generate_key("admin")
    admin_key_hash = key_manager.hash_key(admin_key)
    key_storage.create_api_key(
        user_id=admin_user.id,
        key_id=admin_key,  # Full key as key_id
        key_hash=admin_key_hash,
        label="Test Admin Key"
    )
    
    # Service app user
    service_user = user_storage.create_user(
        username="test_service",
        role="service-app",
        email="service@test.com"
    )
    service_key = key_manager.generate_key("serviceapp")
    service_key_hash = key_manager.hash_key(service_key)
    key_storage.create_api_key(
        user_id=service_user.id,
        key_id=service_key,  # Full key as key_id
        key_hash=service_key_hash,
        label="Test Service Key"
    )
    
    # Monitor user
    monitor_user = user_storage.create_user(
        username="test_monitor",
        role="monitor",
        email="monitor@test.com"
    )
    monitor_key = key_manager.generate_key("monitor")
    monitor_key_hash = key_manager.hash_key(monitor_key)
    key_storage.create_api_key(
        user_id=monitor_user.id,
        key_id=monitor_key,  # Full key as key_id
        key_hash=monitor_key_hash,
        label="Test Monitor Key"
    )
    
    # Return test data
    test_data = {
        "db": db,
        "db_path": db_path,
        "user_storage": user_storage,
        "key_storage": key_storage,
        "project_storage": project_storage,
        "admin": {
            "user": admin_user,
            "key": admin_key,
            "key_hash": admin_key_hash
        },
        "service": {
            "user": service_user,
            "key": service_key,
            "key_hash": service_key_hash
        },
        "monitor": {
            "user": monitor_user,
            "key": monitor_key,
            "key_hash": monitor_key_hash
        }
    }
    
    yield test_data
    
    # Cleanup
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def admin_auth_headers(test_auth_db):
    """Authentication headers for admin user."""
    return {"Authorization": f"Bearer {test_auth_db['admin']['key']}"}


@pytest.fixture
def service_auth_headers(test_auth_db):
    """Authentication headers for service-app user."""
    return {"Authorization": f"Bearer {test_auth_db['service']['key']}"}


@pytest.fixture
def monitor_auth_headers(test_auth_db):
    """Authentication headers for monitor user."""
    return {"Authorization": f"Bearer {test_auth_db['monitor']['key']}"}


@pytest.fixture(autouse=True)
def setup_test_auth(test_auth_db):
    """Setup test authentication for all tests."""
    from app.adapters.rest.auth_middleware import set_test_auth_storage, reset_auth_storage
    from app.adapters.infra.auth_storage import AuditLogStorage
    
    # Create audit storage
    audit_storage = AuditLogStorage(test_auth_db['db'])
    
    # Inject test storage into auth middleware
    set_test_auth_storage(
        db=test_auth_db['db'],
        user_storage=test_auth_db['user_storage'],
        key_storage=test_auth_db['key_storage'],
        audit_storage=audit_storage,
        project_storage=test_auth_db['project_storage']
    )
    
    # Reset VDB routes usage tracking to force reinitialization with test DB
    try:
        from app.adapters.rest import vdb_routes
        vdb_routes._usage_storage = None
        vdb_routes._quota_storage = None
    except ImportError:
        pass  # VDB routes not imported yet
    
    yield
    
    # Cleanup
    reset_auth_storage()
    try:
        from app.adapters.rest import vdb_routes
        vdb_routes._usage_storage = None
        vdb_routes._quota_storage = None
    except ImportError:
        pass
