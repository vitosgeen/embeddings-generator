"""Unit tests for infrastructure adapters."""

from unittest.mock import MagicMock, Mock, patch

import pytest
import torch

from app.adapters.infra.sentence_encoder import SentenceEncoder


class TestSentenceEncoder:
    """Test cases for SentenceEncoder infrastructure adapter."""

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_initialization_with_defaults(self, mock_sentence_transformer):
        """Test SentenceEncoder initialization with default parameters."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        encoder = SentenceEncoder("test-model")

        assert encoder._model_id == "test-model"
        assert encoder._batch_size == 32
        mock_sentence_transformer.assert_called_once_with(
            "test-model", device=encoder._device
        )

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    @patch("torch.cuda.is_available", return_value=True)
    def test_device_selection_cuda_available(
        self, mock_cuda_available, mock_sentence_transformer
    ):
        """Test device selection when CUDA is available."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        encoder = SentenceEncoder("test-model")

        assert encoder._device == "cuda"

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    @patch("torch.cuda.is_available", return_value=False)
    def test_device_selection_cuda_not_available(
        self, mock_cuda_available, mock_sentence_transformer
    ):
        """Test device selection when CUDA is not available."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        encoder = SentenceEncoder("test-model")

        # Should fall back to CPU if MPS is not available
        expected_device = "cpu"  # Assuming MPS is not available in test environment
        assert encoder._device == expected_device

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_initialization_with_custom_device(self, mock_sentence_transformer):
        """Test SentenceEncoder initialization with custom device."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        encoder = SentenceEncoder("test-model", device="cpu", batch_size=16)

        assert encoder._device == "cpu"
        assert encoder._batch_size == 16
        mock_sentence_transformer.assert_called_once_with("test-model", device="cpu")

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_model_id_property(self, mock_sentence_transformer):
        """Test model_id property returns correct value."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        encoder = SentenceEncoder("my-custom-model")

        assert encoder.model_id() == "my-custom-model"

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_device_property(self, mock_sentence_transformer):
        """Test device property returns correct value."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        encoder = SentenceEncoder("test-model", device="cpu")

        assert encoder.device() == "cpu"

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_prefix_addition_passage(self, mock_sentence_transformer):
        """Test prefix addition for passage task type."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        encoder = SentenceEncoder("test-model")

        texts = ["This is a test passage"]
        prefixed = encoder._prefix(texts, "passage")

        assert prefixed[0].startswith("Represent this passage for retrieval: ")
        assert "This is a test passage" in prefixed[0]

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_prefix_addition_query(self, mock_sentence_transformer):
        """Test prefix addition for query task type."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        encoder = SentenceEncoder("test-model")

        texts = ["This is a test query"]
        prefixed = encoder._prefix(texts, "query")

        assert prefixed[0].startswith(
            "Represent this query for retrieving relevant passages: "
        )
        assert "This is a test query" in prefixed[0]

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_prefix_addition_unknown_task(self, mock_sentence_transformer):
        """Test prefix addition for unknown task type defaults to passage."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        encoder = SentenceEncoder("test-model")

        texts = ["This is a test text"]
        prefixed = encoder._prefix(texts, "unknown_task")

        # Should default to passage prefix
        assert prefixed[0].startswith("Represent this passage for retrieval: ")
        assert "This is a test text" in prefixed[0]

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_encode_method(self, mock_sentence_transformer):
        """Test encode method with mocked SentenceTransformer."""
        # Mock the SentenceTransformer model
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        # Mock the encode method to return numpy arrays
        import numpy as np

        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_model.encode.return_value = mock_embeddings

        encoder = SentenceEncoder("test-model")
        texts = ["First text", "Second text"]

        result = encoder.encode(texts, task_type="passage", normalize=True)

        # Check that the model.encode was called with correct parameters
        mock_model.encode.assert_called_once()
        call_args = mock_model.encode.call_args

        # Check that texts were prefixed
        prefixed_texts = call_args[0][0]
        assert len(prefixed_texts) == 2
        assert "Represent this passage for retrieval: First text" in prefixed_texts
        assert "Represent this passage for retrieval: Second text" in prefixed_texts

        # Check call kwargs
        assert call_args[1]["batch_size"] == 32
        assert call_args[1]["convert_to_numpy"] == True
        assert call_args[1]["normalize_embeddings"] == True
        assert call_args[1]["show_progress_bar"] == False

        # Check result format
        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_encode_with_different_batch_size(self, mock_sentence_transformer):
        """Test encode method with custom batch size."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        import numpy as np

        mock_model.encode.return_value = np.array([[0.1, 0.2]])

        encoder = SentenceEncoder("test-model", batch_size=8)
        encoder.encode(["test"], normalize=False)

        call_args = mock_model.encode.call_args
        assert call_args[1]["batch_size"] == 8
        assert call_args[1]["normalize_embeddings"] == False

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_dim_method(self, mock_sentence_transformer):
        """Test dim method returns correct dimension."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        # Mock encode to return a vector with known dimension
        import numpy as np

        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])

        encoder = SentenceEncoder("test-model")
        dimension = encoder.dim()

        assert dimension == 5

        # Verify that encode was called with the probe text
        mock_model.encode.assert_called_once()
        call_args = mock_model.encode.call_args[0][0]
        assert "dim_probe" in call_args[0]

    @patch("app.adapters.infra.sentence_encoder.SentenceTransformer")
    def test_encode_empty_list(self, mock_sentence_transformer):
        """Test encode method with empty text list."""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model

        import numpy as np

        mock_model.encode.return_value = np.array([]).reshape(0, 3)

        encoder = SentenceEncoder("test-model")
        result = encoder.encode([])

        assert result == []
