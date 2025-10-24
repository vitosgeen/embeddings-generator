import asyncio

import grpc

from proto import embeddings_pb2 as pb
from proto import embeddings_pb2_grpc as pb_grpc

from ...usecases.generate_embedding import GenerateEmbeddingUC


class EmbeddingsService(pb_grpc.EmbeddingsServiceServicer):
    def __init__(self, uc: GenerateEmbeddingUC):
        self.uc = uc

    async def Embed(self, request: pb.EmbedRequest, context):
        out = self.uc.embed(
            request.text,
            task_type=request.task_type or "passage",
            normalize=request.normalize or True,
        )
        return pb.EmbedResponse(
            model_id=out["model_id"], dim=out["dim"], embedding=out["embedding"]
        )

    async def EmbedBatch(self, request: pb.EmbedBatchRequest, context):
        texts = list(request.texts)
        out = self.uc.embed_batch(
            texts,
            task_type=request.task_type or "passage",
            normalize=request.normalize or True,
        )
        items = [
            pb.EmbeddingItem(index=it["index"], embedding=it["embedding"])
            for it in out["items"]
        ]
        return pb.EmbedBatchResponse(
            model_id=out["model_id"], dim=out["dim"], items=items
        )

    async def Health(self, request: pb.HealthRequest, context):
        h = self.uc.health()
        return pb.HealthResponse(
            status=h["status"], model_id=h["model_id"], device=h["device"], dim=h["dim"]
        )


async def serve_grpc(uc: GenerateEmbeddingUC, host: str = "0.0.0.0", port: int = 50051):
    server = grpc.aio.server()
    pb_grpc.add_EmbeddingsServiceServicer_to_server(EmbeddingsService(uc), server)
    server.add_insecure_port(f"{host}:{port}")
    await server.start()
    return server
