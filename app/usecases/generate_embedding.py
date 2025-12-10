from typing import Any, Dict, List

from ..ports.encoder_port import EncoderPort

# Health check constants
HEALTH_STATUS_OK = "ok"
HEALTH_PROBE_TEXT = "ping"

# Dimension probe constants
DIMENSION_PROBE_TEXT = "probe"

# Default task type for use cases
DEFAULT_TASK_TYPE = "passage"

# Response field names
FIELD_MODEL_ID = "model_id"
FIELD_DIM = "dim" 
FIELD_EMBEDDING = "embedding"
FIELD_ITEMS = "items"
FIELD_STATUS = "status"
FIELD_DEVICE = "device"
FIELD_INDEX = "index"
FIELD_BATCH_SIZE = "batch_size"


class GenerateEmbeddingUC:
    def __init__(self, encoder: EncoderPort):
        self.encoder = encoder

    def embed(
        self, text: str, task_type: str = DEFAULT_TASK_TYPE, normalize: bool = True
    ) -> Dict[str, Any]:
        vec = self.encoder.encode([text], task_type=task_type, normalize=normalize)[0]
        return {
            FIELD_MODEL_ID: self.encoder.model_id(), 
            FIELD_DIM: len(vec), 
            FIELD_EMBEDDING: vec
        }

    def embed_batch(
        self, texts: List[str], task_type: str = DEFAULT_TASK_TYPE, normalize: bool = True
    ) -> Dict[str, Any]:
        if not texts:
            # Handle empty batch - use a probe to get dimensions
            probe = self.encoder.encode(
                [DIMENSION_PROBE_TEXT], task_type=task_type, normalize=normalize
            )[0]
            return {
                FIELD_MODEL_ID: self.encoder.model_id(),
                FIELD_DIM: len(probe),
                FIELD_ITEMS: [],
            }

        vecs = self.encoder.encode(texts, task_type=task_type, normalize=normalize)
        dim = len(vecs[0])
        return {
            FIELD_MODEL_ID: self.encoder.model_id(),
            FIELD_DIM: dim,
            FIELD_ITEMS: [{FIELD_INDEX: i, FIELD_EMBEDDING: v} for i, v in enumerate(vecs)],
        }

    def health(self) -> Dict[str, Any]:
        probe = self.encoder.encode([HEALTH_PROBE_TEXT], task_type=DEFAULT_TASK_TYPE, normalize=True)[0]
        return {
            FIELD_STATUS: HEALTH_STATUS_OK,
            FIELD_MODEL_ID: self.encoder.model_id(),
            FIELD_DEVICE: self.encoder.device(),
            FIELD_DIM: len(probe),
            FIELD_BATCH_SIZE: self.encoder.batch_size(),
        }
