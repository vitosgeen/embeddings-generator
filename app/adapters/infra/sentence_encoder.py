from typing import List, Optional

import torch
from sentence_transformers import SentenceTransformer

# Task types
TASK_TYPE_PASSAGE = "passage"
TASK_TYPE_QUERY = "query"

# Device types
DEVICE_CUDA = "cuda"
DEVICE_MPS = "mps"
DEVICE_CPU = "cpu"

# Default values
DEFAULT_BATCH_SIZE = 32
DEFAULT_TASK_TYPE = TASK_TYPE_PASSAGE

# Embedding prefixes for different task types
PASSAGE_PREFIX = "Represent this passage for retrieval: "
QUERY_PREFIX = "Represent this query for retrieving relevant passages: "

# Probe text for dimension detection
DIM_PROBE_TEXT = "dim_probe"

_PREFIXES = {
    TASK_TYPE_PASSAGE: PASSAGE_PREFIX,
    TASK_TYPE_QUERY: QUERY_PREFIX,
}


class SentenceEncoder:
    def __init__(self, model_id: str, device: Optional[str] = None, batch_size: int = DEFAULT_BATCH_SIZE):
        self._model_id = model_id
        self._device = device or (
            DEVICE_CUDA
            if torch.cuda.is_available()
            else (
                DEVICE_MPS
                if getattr(torch.backends, DEVICE_MPS, None)
                and torch.backends.mps.is_available()
                else DEVICE_CPU
            )
        )
        self._model = SentenceTransformer(self._model_id, device=self._device)
        self._batch_size = batch_size

    def _prefix(self, texts: List[str], task_type: str) -> List[str]:
        prefix = _PREFIXES.get(task_type, _PREFIXES[DEFAULT_TASK_TYPE])
        return [prefix + t for t in texts]

    def encode(
        self, texts: List[str], task_type: str = DEFAULT_TASK_TYPE, normalize: bool = True
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
        return len(self.encode([DIM_PROBE_TEXT], DEFAULT_TASK_TYPE, True)[0])

    def device(self) -> str:
        return self._device

    def model_id(self) -> str:
        return self._model_id

    def batch_size(self) -> int:
        return self._batch_size
