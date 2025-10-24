"""Common test fixtures and mock implementations."""

from typing import List
from unittest.mock import Mock

import pytest

from app.ports.encoder_port import EncoderPort


class MockEncoder:
    """Mock implementation of EncoderPort for testing."""

    def __init__(
        self, model_id: str = "mock-model", device: str = "cpu", dim: int = 384
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
            hash_value = hash(text) % 100
            embedding = [float(hash_value + j + i) / 100.0 for j in range(self._dim)]
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
    return MockEncoder(model_id="large-mock-model", dim=768)


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
