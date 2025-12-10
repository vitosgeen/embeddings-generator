from typing import Any, Dict, List
import numpy as np
import re

from ..ports.encoder_port import EncoderPort

# Health check constants
HEALTH_STATUS_OK = "ok"
HEALTH_PROBE_TEXT = "ping"

# Dimension probe constants
DIMENSION_PROBE_TEXT = "probe"

# Default task type for use cases
DEFAULT_TASK_TYPE = "passage"

# Chunking defaults
DEFAULT_CHUNK_SIZE = 1000  # characters
DEFAULT_CHUNK_OVERLAP = 100  # characters

# Response field names
FIELD_MODEL_ID = "model_id"
FIELD_DIM = "dim" 
FIELD_EMBEDDING = "embedding"
FIELD_ITEMS = "items"
FIELD_STATUS = "status"
FIELD_DEVICE = "device"
FIELD_INDEX = "index"
FIELD_BATCH_SIZE = "batch_size"
FIELD_CHUNKS = "chunks"
FIELD_CHUNK_COUNT = "chunk_count"
FIELD_AGGREGATION = "aggregation"


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

    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Split text into overlapping chunks based on sentences.
        Tries to respect sentence boundaries while staying within chunk_size.
        """
        if len(text) <= chunk_size:
            return [text]
        
        # Split text into sentences using regex
        # Matches common sentence endings: . ! ? followed by space or newline
        sentence_pattern = r'(?<=[.!?])\s+'
        sentences = re.split(sentence_pattern, text.strip())
        
        # Remove empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return [text]
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If single sentence is longer than chunk_size, split it
            if sentence_length > chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split long sentence into character-based chunks
                for i in range(0, len(sentence), chunk_size - overlap):
                    chunk = sentence[i:i + chunk_size]
                    if chunk.strip():
                        chunks.append(chunk)
                continue
            
            # If adding this sentence exceeds chunk_size, start new chunk
            if current_length + sentence_length > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Apply overlap: keep last few sentences if overlap is specified
                if overlap > 0:
                    overlap_text = ' '.join(current_chunk)
                    if len(overlap_text) > overlap:
                        # Keep approximately 'overlap' characters from the end
                        overlap_sentences = []
                        overlap_length = 0
                        for s in reversed(current_chunk):
                            if overlap_length + len(s) <= overlap:
                                overlap_sentences.insert(0, s)
                                overlap_length += len(s) + 1  # +1 for space
                            else:
                                break
                        current_chunk = overlap_sentences
                        current_length = overlap_length
                    else:
                        current_chunk = []
                        current_length = 0
                else:
                    current_chunk = []
                    current_length = 0
            
            current_chunk.append(sentence)
            current_length += sentence_length + 1  # +1 for space
        
        # Add the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [text]

    def embed_chunked(
        self,
        text: str,
        task_type: str = DEFAULT_TASK_TYPE,
        normalize: bool = True,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> Dict[str, Any]:
        """
        Embed long text by splitting into chunks and aggregating.
        
        Returns:
            - model_id: The model used
            - dim: Embedding dimension
            - embedding: Aggregated embedding (mean of all chunks)
            - chunk_count: Number of chunks created
            - chunks: List of chunk info (text preview + embedding)
        """
        # Create chunks
        chunks = self._chunk_text(text, chunk_size, chunk_overlap)
        
        # Get embeddings for all chunks
        chunk_embeddings = self.encoder.encode(chunks, task_type=task_type, normalize=normalize)
        
        # Aggregate embeddings (mean pooling)
        aggregated = np.mean(chunk_embeddings, axis=0).tolist()
        
        # Normalize the aggregated embedding if requested
        if normalize:
            norm = np.linalg.norm(aggregated)
            if norm > 0:
                aggregated = (np.array(aggregated) / norm).tolist()
        
        return {
            FIELD_MODEL_ID: self.encoder.model_id(),
            FIELD_DIM: len(aggregated),
            FIELD_EMBEDDING: aggregated,
            FIELD_CHUNK_COUNT: len(chunks),
            FIELD_AGGREGATION: "mean",
            FIELD_CHUNKS: [
                {
                    FIELD_INDEX: i,
                    "text_preview": chunk[:100] + "..." if len(chunk) > 100 else chunk,
                    "length": len(chunk),
                    FIELD_EMBEDDING: emb,
                }
                for i, (chunk, emb) in enumerate(zip(chunks, chunk_embeddings))
            ],
        }
