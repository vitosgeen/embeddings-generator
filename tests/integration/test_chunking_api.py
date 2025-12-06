"""Integration tests for text chunking API endpoints."""
import pytest
import requests


@pytest.fixture
def api_url():
    """Base API URL."""
    return "http://localhost:8000"


@pytest.fixture
def api_key():
    """API key for authentication."""
    return "sk-admin-m1YHp13elEvafGYLT27H0gmD"


@pytest.fixture
def headers(api_key):
    """Request headers with authentication."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


class TestEmbedEndpointChunking:
    """Test /embed endpoint with chunking features."""

    def test_short_text_no_chunking(self, api_url, headers):
        """Short text should not trigger chunking."""
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": "This is a short test text.",
                "task_type": "passage",
                "normalize": True,
                "auto_chunk": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["dim"] == 768
        assert "embedding" in data
        assert data.get("was_chunked") is False

    def test_long_text_without_chunking_shows_warning(self, api_url, headers):
        """Long text without auto_chunk should show truncation warning."""
        long_text = "This is a test sentence. " * 200  # ~5000 chars
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "task_type": "passage",
                "normalize": True,
                "auto_chunk": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["truncated"] is True
        assert "warning" in data
        assert "exceeds model limit" in data["warning"]

    def test_long_text_with_auto_chunking(self, api_url, headers):
        """Long text with auto_chunk should be split and combined."""
        long_text = "Machine learning is amazing. " * 200  # ~5800 chars
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "task_type": "passage",
                "normalize": True,
                "auto_chunk": True,
                "chunk_size": 2000,
                "chunk_overlap": 200,
                "combine_method": "average"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["was_chunked"] is True
        assert data["num_chunks"] > 1
        assert "chunk_sizes" in data
        assert data["combine_method"] == "average"
        assert data["dim"] == 768
        assert len(data["embedding"]) == 768
        
        # Verify all chunks were processed
        total_chars = sum(data["chunk_sizes"])
        assert total_chars >= len(long_text)  # Includes overlaps

    def test_very_long_text_multiple_chunks(self, api_url, headers):
        """Very long text should create many chunks."""
        very_long_text = "Artificial intelligence technology. " * 300  # ~10,800 chars
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": very_long_text,
                "task_type": "passage",
                "normalize": True,
                "auto_chunk": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["was_chunked"] is True
        assert data["num_chunks"] >= 5  # Should create multiple chunks
        assert len(data["chunk_sizes"]) == data["num_chunks"]

    def test_combine_method_average(self, api_url, headers):
        """Test average combine method."""
        long_text = "Test text for averaging. " * 150
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "auto_chunk": True,
                "combine_method": "average"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["combine_method"] == "average"

    def test_combine_method_weighted(self, api_url, headers):
        """Test weighted combine method (favors first chunks)."""
        long_text = "First chunk is most important. " * 150
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "auto_chunk": True,
                "combine_method": "weighted"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["combine_method"] == "weighted"

    def test_combine_method_max(self, api_url, headers):
        """Test max combine method (element-wise maximum)."""
        long_text = "Maximum values across chunks. " * 150
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "auto_chunk": True,
                "combine_method": "max"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["combine_method"] == "max"

    def test_combine_method_first(self, api_url, headers):
        """Test first combine method (only use first chunk)."""
        long_text = "Only first chunk matters. " * 150
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "auto_chunk": True,
                "combine_method": "first"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["combine_method"] == "first"

    def test_return_individual_chunks(self, api_url, headers):
        """Test returning individual chunk embeddings."""
        long_text = "Get individual chunk embeddings. " * 100
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "auto_chunk": True,
                "return_chunks": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["was_chunked"] is True
        assert "chunk_embeddings" in data
        assert len(data["chunk_embeddings"]) == data["num_chunks"]
        
        # Each chunk embedding should be an array with correct dimension
        for chunk_emb in data["chunk_embeddings"]:
            assert isinstance(chunk_emb, list)
            assert len(chunk_emb) == 768
        
        # Individual chunk texts should also be returned
        assert "chunks" in data
        assert len(data["chunks"]) == data["num_chunks"]

    def test_custom_chunk_size(self, api_url, headers):
        """Test custom chunk size parameter."""
        long_text = "Custom chunk size test. " * 200
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "auto_chunk": True,
                "chunk_size": 1500,
                "chunk_overlap": 150
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # With larger chunk size, should have fewer chunks
        assert data["was_chunked"] is True
        for size in data["chunk_sizes"]:
            assert size <= 1650  # chunk_size + buffer

    def test_zero_overlap(self, api_url, headers):
        """Test chunking with zero overlap."""
        long_text = "No overlap between chunks. " * 150
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "auto_chunk": True,
                "chunk_overlap": 0
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["was_chunked"] is True


class TestEmbedCheckEndpoint:
    """Test /embed/check endpoint for preview."""

    def test_check_short_text(self, api_url, headers):
        """Check endpoint with short text."""
        response = requests.post(
            f"{api_url}/embed/check",
            headers=headers,
            json={
                "text": "Short text for checking.",
                "chunk_size": 2000,
                "chunk_overlap": 200
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["would_be_chunked"] is False
        assert data["text_length"] < 2000

    def test_check_long_text(self, api_url, headers):
        """Check endpoint with long text."""
        long_text = "Preview chunking behavior. " * 150
        
        response = requests.post(
            f"{api_url}/embed/check",
            headers=headers,
            json={
                "text": long_text,
                "chunk_size": 2000,
                "chunk_overlap": 200
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["would_be_chunked"] is True
        assert data["num_chunks"] > 1
        assert "chunk_sizes" in data
        assert len(data["chunk_sizes"]) == data["num_chunks"]

    def test_check_matches_actual_chunking(self, api_url, headers):
        """Check preview should match actual chunking."""
        test_text = "Testing preview accuracy. " * 100
        
        # Get preview
        check_response = requests.post(
            f"{api_url}/embed/check",
            headers=headers,
            json={
                "text": test_text,
                "chunk_size": 1000,
                "chunk_overlap": 100
            }
        )
        check_data = check_response.json()
        
        # Get actual embedding
        embed_response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": test_text,
                "auto_chunk": True,
                "chunk_size": 1000,
                "chunk_overlap": 100
            }
        )
        embed_data = embed_response.json()
        
        # Preview should match actual
        assert check_data["would_be_chunked"] == embed_data["was_chunked"]
        if check_data["would_be_chunked"]:
            assert check_data["num_chunks"] == embed_data["num_chunks"]


class TestChunkingEdgeCases:
    """Test edge cases for chunking."""

    def test_empty_text(self, api_url, headers):
        """Empty text should be handled gracefully."""
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": "",
                "auto_chunk": True
            }
        )
        
        # Should either succeed with empty result or return appropriate error
        assert response.status_code in [200, 400, 422]

    def test_unicode_text_chunking(self, api_url, headers):
        """Unicode text should be chunked correctly."""
        unicode_text = "Hello 世界! مرحبا! Привет! " * 100
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": unicode_text,
                "auto_chunk": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["dim"] == 768

    def test_text_with_newlines(self, api_url, headers):
        """Text with newlines should be handled."""
        text_with_newlines = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3.\n" * 100
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": text_with_newlines,
                "auto_chunk": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["dim"] == 768

    def test_exactly_at_limit(self, api_url, headers):
        """Text exactly at token limit should be handled."""
        # Create text of exactly ~2048 chars (512 tokens)
        text = "word " * 410  # ~2050 chars
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": text,
                "auto_chunk": False
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["dim"] == 768

    def test_invalid_combine_method(self, api_url, headers):
        """Invalid combine method should return 500 error."""
        long_text = "Test invalid method. " * 150
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": long_text,
                "auto_chunk": True,
                "combine_method": "invalid_method"
            }
        )
        
        # Should return error for invalid method
        assert response.status_code == 500


class TestChunkingPerformance:
    """Test performance-related aspects of chunking."""

    def test_very_large_text(self, api_url, headers):
        """Test with very large text (>50KB)."""
        # Create ~50KB of text
        large_text = "Performance test with large text. " * 1500  # ~52KB
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": large_text,
                "auto_chunk": True,
                "combine_method": "weighted"
            },
            timeout=30  # Give it more time
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["was_chunked"] is True
        assert data["num_chunks"] >= 10  # Should have many chunks
        assert data["dim"] == 768

    def test_chunk_count_reasonable(self, api_url, headers):
        """Chunk count should be reasonable for text size."""
        text_10k = "Test. " * 1700  # ~10,200 chars
        
        response = requests.post(
            f"{api_url}/embed",
            headers=headers,
            json={
                "text": text_10k,
                "auto_chunk": True,
                "chunk_size": 2000
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have roughly 5-6 chunks for 10K chars with 2K chunk size
        assert 4 <= data["num_chunks"] <= 8
