"""Integration tests for REST API."""

import json
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.adapters.rest.fastapi_app import build_fastapi
from app.usecases.generate_embedding import GenerateEmbeddingUC
from app.auth import get_current_user
from tests.conftest import MockEncoder


# Test API keys for integration tests
TEST_API_KEYS = {
    "sk-test-integration-123": "test_user",
    "sk-test-admin-456": "admin"
}
TEST_VALID_API_KEYS = set(TEST_API_KEYS.keys())


def mock_get_current_user(*args, **kwargs):
    """Mock authentication function that always returns test_user."""
    return "test_user"


class TestFastAPIIntegration:
    """Integration tests for FastAPI REST endpoints."""

    @pytest.fixture
    def use_case(self):
        """Create a use case with mock encoder for testing."""
        mock_encoder = MockEncoder()
        return GenerateEmbeddingUC(mock_encoder)

    @pytest.fixture
    def client(self, use_case):
        """Create a test client for the FastAPI app."""
        # Mock the dependency to return a test user without authentication
        def override_auth():
            return "test_user"
        
        app = build_fastapi(use_case)
        app.dependency_overrides[get_current_user] = override_auth
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self):
        """Provide authentication headers for testing."""
        return {"Authorization": "Bearer sk-test-integration-123"}

    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "model_id" in data
        assert "device" in data
        assert "dim" in data
        assert data["status"] == "ok"
        assert isinstance(data["dim"], int)
        assert data["dim"] > 0

    def test_embed_single_text(self, client, auth_headers):
        """Test embedding a single text via REST API."""
        payload = {
            "text": "This is a test sentence for embedding",
            "task_type": "passage",
            "normalize": True,
        }

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "model_id" in data
        assert "dim" in data
        assert "embedding" in data
        assert "requested_by" in data
        assert data["requested_by"] == "test_user"
        assert isinstance(data["embedding"], list)
        assert len(data["embedding"]) == data["dim"]
        assert all(isinstance(x, float) for x in data["embedding"])

    def test_embed_multiple_texts(self, client, auth_headers):
        """Test embedding multiple texts via REST API."""
        payload = {
            "texts": [
                "First test sentence",
                "Second test sentence",
                "Third test sentence",
            ],
            "task_type": "query",
            "normalize": False,
        }

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "model_id" in data
        assert "dim" in data
        assert "embeddings" in data
        assert "requested_by" in data
        assert data["requested_by"] == "test_user"
        assert isinstance(data["embeddings"], list)
        assert len(data["embeddings"]) == 3

        # Check each embedding
        for embedding in data["embeddings"]:
            assert isinstance(embedding, list)
            assert len(embedding) == data["dim"]
            assert all(isinstance(x, float) for x in embedding)

    def test_embed_mixed_input(self, client, auth_headers):
        """Test embedding with both text and texts provided."""
        payload = {
            "text": "Single text",
            "texts": ["Multiple", "Texts", "Here"],
            "task_type": "passage",
        }

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Should process all texts (single + multiple)
        assert "embeddings" in data
        assert "requested_by" in data
        assert len(data["embeddings"]) == 4  # 1 + 3 texts

    def test_embed_no_input(self, client, auth_headers):
        """Test embedding request with no text provided."""
        payload = {"task_type": "passage", "normalize": True}

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data
        assert "Provide 'text' or 'texts'" in error_data["detail"]

    def test_embed_empty_text(self, client, auth_headers):
        """Test embedding request with empty text."""
        payload = {"text": "", "task_type": "passage"}

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data

    def test_embed_empty_texts_list(self, client, auth_headers):
        """Test embedding request with empty texts list."""
        payload = {"texts": [], "task_type": "passage"}

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data

    def test_embed_whitespace_only_texts(self, client, auth_headers):
        """Test embedding request with whitespace-only texts."""
        payload = {
            "text": "   ",
            "texts": ["  ", "\t", "\n"],  # Actual whitespace characters
            "task_type": "passage",
        }

        response = client.post("/embed", json=payload, headers=auth_headers)

        # The implementation strips whitespace, so all texts become empty and it returns 400
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data

    def test_embed_default_parameters(self, client, auth_headers):
        """Test embedding with default parameters."""
        payload = {"text": "Test with defaults"}

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
        assert "requested_by" in data
        assert data["requested_by"] == "test_user"
        # Default task_type is "passage" and normalize is True
        assert isinstance(data["embedding"], list)

    def test_embed_task_type_variations(self, client, auth_headers):
        """Test different task types."""
        for task_type in ["passage", "query"]:
            payload = {"text": f"Test for {task_type}", "task_type": task_type}

            response = client.post("/embed", json=payload, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "embedding" in data
            assert "requested_by" in data

    def test_embed_normalize_variations(self, client, auth_headers):
        """Test different normalization settings."""
        for normalize in [True, False]:
            payload = {
                "text": f"Test for normalize={normalize}",
                "normalize": normalize,
            }

            response = client.post("/embed", json=payload, headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "embedding" in data
            assert "requested_by" in data

    def test_invalid_json_payload(self, client):
        """Test request with invalid JSON payload."""
        response = client.post(
            "/embed", data="invalid json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_missing_content_type(self, client, auth_headers):
        """Test request without proper content type."""
        response = client.post("/embed", data=json.dumps({"text": "test"}), headers=auth_headers)

        # FastAPI handles this gracefully and processes the request
        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
        assert "requested_by" in data

    def test_large_text_input(self, client, auth_headers):
        """Test with large text input."""
        large_text = "A" * 10000  # 10KB of text
        payload = {"text": large_text, "task_type": "passage"}

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
        assert "requested_by" in data

    def test_many_texts_batch(self, client, auth_headers):
        """Test batch processing with many texts."""
        many_texts = [f"Text number {i}" for i in range(50)]
        payload = {"texts": many_texts, "task_type": "passage"}

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "embeddings" in data
        assert "requested_by" in data
        assert len(data["embeddings"]) == 50

    def test_special_characters_in_text(self, client, auth_headers):
        """Test with special characters and unicode."""
        payload = {
            "text": "Special chars: éñüñ, 中文, emoji 🚀, symbols @#$%",
            "task_type": "passage",
        }

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
        assert "requested_by" in data

    # Tests for /embed/chunked endpoint
    def test_embed_chunked_short_text(self, client, auth_headers):
        """Test /embed/chunked with short text."""
        payload = {
            "text": "This is a short text.",
            "task_type": "passage",
            "normalize": True,
        }

        response = client.post("/embed/chunked", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert "model_id" in data
        assert "dim" in data
        assert "embedding" in data
        assert "chunk_count" in data
        assert "aggregation" in data
        assert "chunks" in data
        assert "requested_by" in data
        assert data["requested_by"] == "test_user"
        assert data["chunk_count"] == 1
        assert data["aggregation"] == "mean"
        assert len(data["chunks"]) == 1

    def test_embed_chunked_long_text(self, client, auth_headers):
        """Test /embed/chunked with long text requiring multiple chunks."""
        long_text = "This is a test sentence. " * 100
        payload = {
            "text": long_text,
            "chunk_size": 200,
            "chunk_overlap": 20,
            "task_type": "passage",
            "normalize": True,
        }

        response = client.post("/embed/chunked", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["chunk_count"] > 1
        assert len(data["chunks"]) == data["chunk_count"]
        assert "aggregation" in data
        assert data["aggregation"] == "mean"

        # Verify chunk structure
        for i, chunk in enumerate(data["chunks"]):
            assert "index" in chunk
            assert "text_preview" in chunk
            assert "length" in chunk
            assert "embedding" in chunk
            assert chunk["index"] == i
            assert isinstance(chunk["embedding"], list)
            assert len(chunk["embedding"]) == data["dim"]

    def test_embed_chunked_empty_text(self, client, auth_headers):
        """Test /embed/chunked with empty text."""
        payload = {
            "text": "",
            "task_type": "passage",
        }

        response = client.post("/embed/chunked", json=payload, headers=auth_headers)

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_embed_chunked_whitespace_only(self, client, auth_headers):
        """Test /embed/chunked with whitespace-only text."""
        payload = {
            "text": "   \n\t  ",
            "task_type": "passage",
        }

        response = client.post("/embed/chunked", json=payload, headers=auth_headers)

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_embed_chunked_custom_chunk_params(self, client, auth_headers):
        """Test /embed/chunked with custom chunk_size and chunk_overlap."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four."
        payload = {
            "text": text,
            "chunk_size": 30,
            "chunk_overlap": 5,
            "task_type": "passage",
        }

        response = client.post("/embed/chunked", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "chunk_count" in data
        assert "chunks" in data

    def test_embed_chunked_no_normalization(self, client, auth_headers):
        """Test /embed/chunked with normalize=False."""
        payload = {
            "text": "Test text for chunking without normalization.",
            "normalize": False,
            "task_type": "passage",
        }

        response = client.post("/embed/chunked", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
        assert "chunk_count" in data

    def test_embed_chunked_response_structure(self, client, auth_headers):
        """Test that /embed/chunked returns complete response structure."""
        payload = {
            "text": "Test sentence one. Test sentence two.",
            "chunk_size": 25,
        }

        response = client.post("/embed/chunked", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Check all required fields
        required_fields = ["model_id", "dim", "embedding", "chunk_count", "aggregation", "chunks", "requested_by"]
        for field in required_fields:
            assert field in data

        # Check aggregated embedding
        assert isinstance(data["embedding"], list)
        assert len(data["embedding"]) == data["dim"]

    def test_embed_with_chunking_enabled(self, client, auth_headers):
        """Test /embed endpoint with chunking parameter enabled."""
        long_text = "This is a sentence. " * 50
        payload = {
            "text": long_text,
            "chunking": True,
            "chunk_size": 150,
            "chunk_overlap": 15,
        }

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # When chunking is enabled, response should include chunk metadata
        assert "chunk_count" in data
        assert "aggregation" in data
        assert "chunks" in data
        assert data["chunk_count"] > 1

    def test_embed_with_chunking_disabled(self, client, auth_headers):
        """Test /embed endpoint with chunking parameter disabled."""
        long_text = "This is a sentence. " * 50
        payload = {
            "text": long_text,
            "chunking": False,
        }

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # When chunking is disabled, response should NOT include chunk metadata
        assert "chunk_count" not in data
        assert "aggregation" not in data
        assert "chunks" not in data
        assert "embedding" in data

    def test_embed_chunked_excessive_overlap_validation(self, client, auth_headers):
        """Test that excessive overlap (>50% of chunk_size) is rejected."""
        payload = {
            "text": "Test text for validation",
            "chunk_size": 100,
            "chunk_overlap": 60,  # 60% overlap - should be rejected
        }

        response = client.post("/embed/chunked", json=payload, headers=auth_headers)

        assert response.status_code == 422  # Validation error
        error_detail = response.json()["detail"]
        assert any("50%" in str(err.get("msg", "")) for err in error_detail)

    def test_embed_excessive_overlap_validation(self, client, auth_headers):
        """Test that excessive overlap is rejected in /embed endpoint too."""
        payload = {
            "text": "Test text for validation",
            "chunking": True,
            "chunk_size": 100,
            "chunk_overlap": 55,  # 55% overlap - should be rejected
        }

        response = client.post("/embed", json=payload, headers=auth_headers)

        assert response.status_code == 422  # Validation error
        error_detail = response.json()["detail"]
        assert any("50%" in str(err.get("msg", "")) for err in error_detail)

    # Tests for /embed/chunks endpoint
    def test_embed_chunks_short_text(self, client, auth_headers):
        """Test /embed/chunks with short text (single chunk)."""
        payload = {
            "text": "This is a short text that fits in one chunk.",
            "chunk_size": 1000,
            "chunk_overlap": 100,
        }

        response = client.post("/embed/chunks", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "model_id" in data
        assert "dim" in data
        assert "chunk_count" in data
        assert "chunks" in data
        assert "requested_by" in data

        # Should have 1 chunk
        assert data["chunk_count"] == 1
        assert len(data["chunks"]) == 1

        # Check chunk structure: [text, embedding, chunk_number]
        chunk = data["chunks"][0]
        assert isinstance(chunk, list)
        assert len(chunk) == 3
        
        # Verify fields
        text, embedding, chunk_num = chunk
        assert isinstance(text, str)
        assert len(text) > 0
        assert isinstance(embedding, list)
        assert len(embedding) == data["dim"]
        assert chunk_num == 1  # First chunk is numbered 1

    def test_embed_chunks_long_text(self, client, auth_headers):
        """Test /embed/chunks with long text requiring multiple chunks."""
        long_text = ". ".join([f"This is sentence number {i}" for i in range(100)])
        payload = {
            "text": long_text,
            "chunk_size": 200,
            "chunk_overlap": 50,
        }

        response = client.post("/embed/chunks", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Should have multiple chunks
        assert data["chunk_count"] > 1
        assert len(data["chunks"]) == data["chunk_count"]

        # Verify each chunk structure
        for i, chunk in enumerate(data["chunks"]):
            assert isinstance(chunk, list)
            assert len(chunk) == 3
            
            text, embedding, chunk_num = chunk
            assert isinstance(text, str)
            assert len(text) > 0  # Full text, not preview
            assert isinstance(embedding, list)
            assert len(embedding) == data["dim"]
            assert chunk_num == i + 1  # Chunks numbered from 1

    def test_embed_chunks_full_text_not_preview(self, client, auth_headers):
        """Test that /embed/chunks returns full chunk text, not preview."""
        # Create text with identifiable content in later part of chunk
        text_chunk = "START_MARKER " + "x" * 200 + " END_MARKER"
        payload = {
            "text": text_chunk,
            "chunk_size": 500,
        }

        response = client.post("/embed/chunks", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Get the full text from first chunk
        chunk_text = data["chunks"][0][0]
        
        # Should contain both markers (full text)
        assert "START_MARKER" in chunk_text
        assert "END_MARKER" in chunk_text
        # Should be longer than 100 chars (not a preview)
        assert len(chunk_text) > 100

    def test_embed_chunks_empty_text(self, client, auth_headers):
        """Test /embed/chunks with empty text."""
        payload = {
            "text": "",
        }

        response = client.post("/embed/chunks", json=payload, headers=auth_headers)

        assert response.status_code == 400  # Bad request
        assert "text" in response.json()["detail"].lower()

    def test_embed_chunks_whitespace_only(self, client, auth_headers):
        """Test /embed/chunks with whitespace-only text."""
        payload = {
            "text": "   \n\t  ",
        }

        response = client.post("/embed/chunks", json=payload, headers=auth_headers)

        assert response.status_code == 400  # Bad request

    def test_embed_chunks_custom_parameters(self, client, auth_headers):
        """Test /embed/chunks with custom chunk_size and overlap."""
        long_text = ". ".join([f"Sentence {i}" for i in range(50)])
        payload = {
            "text": long_text,
            "chunk_size": 150,
            "chunk_overlap": 30,
            "task_type": "query",
            "normalize": False,
        }

        response = client.post("/embed/chunks", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Should have multiple chunks with these settings
        assert data["chunk_count"] > 1

    def test_embed_chunks_excessive_overlap_validation(self, client, auth_headers):
        """Test that excessive overlap is rejected in /embed/chunks endpoint."""
        payload = {
            "text": "Test text for validation",
            "chunk_size": 100,
            "chunk_overlap": 51,  # >50% overlap - should be rejected
        }

        response = client.post("/embed/chunks", json=payload, headers=auth_headers)

        assert response.status_code == 422  # Validation error
        error_detail = response.json()["detail"]
        assert any("50%" in str(err.get("msg", "")) for err in error_detail)

    def test_embed_chunks_response_format(self, client, auth_headers):
        """Test the exact format of /embed/chunks response."""
        payload = {
            "text": "First sentence. Second sentence. Third sentence.",
            "chunk_size": 30,
        }

        response = client.post("/embed/chunks", json=payload, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Top-level structure
        assert set(data.keys()) == {"model_id", "dim", "chunk_count", "chunks", "requested_by"}
        
        # NO aggregated embedding in this endpoint
        assert "embedding" not in data
        assert "aggregation" not in data

        # Chunks should be array of [text, embedding, chunk_number]
        for chunk in data["chunks"]:
            assert isinstance(chunk, list)
            assert len(chunk) == 3
            assert isinstance(chunk[0], str)  # text
            assert isinstance(chunk[1], list)  # embedding
            assert isinstance(chunk[2], int)  # chunk_number


