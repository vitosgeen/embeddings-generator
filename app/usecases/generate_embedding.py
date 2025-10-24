from typing import Any, Dict, List

from ..ports.encoder_port import EncoderPort


class GenerateEmbeddingUC:
    def __init__(self, encoder: EncoderPort):
        self.encoder = encoder

    def embed(
        self, text: str, task_type: str = "passage", normalize: bool = True
    ) -> Dict[str, Any]:
        vec = self.encoder.encode([text], task_type=task_type, normalize=normalize)[0]
        return {"model_id": self.encoder.model_id(), "dim": len(vec), "embedding": vec}

    def embed_batch(
        self, texts: List[str], task_type: str = "passage", normalize: bool = True
    ) -> Dict[str, Any]:
        if not texts:
            # Handle empty batch - use a probe to get dimensions
            probe = self.encoder.encode(
                ["probe"], task_type=task_type, normalize=normalize
            )[0]
            return {
                "model_id": self.encoder.model_id(),
                "dim": len(probe),
                "items": [],
            }

        vecs = self.encoder.encode(texts, task_type=task_type, normalize=normalize)
        dim = len(vecs[0])
        return {
            "model_id": self.encoder.model_id(),
            "dim": dim,
            "items": [{"index": i, "embedding": v} for i, v in enumerate(vecs)],
        }

    def health(self) -> Dict[str, Any]:
        probe = self.encoder.encode(["ping"], task_type="passage", normalize=True)[0]
        return {
            "status": "ok",
            "model_id": self.encoder.model_id(),
            "device": self.encoder.device(),
            "dim": len(probe),
        }
