from typing import Any, Dict, List, Protocol


class EmbeddingServicePort(Protocol):
    def embed(
        self, text: str, task_type: str = "passage", normalize: bool = True
    ) -> Dict[str, Any]: ...
    def embed_batch(
        self, texts: List[str], task_type: str = "passage", normalize: bool = True
    ) -> Dict[str, Any]: ...
    def health(self) -> Dict[str, Any]: ...
