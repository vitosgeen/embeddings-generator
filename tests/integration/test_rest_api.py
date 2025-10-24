"""Integration tests for REST API."""

import json

import pytest
from fastapi.testclient import TestClient

from app.adapters.rest.fastapi_app import build_fastapi
from app.usecases.generate_embedding import GenerateEmbeddingUC
from tests.conftest import MockEncoder


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
        app = build_fastapi(use_case)
        return TestClient(app)

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

    def test_embed_single_text(self, client):
        """Test embedding a single text via REST API."""
        payload = {
            "text": "This is a test sentence for embedding",
            "task_type": "passage",
            "normalize": True,
        }

        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "model_id" in data
        assert "dim" in data
        assert "embedding" in data
        assert isinstance(data["embedding"], list)
        assert len(data["embedding"]) == data["dim"]
        assert all(isinstance(x, float) for x in data["embedding"])

    def test_embed_multiple_texts(self, client):
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

        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()

        assert "model_id" in data
        assert "dim" in data
        assert "embeddings" in data
        assert isinstance(data["embeddings"], list)
        assert len(data["embeddings"]) == 3

        # Check each embedding
        for embedding in data["embeddings"]:
            assert isinstance(embedding, list)
            assert len(embedding) == data["dim"]
            assert all(isinstance(x, float) for x in embedding)

    def test_embed_mixed_input(self, client):
        """Test embedding with both text and texts provided."""
        payload = {
            "text": "Single text",
            "texts": ["Multiple", "Texts", "Here"],
            "task_type": "passage",
        }

        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Should process all texts (single + multiple)
        assert "embeddings" in data
        assert len(data["embeddings"]) == 4  # 1 + 3 texts

    def test_embed_no_input(self, client):
        """Test embedding request with no text provided."""
        payload = {"task_type": "passage", "normalize": True}

        response = client.post("/embed", json=payload)

        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data
        assert "Provide 'text' or 'texts'" in error_data["detail"]

    def test_embed_empty_text(self, client):
        """Test embedding request with empty text."""
        payload = {"text": "", "task_type": "passage"}

        response = client.post("/embed", json=payload)

        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data

    def test_embed_empty_texts_list(self, client):
        """Test embedding request with empty texts list."""
        payload = {"texts": [], "task_type": "passage"}

        response = client.post("/embed", json=payload)

        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data

    def test_embed_whitespace_only_texts(self, client):
        """Test embedding request with whitespace-only texts."""
        payload = {
            "text": "   ",
            "texts": ["  ", "\t", "\n"],  # Actual whitespace characters
            "task_type": "passage",
        }

        response = client.post("/embed", json=payload)

        # The implementation strips whitespace, so all texts become empty and it returns 400
        assert response.status_code == 400
        error_data = response.json()
        assert "detail" in error_data

    def test_embed_default_parameters(self, client):
        """Test embedding with default parameters."""
        payload = {"text": "Test with defaults"}

        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data

    def test_embed_task_type_variations(self, client):
        """Test different task types."""
        text = "Test text for different task types"

        for task_type in ["passage", "query"]:
            payload = {"text": text, "task_type": task_type}

            response = client.post("/embed", json=payload)
            assert response.status_code == 200

            data = response.json()
            assert "embedding" in data
            assert len(data["embedding"]) > 0

    def test_embed_normalize_variations(self, client):
        """Test with different normalize values."""
        text = "Test text for normalization"

        for normalize in [True, False]:
            payload = {"text": text, "normalize": normalize}

            response = client.post("/embed", json=payload)
            assert response.status_code == 200

            data = response.json()
            assert "embedding" in data

    def test_invalid_json_payload(self, client):
        """Test request with invalid JSON payload."""
        response = client.post(
            "/embed", data="invalid json", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_missing_content_type(self, client):
        """Test request without proper content type."""
        response = client.post("/embed", data=json.dumps({"text": "test"}))

        # FastAPI handles this gracefully and processes the request
        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data

    def test_large_text_input(self, client):
        """Test with large text input."""
        large_text = "A" * 10000  # 10KB of text
        payload = {"text": large_text, "task_type": "passage"}

        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data

    def test_many_texts_batch(self, client):
        """Test batch processing with many texts."""
        many_texts = [f"Text number {i}" for i in range(50)]
        payload = {"texts": many_texts, "task_type": "passage"}

        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "embeddings" in data
        assert len(data["embeddings"]) == 50

    def test_special_characters_in_text(self, client):
        """Test with special characters and unicode."""
        payload = {
            "text": "Special chars: éñüñ, 中文, emoji 🚀, symbols @#$%",
            "task_type": "passage",
        }

        response = client.post("/embed", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
