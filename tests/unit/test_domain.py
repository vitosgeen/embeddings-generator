"""Unit tests for domain models."""

import pytest

from app.domain.embedding import EmbeddingVector


class TestEmbeddingVector:
    """Test cases for EmbeddingVector domain model."""

    def test_create_embedding_vector(self):
        """Test creating an embedding vector with valid values."""
        values = [0.1, 0.2, 0.3, 0.4, 0.5]
        embedding = EmbeddingVector(values)

        assert embedding.values == tuple(values)
        assert embedding.dim == 5

    def test_empty_embedding_vector(self):
        """Test creating an embedding vector with empty values."""
        embedding = EmbeddingVector([])

        assert embedding.values == tuple()
        assert embedding.dim == 0

    def test_single_value_embedding(self):
        """Test creating an embedding vector with a single value."""
        embedding = EmbeddingVector([1.0])

        assert embedding.values == (1.0,)
        assert embedding.dim == 1

    def test_large_dimension_embedding(self):
        """Test creating an embedding vector with many dimensions."""
        values = [i * 0.1 for i in range(1000)]
        embedding = EmbeddingVector(values)

        assert len(embedding.values) == 1000
        assert embedding.dim == 1000
        assert embedding.values[0] == 0.0
        assert embedding.values[999] == 99.9

    def test_negative_values_allowed(self):
        """Test that negative values are allowed in embeddings."""
        values = [-0.5, -0.1, 0.0, 0.1, 0.5]
        embedding = EmbeddingVector(values)

        assert embedding.values == tuple(values)
        assert embedding.dim == 5

    def test_immutable_embedding_vector(self):
        """Test that EmbeddingVector is immutable (frozen dataclass)."""
        embedding = EmbeddingVector([1.0, 2.0, 3.0])

        # Should raise AttributeError when trying to modify
        with pytest.raises(AttributeError):
            embedding.values = (4.0, 5.0, 6.0)

    def test_embedding_vector_equality(self):
        """Test equality comparison of embedding vectors."""
        values1 = [0.1, 0.2, 0.3]
        values2 = [0.1, 0.2, 0.3]
        values3 = [0.1, 0.2, 0.4]

        embedding1 = EmbeddingVector(values1)
        embedding2 = EmbeddingVector(values2)
        embedding3 = EmbeddingVector(values3)

        assert embedding1 == embedding2
        assert embedding1 != embedding3
        assert embedding2 != embedding3

    def test_embedding_vector_hash(self):
        """Test that embedding vectors are hashable."""
        values = [0.1, 0.2, 0.3]
        embedding1 = EmbeddingVector(values)
        embedding2 = EmbeddingVector(values)

        # Should be able to use as dict key
        embedding_dict = {embedding1: "test"}
        assert embedding_dict[embedding2] == "test"
