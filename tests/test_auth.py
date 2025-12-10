"""Tests for authentication system."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.adapters.rest.fastapi_app import build_fastapi
from app.usecases.generate_embedding import GenerateEmbeddingUC


@pytest.fixture
def mock_uc():
    """Mock use case for testing."""
    uc = MagicMock(spec=GenerateEmbeddingUC)
    
    # Mock the health method
    uc.health.return_value = {
        "status": "ok",
        "model_id": "test-model",
        "device": "cpu",
        "dim": 768,
        "batch_size": 32
    }
    
    # Mock the embed method
    uc.embed.return_value = {
        "model_id": "test-model",
        "dim": 768,
        "embedding": [0.1, 0.2, 0.3]
    }
    
    # Mock the embed_chunked method (used when chunking=true)
    uc.embed_chunked.return_value = {
        "model_id": "test-model",
        "dim": 768,
        "embedding": [0.1, 0.2, 0.3],
        "chunk_count": 1,
        "aggregation": "mean",
        "chunks": [{
            "index": 0,
            "text_preview": "test text",
            "length": 9,
            "embedding": [0.1, 0.2, 0.3]
        }]
    }
    
    # Mock the embed_batch method
    uc.embed_batch.return_value = {
        "model_id": "test-model",
        "dim": 768,
        "items": [{"embedding": [0.1, 0.2, 0.3]}, {"embedding": [0.4, 0.5, 0.6]}]
    }
    
    return uc


@pytest.fixture
def client(mock_uc):
    """Test client with mocked dependencies."""
    app = build_fastapi(mock_uc)
    return TestClient(app)


class TestAuthentication:
    """Test authentication functionality."""
    
    def test_health_endpoint_public(self, client):
        """Health endpoint should be accessible without authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_index_endpoint_public(self, client):
        """Index endpoint should be accessible without authentication."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
    
    def test_embed_endpoint_requires_auth(self, client):
        """Embed endpoint should require authentication."""
        response = client.post(
            "/embed",
            json={"text": "test text"}
        )
        assert response.status_code == 403  # No Authorization header
    
    def test_embed_endpoint_invalid_api_key(self, client):
        """Embed endpoint should reject invalid API keys."""
        response = client.post(
            "/embed",
            headers={"Authorization": "Bearer invalid-key"},
            json={"text": "test text"}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    @patch("app.config.API_KEYS", {"sk-test-123": "test_user"})
    @patch("app.config.VALID_API_KEYS", {"sk-test-123"})
    def test_embed_endpoint_valid_api_key(self, client):
        """Embed endpoint should accept valid API keys."""
        response = client.post(
            "/embed",
            headers={"Authorization": "Bearer sk-test-123"},
            json={"text": "test text"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "test-model"
        assert data["requested_by"] == "test_user"
        assert "embedding" in data
    
    @patch("app.config.API_KEYS", {"sk-admin-123": "admin", "sk-user-456": "user1"})
    @patch("app.config.VALID_API_KEYS", {"sk-admin-123", "sk-user-456"})
    def test_multiple_api_keys(self, client):
        """Test multiple API keys work correctly."""
        # Test admin key
        response = client.post(
            "/embed",
            headers={"Authorization": "Bearer sk-admin-123"},
            json={"text": "admin test"}
        )
        assert response.status_code == 200
        assert response.json()["requested_by"] == "admin"
        
        # Test user key
        response = client.post(
            "/embed",
            headers={"Authorization": "Bearer sk-user-456"},
            json={"text": "user test"}
        )
        assert response.status_code == 200
        assert response.json()["requested_by"] == "user1"
    
    @patch("app.config.API_KEYS", {"sk-batch-123": "batch_user"})
    @patch("app.config.VALID_API_KEYS", {"sk-batch-123"})
    def test_batch_embedding_authentication(self, client):
        """Test batch embedding with authentication."""
        response = client.post(
            "/embed",
            headers={"Authorization": "Bearer sk-batch-123"},
            json={
                "texts": ["text1", "text2"],
                "task_type": "passage",
                "normalize": True
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_id"] == "test-model"
        assert data["requested_by"] == "batch_user"
        assert len(data["embeddings"]) == 2
    
    def test_malformed_authorization_header(self, client):
        """Test malformed authorization headers."""
        # Missing Bearer prefix
        response = client.post(
            "/embed",
            headers={"Authorization": "sk-test-123"},
            json={"text": "test"}
        )
        assert response.status_code == 403
        
        # Empty Bearer token - FastAPI HTTPBearer returns 403 for malformed headers
        response = client.post(
            "/embed",
            headers={"Authorization": "Bearer "},
            json={"text": "test"}
        )
        assert response.status_code == 403


class TestAuthenticationConfiguration:
    """Test authentication configuration parsing."""
    
    @patch.dict("os.environ", {"API_KEYS": "admin:sk-admin-123,user1:sk-user-456"})
    def test_parse_api_keys_from_env(self):
        """Test parsing API keys from environment variable."""
        from app.config import _parse_api_keys
        
        api_keys = _parse_api_keys()
        expected = {
            "sk-admin-123": "admin",
            "sk-user-456": "user1"
        }
        assert api_keys == expected
    
    @patch.dict("os.environ", {"API_KEYS": ""})
    def test_empty_api_keys_env(self):
        """Test empty API_KEYS environment variable."""
        from app.config import _parse_api_keys
        
        api_keys = _parse_api_keys()
        assert api_keys == {}
    
    @patch.dict("os.environ", {"API_KEYS": "malformed,admin:sk-123,invalid"})
    def test_malformed_api_keys_env(self):
        """Test malformed API_KEYS environment variable."""
        from app.config import _parse_api_keys
        
        api_keys = _parse_api_keys()
        # Should only parse valid entries
        assert api_keys == {"sk-123": "admin"}