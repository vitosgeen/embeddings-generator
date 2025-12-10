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
        """
        Health check endpoint that verifies the encoder is operational.
        
        Returns:
            Dict with status, model_id, device, dim (embedding dimension),
            and batch_size (maximum number of texts processed simultaneously).
        """
        probe = self.encoder.encode([HEALTH_PROBE_TEXT], task_type=DEFAULT_TASK_TYPE, normalize=True)[0]
        return {
            FIELD_STATUS: HEALTH_STATUS_OK,
            FIELD_MODEL_ID: self.encoder.model_id(),
            FIELD_DEVICE: self.encoder.device(),
            FIELD_DIM: len(probe),
            FIELD_BATCH_SIZE: self.encoder.batch_size(),  # Processing batch size capability
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
            
            # If single sentence is longer than chunk_size, split it into character-based chunks
            if sentence_length > chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split long sentence into character-based chunks with overlap
                for i in range(0, len(sentence), chunk_size - overlap):
                    chunk = sentence[i:i + chunk_size]
                    if chunk.strip():
                        chunks.append(chunk)
                
                # Don't carry over overlap from long sentences - they're already internally overlapping
                # Reset for next sentence
                current_chunk = []
                current_length = 0
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
                            # Account for space between sentences when calculating overlap
                            space_needed = 1 if overlap_sentences else 0
                            if overlap_length + len(s) + space_needed <= overlap:
                                overlap_sentences.insert(0, s)
                                overlap_length += len(s) + space_needed
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
        Embed long text by splitting it into chunks, encoding each chunk, and aggregating the embeddings.

        This method handles texts that exceed model input limits by automatically splitting them into
        manageable chunks, generating embeddings for each chunk, and aggregating them using mean pooling.

        Parameters:
            text (str): The input text to embed.
            task_type (str, optional): The task type for the encoder. Common values: "passage", "query".
                Default: "passage".
            normalize (bool, optional): If True, normalizes each chunk embedding before aggregation,
                and normalizes the aggregated embedding after mean pooling. Default: True.
            chunk_size (int, optional): The maximum number of characters per chunk. Default: 1000.
            chunk_overlap (int, optional): The number of overlapping characters between consecutive
                chunks. Helps maintain context across chunk boundaries. Default: 100.

        Aggregation and Normalization Process:
            1. The input text is split into overlapping chunks using sentence boundaries when possible.
            2. Each chunk is encoded into an embedding vector WITHOUT normalization (to avoid double normalization).
            3. The aggregated embedding is computed as the mean of all chunk embeddings (mean pooling).
            4. If normalize=True: The aggregated embedding is normalized to unit length after mean pooling.
            5. Individual chunk embeddings in the response are normalized separately if normalize=True.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - model_id (str): The model used for encoding.
                - dim (int): The dimension of the embedding vectors.
                - embedding (List[float]): The aggregated embedding (mean of all chunk embeddings).
                - chunk_count (int): The number of chunks created from the input text.
                - aggregation (str): The aggregation method used ("mean").
                - chunks (List[Dict]): List of dictionaries for each chunk, each containing:
                    - index (int): The chunk index (0-based).
                    - text_preview (str): The first 100 characters of the chunk, truncated with "..."
                        if longer. Useful for debugging and understanding chunk boundaries.
                    - length (int): The length of the chunk in characters.
                    - embedding (List[float]): The full embedding vector for the chunk.

        Memory and Performance Notes:
            - All chunk embeddings are kept in memory and included in the response.
            - For very long texts: With 100 chunks and 1024-dimensional embeddings, memory usage
              is approximately 800KB per request, with similar JSON response size.
            - Consider the memory implications when processing very long texts or handling
              many concurrent requests.
            - The batch_size parameter (from encoder configuration) affects processing speed.

        Example:
            >>> uc = GenerateEmbeddingUC(encoder)
            >>> result = uc.embed_chunked(
            ...     "Very long text..." * 1000,
            ...     chunk_size=500,
            ...     chunk_overlap=50
            ... )
            >>> print(f"Created {result['chunk_count']} chunks")
            >>> print(f"Aggregated embedding dim: {result['dim']}")
        """
        # Create chunks
        chunks = self._chunk_text(text, chunk_size, chunk_overlap)
        
        # Get embeddings for all chunks WITHOUT normalization
        # We'll normalize the final aggregated embedding instead
        chunk_embeddings = self.encoder.encode(chunks, task_type=task_type, normalize=False)
        
        # Aggregate embeddings (mean pooling)
        aggregated = np.mean(chunk_embeddings, axis=0)
        
        # Normalize the aggregated embedding if requested
        if normalize:
            norm = np.linalg.norm(aggregated)
            if norm > 0:
                aggregated = aggregated / norm
        
        aggregated = aggregated.tolist()
        
        # For individual chunk embeddings in the response, normalize them if requested
        if normalize:
            chunk_embeddings_for_response = []
            for emb in chunk_embeddings:
                # Convert to numpy array if it's a list
                emb_array = np.array(emb) if isinstance(emb, list) else emb
                norm = np.linalg.norm(emb_array)
                if norm > 0:
                    chunk_embeddings_for_response.append((emb_array / norm).tolist())
                else:
                    chunk_embeddings_for_response.append(emb_array.tolist())
        else:
            chunk_embeddings_for_response = [
                emb.tolist() if hasattr(emb, 'tolist') else emb 
                for emb in chunk_embeddings
            ]
        
        return {
            FIELD_MODEL_ID: self.encoder.model_id(),
            FIELD_DIM: len(aggregated),
            FIELD_EMBEDDING: aggregated,
            FIELD_CHUNK_COUNT: len(chunks),
            FIELD_AGGREGATION: "mean",
            FIELD_CHUNKS: [
                {
                    FIELD_INDEX: i,
                    # Note: Chunks exactly 100 characters won't have "..." appended
                    "text_preview": chunk[:100] + "..." if len(chunk) > 100 else chunk,
                    "length": len(chunk),
                    FIELD_EMBEDDING: emb,
                }
                for i, (chunk, emb) in enumerate(zip(chunks, chunk_embeddings_for_response))
            ],
        }
