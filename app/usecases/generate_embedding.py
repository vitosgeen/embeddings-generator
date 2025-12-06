from typing import Any, Dict, List

from ..ports.encoder_port import EncoderPort
from .. import config

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


class GenerateEmbeddingUC:
    def __init__(self, encoder: EncoderPort):
        self.encoder = encoder

    def embed(
        self, text: str, task_type: str = DEFAULT_TASK_TYPE, normalize: bool = True, model: str = None
    ) -> Dict[str, Any]:
        # model parameter ignored for backward compatibility with single-model architecture
        vec = self.encoder.encode([text], task_type=task_type, normalize=normalize)[0]
        return {
            FIELD_MODEL_ID: self.encoder.model_id(), 
            FIELD_DIM: len(vec), 
            FIELD_EMBEDDING: vec
        }

    def embed_batch(
        self, texts: List[str], task_type: str = DEFAULT_TASK_TYPE, normalize: bool = True, model: str = None
    ) -> Dict[str, Any]:
        # model parameter ignored for backward compatibility with single-model architecture
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
            "batch_size": config.BATCH_SIZE,
        }


class MultiModelEmbeddingUC:
    """Use case for handling multiple models (fast and thinking)."""
    
    def __init__(self, encoders: Dict[str, EncoderPort], model_aliases: Dict[str, str]):
        self.encoders = encoders
        self.model_aliases = model_aliases
        self.default_model = "fast"
    
    def _get_encoder(self, model: str = None) -> tuple[EncoderPort, str]:
        """Get encoder by model name or alias."""
        if not model:
            model = self.default_model
        
        # Resolve alias
        model_id = self.model_aliases.get(model, model)
        
        # Find encoder by model_id
        for name, encoder in self.encoders.items():
            if encoder.model_id() == model_id or name == model:
                return encoder, name
        
        # Fallback to default
        return self.encoders[self.default_model], self.default_model
    
    def embed(
        self, 
        text: str, 
        model: str = None,
        task_type: str = DEFAULT_TASK_TYPE, 
        normalize: bool = True
    ) -> Dict[str, Any]:
        encoder, model_name = self._get_encoder(model)
        vec = encoder.encode([text], task_type=task_type, normalize=normalize)[0]
        return {
            FIELD_MODEL_ID: encoder.model_id(),
            "model_name": model_name,
            FIELD_DIM: len(vec), 
            FIELD_EMBEDDING: vec
        }

    def embed_batch(
        self, 
        texts: List[str], 
        model: str = None,
        task_type: str = DEFAULT_TASK_TYPE, 
        normalize: bool = True
    ) -> Dict[str, Any]:
        encoder, model_name = self._get_encoder(model)
        
        if not texts:
            probe = encoder.encode(
                [DIMENSION_PROBE_TEXT], task_type=task_type, normalize=normalize
            )[0]
            return {
                FIELD_MODEL_ID: encoder.model_id(),
                "model_name": model_name,
                FIELD_DIM: len(probe),
                FIELD_ITEMS: [],
            }

        vecs = encoder.encode(texts, task_type=task_type, normalize=normalize)
        dim = len(vecs[0])
        return {
            FIELD_MODEL_ID: encoder.model_id(),
            "model_name": model_name,
            FIELD_DIM: dim,
            FIELD_ITEMS: [{FIELD_INDEX: i, FIELD_EMBEDDING: v} for i, v in enumerate(vecs)],
        }

    def health(self) -> Dict[str, Any]:
        """Health check with info about all available models."""
        models_info = {}
        for name, encoder in self.encoders.items():
            probe = encoder.encode([HEALTH_PROBE_TEXT], task_type=DEFAULT_TASK_TYPE, normalize=True)[0]
            models_info[name] = {
                FIELD_MODEL_ID: encoder.model_id(),
                FIELD_DEVICE: encoder.device(),
                FIELD_DIM: len(probe),
            }
        
        return {
            FIELD_STATUS: HEALTH_STATUS_OK,
            "models": models_info,
            "default_model": self.default_model,
            "batch_size": config.BATCH_SIZE,
        }
