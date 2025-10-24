"""Unit tests for use cases."""

from unittest.mock import Mock

import pytest

from app.usecases.generate_embedding import GenerateEmbeddingUC
from tests.conftest import MockEncoder


class TestGenerateEmbeddingUC:
    """Test cases for GenerateEmbeddingUC."""

    @pytest.fixture
    def use_case(self, mock_encoder):
        """Create a GenerateEmbeddingUC instance with mock encoder."""
        return GenerateEmbeddingUC(mock_encoder)

    def test_embed_single_text(self, use_case, mock_encoder):
        """Test embedding a single text."""
        text = "Hello world"
        result = use_case.embed(text)

        assert "model_id" in result
        assert "dim" in result
        assert "embedding" in result
        assert result["model_id"] == mock_encoder.model_id()
        assert result["dim"] == len(result["embedding"])
        assert isinstance(result["embedding"], list)
        assert len(result["embedding"]) > 0

    def test_embed_with_task_type(self, use_case):
        """Test embedding with different task types."""
        text = "Query text"

        result_passage = use_case.embed(text, task_type="passage")
        result_query = use_case.embed(text, task_type="query")

        # Both should return valid embeddings
        assert "embedding" in result_passage
        assert "embedding" in result_query
        assert len(result_passage["embedding"]) > 0
        assert len(result_query["embedding"]) > 0

    def test_embed_with_normalize_flag(self, use_case):
        """Test embedding with normalize flag."""
        text = "Test normalization"

        result_normalized = use_case.embed(text, normalize=True)
        result_not_normalized = use_case.embed(text, normalize=False)

        assert "embedding" in result_normalized
        assert "embedding" in result_not_normalized

    def test_embed_batch_multiple_texts(self, use_case, mock_encoder, sample_texts):
        """Test batch embedding of multiple texts."""
        result = use_case.embed_batch(sample_texts)

        assert "model_id" in result
        assert "dim" in result
        assert "items" in result
        assert result["model_id"] == mock_encoder.model_id()
        assert len(result["items"]) == len(sample_texts)

        # Check each item in the batch
        for i, item in enumerate(result["items"]):
            assert "index" in item
            assert "embedding" in item
            assert item["index"] == i
            assert len(item["embedding"]) == result["dim"]

    def test_embed_batch_single_text(self, use_case):
        """Test batch embedding with a single text."""
        texts = ["Single text for batch"]
        result = use_case.embed_batch(texts)

        assert len(result["items"]) == 1
        assert result["items"][0]["index"] == 0
        assert len(result["items"][0]["embedding"]) == result["dim"]

    def test_embed_batch_empty_list(self, use_case):
        """Test batch embedding with empty list."""
        result = use_case.embed_batch([])

        assert "items" in result
        assert result["items"] == []
        assert "model_id" in result
        assert "dim" in result

    def test_embed_batch_with_task_type(self, use_case, sample_texts):
        """Test batch embedding with different task types."""
        result_passage = use_case.embed_batch(sample_texts, task_type="passage")
        result_query = use_case.embed_batch(sample_texts, task_type="query")

        assert len(result_passage["items"]) == len(sample_texts)
        assert len(result_query["items"]) == len(sample_texts)

    def test_health_check(self, use_case, mock_encoder):
        """Test health check functionality."""
        result = use_case.health()

        assert "status" in result
        assert "model_id" in result
        assert "device" in result
        assert "dim" in result
        assert result["status"] == "ok"
        assert result["model_id"] == mock_encoder.model_id()
        assert result["device"] == mock_encoder.device()
        assert result["dim"] > 0

    def test_encoder_error_handling(self):
        """Test handling of encoder errors."""
        # Create a mock encoder that raises an exception
        failing_encoder = Mock()
        failing_encoder.encode.side_effect = Exception("Encoder failed")
        failing_encoder.model_id.return_value = "failing-model"

        use_case = GenerateEmbeddingUC(failing_encoder)

        with pytest.raises(Exception, match="Encoder failed"):
            use_case.embed("test text")

    def test_dimensions_consistency(self, use_case, sample_texts):
        """Test that dimensions are consistent across operations."""
        single_result = use_case.embed(sample_texts[0])
        batch_result = use_case.embed_batch(sample_texts)
        health_result = use_case.health()

        # All dimensions should match
        assert single_result["dim"] == batch_result["dim"]
        assert single_result["dim"] == health_result["dim"]
        assert len(single_result["embedding"]) == single_result["dim"]

        for item in batch_result["items"]:
            assert len(item["embedding"]) == batch_result["dim"]

    def test_model_id_consistency(self, use_case, sample_texts):
        """Test that model_id is consistent across operations."""
        single_result = use_case.embed(sample_texts[0])
        batch_result = use_case.embed_batch(sample_texts)
        health_result = use_case.health()

        # All model_ids should match
        assert single_result["model_id"] == batch_result["model_id"]
        assert single_result["model_id"] == health_result["model_id"]
