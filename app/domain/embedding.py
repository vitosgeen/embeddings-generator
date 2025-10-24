from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class EmbeddingVector:
    values: Tuple[float, ...]

    def __init__(self, values: List[float]):
        object.__setattr__(self, "values", tuple(values))

    @property
    def dim(self) -> int:
        return len(self.values)
