"""Common test fixtures and mock implementations."""

import os
from typing import List
from unittest.mock import Mock
import tempfile
import shutil

import pytest

from app.ports.encoder_port import EncoderPort

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
