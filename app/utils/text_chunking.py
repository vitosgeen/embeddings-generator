"""Text chunking utilities for handling long documents."""

from typing import List, Dict, Any, Optional
import numpy as np


def chunk_text(
    text: str,
    max_chars: int = 2000,
    overlap: int = 200,
    min_chunk_size: int = 100
) -> List[str]:
    """Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk
        overlap: Character overlap between chunks
        min_chunk_size: Minimum size for a chunk
        
    Returns:
        List of text chunks
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + max_chars
        
        # If this is not the last chunk, try to break at sentence boundary
        if end < len(text):
            # Look for sentence boundaries in the last 200 chars
            search_start = max(end - 200, start)
            last_period = text.rfind('. ', search_start, end)
            last_newline = text.rfind('\n', search_start, end)
            last_question = text.rfind('? ', search_start, end)
            last_exclamation = text.rfind('! ', search_start, end)
            
            # Use the latest sentence boundary found
            boundary = max(last_period, last_newline, last_question, last_exclamation)
            if boundary > search_start:
                end = boundary + 1  # Include the punctuation
        
        chunk = text[start:end].strip()
        
        # Only add if chunk is substantial
        if len(chunk) >= min_chunk_size:
            chunks.append(chunk)
        
        # Move start position with overlap
        start = end - overlap
        
        # Avoid infinite loop if overlap is too large
        if chunks and start <= len(chunks[-1]):
            start = end
    
    return chunks


def combine_embeddings(
    embeddings: List[List[float]],
    method: str = "average",
    weights: Optional[List[float]] = None
) -> List[float]:
    """Combine multiple embeddings into one.
    
    Args:
        embeddings: List of embedding vectors
        method: Combination method ('average', 'weighted', 'max')
        weights: Weights for 'weighted' method (default: exponential decay)
        
    Returns:
        Combined embedding vector
    """
    if not embeddings:
        raise ValueError("No embeddings to combine")
    
    if len(embeddings) == 1:
        return embeddings[0]
    
    arr = np.array(embeddings)
    
    if method == "average":
        return np.mean(arr, axis=0).tolist()
    
    elif method == "weighted":
        if weights is None:
            # Default: exponential decay (first chunk = most important)
            weights = [0.5 ** i for i in range(len(embeddings))]
            weights = np.array(weights) / sum(weights)  # Normalize
        else:
            weights = np.array(weights)
            if len(weights) != len(embeddings):
                raise ValueError("Weights length must match embeddings length")
            weights = weights / np.sum(weights)  # Normalize
        
        return np.average(arr, axis=0, weights=weights).tolist()
    
    elif method == "max":
        return np.max(arr, axis=0).tolist()
    
    elif method == "first":
        # Just use first chunk (most important)
        return embeddings[0]
    
    else:
        raise ValueError(f"Unknown combination method: {method}")


def estimate_tokens(text: str) -> int:
    """Estimate token count from text.
    
    Rough estimate: ~4 characters per token for English.
    
    Args:
        text: Input text
        
    Returns:
        Estimated token count
    """
    return len(text) // 4


def should_chunk(text: str, max_tokens: int = 512) -> bool:
    """Check if text should be chunked.
    
    Args:
        text: Input text
        max_tokens: Maximum tokens supported by model
        
    Returns:
        True if text should be chunked
    """
    estimated_tokens = estimate_tokens(text)
    # Use 80% of max to be safe
    return estimated_tokens > (max_tokens * 0.8)


def get_chunking_info(text: str, max_chars: int = 2000) -> Dict[str, Any]:
    """Get information about how text would be chunked.
    
    Args:
        text: Input text
        max_chars: Maximum characters per chunk
        
    Returns:
        Dictionary with chunking information
    """
    text_length = len(text)
    estimated_tokens = estimate_tokens(text)
    would_be_chunked = should_chunk(text)
    
    if would_be_chunked:
        chunks = chunk_text(text, max_chars=max_chars)
        num_chunks = len(chunks)
        chunk_sizes = [len(c) for c in chunks]
    else:
        num_chunks = 1
        chunk_sizes = [text_length]
    
    return {
        "text_length": text_length,
        "estimated_tokens": estimated_tokens,
        "would_be_chunked": would_be_chunked,
        "num_chunks": num_chunks,
        "chunk_sizes": chunk_sizes,
        "max_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
        "min_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
    }
