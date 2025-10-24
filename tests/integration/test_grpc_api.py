"""Integration tests for gRPC API."""

import asyncio
from unittest.mock import Mock

import grpc
import pytest
from grpc import aio
from grpc_testing import server_from_dictionary, strict_real_time

from app.adapters.grpc.server import EmbeddingsService
from app.usecases.generate_embedding import GenerateEmbeddingUC
from proto import embeddings_pb2 as pb
from proto import embeddings_pb2_grpc as pb_grpc
from tests.conftest import MockEncoder


class TestGrpcIntegration:
    """Integration tests for gRPC service."""

    @pytest.fixture
    def use_case(self):
        """Create a use case with mock encoder for testing."""
        mock_encoder = MockEncoder()
        return GenerateEmbeddingUC(mock_encoder)

    @pytest.fixture
    def grpc_service(self, use_case):
        """Create a gRPC service instance for testing."""
        return EmbeddingsService(use_case)

    @pytest.fixture
    def grpc_server(self, grpc_service):
        """Create a test gRPC server."""
        # Create a test server using grpc_testing
        services = {pb.DESCRIPTOR.services_by_name["EmbeddingsService"]: grpc_service}
        return server_from_dictionary(services, strict_real_time())

    @pytest.mark.asyncio
    async def test_embed_single_text(self, grpc_service):
        """Test embedding a single text via gRPC."""
        request = pb.EmbedRequest(
            text="This is a test sentence for gRPC embedding",
            task_type="passage",
            normalize=True,
        )

        context = Mock()
        response = await grpc_service.Embed(request, context)

        assert isinstance(response, pb.EmbedResponse)
        assert response.model_id == "mock-model"
        assert response.dim > 0
        assert len(response.embedding) == response.dim
        assert all(isinstance(x, float) for x in response.embedding)

    @pytest.mark.asyncio
    async def test_embed_batch_multiple_texts(self, grpc_service):
        """Test batch embedding via gRPC."""
        texts = [
            "First test sentence for gRPC",
            "Second test sentence for gRPC",
            "Third test sentence for gRPC",
        ]

        request = pb.EmbedBatchRequest(texts=texts, task_type="query", normalize=False)

        context = Mock()
        response = await grpc_service.EmbedBatch(request, context)

        assert isinstance(response, pb.EmbedBatchResponse)
        assert response.model_id == "mock-model"
        assert response.dim > 0
        assert len(response.items) == 3

        for i, item in enumerate(response.items):
            assert item.index == i
            assert len(item.embedding) == response.dim
            assert all(isinstance(x, float) for x in item.embedding)

    @pytest.mark.asyncio
    async def test_embed_batch_single_text(self, grpc_service):
        """Test batch embedding with single text via gRPC."""
        request = pb.EmbedBatchRequest(
            texts=["Single text for batch"], task_type="passage", normalize=True
        )

        context = Mock()
        response = await grpc_service.EmbedBatch(request, context)

        assert len(response.items) == 1
        assert response.items[0].index == 0
        assert len(response.items[0].embedding) == response.dim

    @pytest.mark.asyncio
    async def test_embed_batch_empty_list(self, grpc_service):
        """Test batch embedding with empty list via gRPC."""
        request = pb.EmbedBatchRequest(texts=[], task_type="passage", normalize=True)

        context = Mock()
        response = await grpc_service.EmbedBatch(request, context)

        assert len(response.items) == 0
        assert response.model_id == "mock-model"
        assert response.dim > 0

    @pytest.mark.asyncio
    async def test_health_check(self, grpc_service):
        """Test health check via gRPC."""
        request = pb.HealthRequest()

        context = Mock()
        response = await grpc_service.Health(request, context)

        assert isinstance(response, pb.HealthResponse)
        assert response.status == "ok"
        assert response.model_id == "mock-model"
        assert response.device == "cpu"
        assert response.dim > 0

    @pytest.mark.asyncio
    async def test_embed_with_default_task_type(self, grpc_service):
        """Test embedding with default task type (None)."""
        request = pb.EmbedRequest(
            text="Test with default task type",
            # task_type not set, should default to "passage"
            normalize=True,
        )

        context = Mock()
        response = await grpc_service.Embed(request, context)

        assert isinstance(response, pb.EmbedResponse)
        assert len(response.embedding) > 0

    @pytest.mark.asyncio
    async def test_embed_with_default_normalize(self, grpc_service):
        """Test embedding with default normalize (None)."""
        request = pb.EmbedRequest(
            text="Test with default normalize",
            task_type="passage",
            # normalize not set, should default to True
        )

        context = Mock()
        response = await grpc_service.Embed(request, context)

        assert isinstance(response, pb.EmbedResponse)
        assert len(response.embedding) > 0

    @pytest.mark.asyncio
    async def test_embed_task_type_variations(self, grpc_service):
        """Test different task types via gRPC."""
        text = "Test text for different task types"

        for task_type in ["passage", "query"]:
            request = pb.EmbedRequest(text=text, task_type=task_type, normalize=True)

            context = Mock()
            response = await grpc_service.Embed(request, context)

            assert isinstance(response, pb.EmbedResponse)
            assert len(response.embedding) > 0

    @pytest.mark.asyncio
    async def test_embed_normalize_variations(self, grpc_service):
        """Test with different normalize values via gRPC."""
        text = "Test text for normalization"

        for normalize in [True, False]:
            request = pb.EmbedRequest(
                text=text, task_type="passage", normalize=normalize
            )

            context = Mock()
            response = await grpc_service.Embed(request, context)

            assert isinstance(response, pb.EmbedResponse)
            assert len(response.embedding) > 0

    @pytest.mark.asyncio
    async def test_large_text_input_grpc(self, grpc_service):
        """Test with large text input via gRPC."""
        large_text = "A" * 10000  # 10KB of text

        request = pb.EmbedRequest(text=large_text, task_type="passage", normalize=True)

        context = Mock()
        response = await grpc_service.Embed(request, context)

        assert isinstance(response, pb.EmbedResponse)
        assert len(response.embedding) > 0

    @pytest.mark.asyncio
    async def test_many_texts_batch_grpc(self, grpc_service):
        """Test batch processing with many texts via gRPC."""
        many_texts = [f"gRPC text number {i}" for i in range(50)]

        request = pb.EmbedBatchRequest(
            texts=many_texts, task_type="passage", normalize=True
        )

        context = Mock()
        response = await grpc_service.EmbedBatch(request, context)

        assert len(response.items) == 50
        for i, item in enumerate(response.items):
            assert item.index == i
            assert len(item.embedding) == response.dim

    @pytest.mark.asyncio
    async def test_special_characters_grpc(self, grpc_service):
        """Test with special characters and unicode via gRPC."""
        request = pb.EmbedRequest(
            text="gRPC Special chars: éñüñ, 中文, emoji 🚀, symbols @#$%",
            task_type="passage",
            normalize=True,
        )

        context = Mock()
        response = await grpc_service.Embed(request, context)

        assert isinstance(response, pb.EmbedResponse)
        assert len(response.embedding) > 0

    @pytest.mark.asyncio
    async def test_consistency_across_methods(self, grpc_service):
        """Test consistency between single embed, batch embed, and health."""
        text = "Consistency test text"

        # Single embed
        single_request = pb.EmbedRequest(text=text, task_type="passage", normalize=True)
        context = Mock()
        single_response = await grpc_service.Embed(single_request, context)

        # Batch embed with same text
        batch_request = pb.EmbedBatchRequest(
            texts=[text], task_type="passage", normalize=True
        )
        batch_response = await grpc_service.EmbedBatch(batch_request, context)

        # Health check
        health_request = pb.HealthRequest()
        health_response = await grpc_service.Health(health_request, context)

        # All should have same model_id and dimensions
        assert single_response.model_id == batch_response.model_id
        assert single_response.model_id == health_response.model_id
        assert single_response.dim == batch_response.dim
        assert single_response.dim == health_response.dim

        # Embedding dimensions should match
        assert len(single_response.embedding) == single_response.dim
        assert len(batch_response.items[0].embedding) == batch_response.dim
