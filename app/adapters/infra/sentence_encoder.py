from typing import List

import torch
from sentence_transformers import SentenceTransformer

_PREFIXES = {
    "passage": "Represent this passage for retrieval: ",
    "query": "Represent this query for retrieving relevant passages: ",
}


class SentenceEncoder:
    def __init__(self, model_id: str, device: str | None = None, batch_size: int = 32):
        self._model_id = model_id
        self._device = device or (
            "cuda"
            if torch.cuda.is_available()
            else (
                "mps"
                if getattr(torch.backends, "mps", None)
                and torch.backends.mps.is_available()
                else "cpu"
            )
        )
        self._model = SentenceTransformer(self._model_id, device=self._device)
        self._batch_size = batch_size

    def _prefix(self, texts: List[str], task_type: str) -> List[str]:
        prefix = _PREFIXES.get(task_type, _PREFIXES["passage"])
        return [prefix + t for t in texts]

    def encode(
        self, texts: List[str], task_type: str = "passage", normalize: bool = True
    ) -> List[List[float]]:
        prepared = self._prefix(texts, task_type)
        vecs = self._model.encode(
            prepared,
            batch_size=self._batch_size,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )
        return [v.tolist() for v in vecs]

    def dim(self) -> int:
        return len(self.encode(["dim_probe"], "passage", True)[0])

    def device(self) -> str:
        return self._device

    def model_id(self) -> str:
        return self._model_id
