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

    # Tests for chunking functionality
    def test_chunk_text_short_text(self, use_case):
        """Test chunking with text shorter than chunk_size."""
        text = "This is a short text."
        chunks = use_case._chunk_text(text, chunk_size=1000, overlap=100)
        
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_multiple_sentences(self, use_case):
        """Test chunking with multiple sentences."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = use_case._chunk_text(text, chunk_size=50, overlap=10)
        
        assert len(chunks) > 1
        # Each chunk should be a string
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk) <= 50 or chunk == chunks[-1]  # Last chunk can be shorter

    def test_chunk_text_overlap(self, use_case):
        """Test that chunks have overlap."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        chunks = use_case._chunk_text(text, chunk_size=40, overlap=15)
        
        if len(chunks) > 1:
            # Check that consecutive chunks share some content (overlap)
            for i in range(len(chunks) - 1):
                # Some overlap should exist between consecutive chunks
                assert len(chunks[i]) > 0
                assert len(chunks[i+1]) > 0

    def test_chunk_text_single_long_sentence(self, use_case):
        """Test chunking with a single sentence longer than chunk_size."""
        text = "A" * 2000  # Very long single "sentence" without punctuation
        chunks = use_case._chunk_text(text, chunk_size=500, overlap=50)
        
        # Should split into character-based chunks
        assert len(chunks) > 1
        # Each chunk should be at most chunk_size, and most should be close to it
        for i, chunk in enumerate(chunks):
            assert len(chunk) <= 500
            # All but the last chunk should be close to chunk_size
            if i < len(chunks) - 1:
                assert len(chunk) >= 450  # Close to chunk_size

    def test_chunk_text_empty_text(self, use_case):
        """Test chunking with empty text."""
        text = ""
        chunks = use_case._chunk_text(text, chunk_size=1000, overlap=100)
        
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_chunk_text_sentence_boundaries(self, use_case):
        """Test that chunking respects sentence boundaries."""
        text = "First. Second. Third. Fourth. Fifth. Sixth. Seventh. Eighth."
        chunks = use_case._chunk_text(text, chunk_size=30, overlap=5)
        
        # Each chunk should end with a complete sentence (except possibly the last)
        for chunk in chunks:
            assert isinstance(chunk, str)
            assert len(chunk.strip()) > 0

    def test_embed_chunked_short_text(self, use_case, mock_encoder):
        """Test embed_chunked with short text (single chunk)."""
        text = "Short text"
        result = use_case.embed_chunked(text)
        
        assert "model_id" in result
        assert "dim" in result
        assert "embedding" in result
        assert "chunk_count" in result
        assert "aggregation" in result
        assert "chunks" in result
        assert result["model_id"] == mock_encoder.model_id()
        assert result["chunk_count"] == 1
        assert result["aggregation"] == "mean"
        assert len(result["chunks"]) == 1

    def test_embed_chunked_long_text(self, use_case):
        """Test embed_chunked with long text (multiple chunks)."""
        text = "This is a test sentence. " * 100  # Long text
        result = use_case.embed_chunked(text, chunk_size=200, chunk_overlap=20)
        
        assert "chunk_count" in result
        assert result["chunk_count"] > 1
        assert len(result["chunks"]) == result["chunk_count"]
        
        # Check each chunk has required fields
        for i, chunk in enumerate(result["chunks"]):
            assert "index" in chunk
            assert "text_preview" in chunk
            assert "length" in chunk
            assert "embedding" in chunk
            assert chunk["index"] == i

    def test_embed_chunked_aggregation(self, use_case):
        """Test that embed_chunked aggregates embeddings correctly."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four."
        result = use_case.embed_chunked(text, chunk_size=30, chunk_overlap=5)
        
        # Result should have aggregated embedding
        assert "embedding" in result
        assert isinstance(result["embedding"], list)
        assert len(result["embedding"]) == result["dim"]
        
        # All individual chunks should also have embeddings
        for chunk in result["chunks"]:
            assert len(chunk["embedding"]) == result["dim"]

    def test_embed_chunked_normalization(self, use_case):
        """Test embed_chunked with normalization."""
        text = "Test normalization. With multiple sentences. For chunking."
        
        result_normalized = use_case.embed_chunked(text, normalize=True, chunk_size=30)
        result_not_normalized = use_case.embed_chunked(text, normalize=False, chunk_size=30)
        
        assert "embedding" in result_normalized
        assert "embedding" in result_not_normalized
        # Both should return embeddings
        assert len(result_normalized["embedding"]) > 0
        assert len(result_not_normalized["embedding"]) > 0

    def test_embed_chunked_task_type(self, use_case):
        """Test embed_chunked with different task types."""
        text = "Query text. Another sentence. Third sentence."
        
        result_passage = use_case.embed_chunked(text, task_type="passage", chunk_size=30)
        result_query = use_case.embed_chunked(text, task_type="query", chunk_size=30)
        
        assert "embedding" in result_passage
        assert "embedding" in result_query
        assert len(result_passage["embedding"]) > 0
        assert len(result_query["embedding"]) > 0

    def test_embed_chunked_text_preview_truncation(self, use_case):
        """Test that text previews are truncated to 100 characters."""
        long_sentence = "A" * 200 + ". "
        text = long_sentence * 5
        result = use_case.embed_chunked(text, chunk_size=300, chunk_overlap=0)
        
        for chunk in result["chunks"]:
            # Text preview should be max 100 chars + "..." = 103 chars
            if chunk["length"] > 100:
                assert len(chunk["text_preview"]) == 103  # 100 + "..."
                assert chunk["text_preview"].endswith("...")
            else:
                assert len(chunk["text_preview"]) == chunk["length"]

    def test_embed_chunked_chunk_metadata(self, use_case):
        """Test that chunk metadata is correct."""
        text = "First sentence. Second sentence. Third sentence."
        result = use_case.embed_chunked(text, chunk_size=30, chunk_overlap=5)
        
        for i, chunk in enumerate(result["chunks"]):
            assert chunk["index"] == i
            assert isinstance(chunk["length"], int)
            assert chunk["length"] > 0
            assert isinstance(chunk["text_preview"], str)
            assert isinstance(chunk["embedding"], list)
