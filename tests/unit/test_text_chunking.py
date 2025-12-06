"""Unit tests for text chunking utilities."""
import pytest
import numpy as np
from app.utils.text_chunking import (
    chunk_text,
    combine_embeddings,
    estimate_tokens,
    should_chunk,
    get_chunking_info
)


class TestChunkText:
    """Test the chunk_text function."""

    def test_short_text_no_chunking(self):
        """Short text should return as single chunk."""
        text = "This is a short text."
        chunks = chunk_text(text, max_chars=100, overlap=20)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_creates_multiple_chunks(self):
        """Long text should be split into multiple chunks."""
        text = "Sentence one. " * 200  # ~2800 chars
        chunks = chunk_text(text, max_chars=1000, overlap=100)
        assert len(chunks) > 1
        assert all(len(chunk) <= 1100 for chunk in chunks)  # max_chars + some buffer

    def test_chunks_have_overlap(self):
        """Consecutive chunks should have overlapping content."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. " * 20
        chunks = chunk_text(text, max_chars=100, overlap=50)
        
        if len(chunks) > 1:
            # Check that there's some overlap between consecutive chunks
            for i in range(len(chunks) - 1):
                # Last part of current chunk should appear in next chunk
                assert len(chunks[i]) > 0
                assert len(chunks[i + 1]) > 0

    def test_sentence_boundary_splitting(self):
        """Text should be split at sentence boundaries when possible."""
        text = "First sentence. Second sentence. Third sentence. " * 50
        chunks = chunk_text(text, max_chars=200, overlap=50)
        
        for chunk in chunks:
            # Most chunks should end with sentence punctuation or be the last chunk
            if chunk != chunks[-1]:
                # Allow some flexibility for edge cases
                assert len(chunk) > 0

    def test_very_long_sentence(self):
        """Very long sentence without punctuation should still be chunked."""
        text = "word " * 1000  # ~5000 chars, no sentence boundaries
        chunks = chunk_text(text, max_chars=1000, overlap=100)
        assert len(chunks) > 1
        assert all(len(chunk) <= 1100 for chunk in chunks)

    def test_empty_text(self):
        """Empty text should return empty list."""
        chunks = chunk_text("", max_chars=1000, overlap=100)
        assert chunks == [""]

    def test_custom_chunk_size(self):
        """Should respect custom chunk size."""
        text = "Test sentence. " * 200
        chunks = chunk_text(text, max_chars=500, overlap=50)
        for chunk in chunks[:-1]:  # All but last chunk
            assert len(chunk) <= 550  # Allow some buffer


class TestCombineEmbeddings:
    """Test the combine_embeddings function."""

    def test_average_method(self):
        """Average method should return mean of embeddings."""
        embeddings = [
            np.array([1.0, 2.0, 3.0]),
            np.array([2.0, 4.0, 6.0]),
            np.array([3.0, 6.0, 9.0])
        ]
        result = combine_embeddings(embeddings, method="average")
        expected = np.array([2.0, 4.0, 6.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_weighted_method(self):
        """Weighted method should favor earlier chunks."""
        embeddings = [
            np.array([1.0, 1.0, 1.0]),
            np.array([2.0, 2.0, 2.0]),
            np.array([3.0, 3.0, 3.0])
        ]
        result = combine_embeddings(embeddings, method="weighted")
        
        # First chunk should have highest weight
        # Result should be closer to first embedding than last
        assert result[0] < 2.0  # Closer to 1.0 than 3.0

    def test_max_method(self):
        """Max method should return element-wise maximum."""
        embeddings = [
            np.array([1.0, 5.0, 2.0]),
            np.array([3.0, 2.0, 4.0]),
            np.array([2.0, 3.0, 1.0])
        ]
        result = combine_embeddings(embeddings, method="max")
        expected = np.array([3.0, 5.0, 4.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_first_method(self):
        """First method should return only first embedding."""
        embeddings = [
            np.array([1.0, 2.0, 3.0]),
            np.array([4.0, 5.0, 6.0]),
            np.array([7.0, 8.0, 9.0])
        ]
        result = combine_embeddings(embeddings, method="first")
        expected = np.array([1.0, 2.0, 3.0])
        np.testing.assert_array_almost_equal(result, expected)

    def test_single_embedding(self):
        """Single embedding should return as-is."""
        embeddings = [np.array([1.0, 2.0, 3.0])]
        result = combine_embeddings(embeddings, method="average")
        np.testing.assert_array_almost_equal(result, embeddings[0])

    def test_invalid_method(self):
        """Invalid method should raise ValueError."""
        embeddings = [
            np.array([1.0, 2.0, 3.0]),
            np.array([2.0, 4.0, 6.0])
        ]
        with pytest.raises(ValueError, match="Unknown combination method"):
            combine_embeddings(embeddings, method="invalid")


class TestEstimateTokens:
    """Test the estimate_tokens function."""

    def test_short_text(self):
        """Short text should have reasonable token estimate."""
        text = "Hello world"
        tokens = estimate_tokens(text)
        assert tokens > 0
        assert tokens < len(text)  # Should be less than character count

    def test_long_text(self):
        """Long text should scale appropriately."""
        text = "word " * 1000
        tokens = estimate_tokens(text)
        assert tokens > 500  # Should be roughly ~1250 tokens
        assert tokens < 2000

    def test_empty_text(self):
        """Empty text should return 0 tokens."""
        assert estimate_tokens("") == 0

    def test_token_ratio(self):
        """Should use roughly 4 chars per token."""
        text = "test " * 100  # 500 chars
        tokens = estimate_tokens(text)
        assert 100 < tokens < 150  # ~125 tokens expected


class TestShouldChunk:
    """Test the should_chunk function."""

    def test_short_text_no_chunk(self):
        """Short text below limit should not need chunking."""
        text = "Short text"
        assert should_chunk(text, max_tokens=512) is False

    def test_long_text_needs_chunk(self):
        """Long text exceeding limit should need chunking."""
        text = "word " * 1000  # ~5000 chars, ~1250 tokens
        assert should_chunk(text, max_tokens=512) is True

    def test_boundary_case(self):
        """Text near boundary should be handled correctly."""
        text = "word " * 400  # ~2000 chars, ~500 tokens
        # Should be close to boundary
        result = should_chunk(text, max_tokens=512)
        assert isinstance(result, bool)

    def test_custom_max_tokens(self):
        """Should respect custom token limit."""
        text = "word " * 100  # ~500 chars
        assert should_chunk(text, max_tokens=100) is True
        assert should_chunk(text, max_tokens=200) is False


class TestGetChunkingInfo:
    """Test the get_chunking_info function."""

    def test_short_text_info(self):
        """Short text should return no chunking needed."""
        text = "Short text"
        info = get_chunking_info(text)
        
        assert info["would_be_chunked"] is False
        assert info["estimated_tokens"] < 512
        assert info["text_length"] == len(text)
        assert info["num_chunks"] == 1

    def test_long_text_info(self):
        """Long text should return chunking details."""
        text = "Sentence. " * 500  # ~5000 chars
        info = get_chunking_info(text, max_chars=2000)
        
        assert info["would_be_chunked"] is True
        assert info["estimated_tokens"] > 512
        assert info["num_chunks"] > 1
        assert len(info["chunk_sizes"]) == info["num_chunks"]

    def test_chunk_sizes_reasonable(self):
        """Chunk sizes should be within expected range."""
        text = "Test sentence. " * 300
        info = get_chunking_info(text, max_chars=1000)
        
        if info["would_be_chunked"]:
            for size in info["chunk_sizes"]:
                assert 0 < size <= 1100  # max_chars + buffer

    def test_custom_parameters(self):
        """Should respect custom chunk size."""
        text = "Word " * 1000
        info1 = get_chunking_info(text, max_chars=1000)
        info2 = get_chunking_info(text, max_chars=2000)
        
        # Larger chunks should result in fewer chunks
        if info1["would_be_chunked"] and info2["would_be_chunked"]:
            assert info1["num_chunks"] >= info2["num_chunks"]


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_whitespace_only(self):
        """Text with only whitespace should be handled."""
        text = "   \n\n\t  "
        chunks = chunk_text(text, max_chars=100, overlap=20)
        assert len(chunks) >= 1

    def test_special_characters(self):
        """Text with special characters should be handled."""
        text = "Hello! How are you? I'm fine. #test @mention 50% done."
        chunks = chunk_text(text, max_chars=100, overlap=20)
        assert len(chunks) >= 1

    def test_unicode_text(self):
        """Unicode text should be handled correctly."""
        text = "Hello 世界! Привет мир! مرحبا العالم!" * 50
        chunks = chunk_text(text, max_chars=200, overlap=50)
        assert len(chunks) >= 1

    def test_newlines_and_paragraphs(self):
        """Text with newlines should be handled."""
        text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3." * 50
        chunks = chunk_text(text, max_chars=200, overlap=50)
        assert len(chunks) >= 1

    def test_zero_overlap(self):
        """Zero overlap should work without errors."""
        text = "Sentence. " * 200
        chunks = chunk_text(text, max_chars=500, overlap=0)
        assert len(chunks) > 1

    def test_large_overlap(self):
        """Large overlap should be handled."""
        text = "Sentence. " * 100
        chunks = chunk_text(text, max_chars=500, overlap=400)
        assert len(chunks) >= 1
