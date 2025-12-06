#!/usr/bin/env python3
"""Demo script for text chunking functionality."""

import requests
import json

BASE_URL = "http://localhost:8000"
API_KEY = "sk-admin-m1YHp13elEvafGYLT27H0gmD"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def test_short_text():
    """Test with short text (no chunking needed)."""
    print_section("1. Short Text (No Chunking)")
    
    text = "Machine learning is a subset of artificial intelligence."
    print(f"Text: {text}")
    print(f"Length: {len(text)} characters")
    
    response = requests.post(
        f"{BASE_URL}/embed",
        headers=headers,
        json={
            "text": text,
            "auto_chunk": True,
        }
    )
    
    result = response.json()
    print(f"\n✅ Response:")
    print(f"  Was chunked: {result.get('was_chunked', False)}")
    print(f"  Embedding dim: {result['dim']}")
    print(f"  Text length: {result.get('text_length', 0)}")


def test_long_text_without_chunking():
    """Test with long text but chunking disabled."""
    print_section("2. Long Text WITHOUT auto_chunk (Truncation Warning)")
    
    # Generate 3800 character text
    text = "This is a test sentence about machine learning and AI. " * 70
    print(f"Text: {text[:100]}...")
    print(f"Length: {len(text)} characters")
    
    response = requests.post(
        f"{BASE_URL}/embed",
        headers=headers,
        json={
            "text": text,
            "auto_chunk": False,  # Disabled
        }
    )
    
    result = response.json()
    print(f"\n⚠️  Response:")
    print(f"  Warning: {result.get('warning', 'None')}")
    print(f"  Truncated: {result.get('truncated', False)}")
    print(f"  Text length: {result.get('text_length', 0)}")


def test_long_text_with_chunking():
    """Test with long text and auto-chunking."""
    print_section("3. Long Text WITH auto_chunk (Smart Chunking)")
    
    # Generate 3800 character text
    text = "This is a test sentence about machine learning and AI. " * 70
    print(f"Text: {text[:100]}...")
    print(f"Length: {len(text)} characters")
    
    response = requests.post(
        f"{BASE_URL}/embed",
        headers=headers,
        json={
            "text": text,
            "auto_chunk": True,  # Enabled
            "chunk_size": 2000,
            "chunk_overlap": 200,
            "combine_method": "average",
        }
    )
    
    result = response.json()
    print(f"\n✅ Response:")
    print(f"  Was chunked: {result.get('was_chunked', False)}")
    print(f"  Number of chunks: {result.get('num_chunks', 0)}")
    print(f"  Chunk sizes: {result.get('chunk_sizes', [])}")
    print(f"  Combine method: {result.get('combine_method', 'N/A')}")
    print(f"  Embedding dim: {result['dim']}")
    print(f"  Total text length: {result.get('text_length', 0)}")


def test_very_long_text():
    """Test with very long text (multiple chunks)."""
    print_section("4. Very Long Text (Multiple Chunks)")
    
    # Generate 8000 character text
    text = "Natural language processing (NLP) is a field of AI. " * 150
    print(f"Text: {text[:100]}...")
    print(f"Length: {len(text)} characters")
    
    response = requests.post(
        f"{BASE_URL}/embed",
        headers=headers,
        json={
            "text": text,
            "auto_chunk": True,
            "chunk_size": 2000,
            "chunk_overlap": 200,
            "combine_method": "weighted",  # First chunk = more important
        }
    )
    
    result = response.json()
    print(f"\n✅ Response:")
    print(f"  Was chunked: {result.get('was_chunked', False)}")
    print(f"  Number of chunks: {result.get('num_chunks', 0)}")
    print(f"  Chunk sizes: {result.get('chunk_sizes', [])}")
    print(f"  Combine method: {result.get('combine_method', 'N/A')}")


def test_check_endpoint():
    """Test the check endpoint."""
    print_section("5. Check Endpoint (Preview Chunking)")
    
    text = "AI and machine learning. " * 100
    print(f"Text length: {len(text)} characters")
    
    response = requests.post(
        f"{BASE_URL}/embed/check",
        headers=headers,
        json={
            "text": text,
            "auto_chunk": True,
            "chunk_size": 2000,
        }
    )
    
    result = response.json()
    print(f"\n📊 Chunking Analysis:")
    print(f"  Text length: {result['text_length']} chars")
    print(f"  Estimated tokens: {result['estimated_tokens']}")
    print(f"  Would be chunked: {result['would_be_chunked']}")
    print(f"  Number of chunks: {result['num_chunks']}")
    print(f"  Chunk sizes: {result['chunk_sizes']}")
    print(f"  Max chunk: {result['max_chunk_size']} chars")
    print(f"  Min chunk: {result['min_chunk_size']} chars")
    print(f"  Recommended: {result['recommended_action']}")


def test_combine_methods():
    """Test different combination methods."""
    print_section("6. Different Combine Methods")
    
    text = "Deep learning uses neural networks. " * 80
    print(f"Text length: {len(text)} characters")
    
    methods = ["average", "weighted", "max", "first"]
    
    for method in methods:
        response = requests.post(
            f"{BASE_URL}/embed",
            headers=headers,
            json={
                "text": text,
                "auto_chunk": True,
                "combine_method": method,
            }
        )
        
        result = response.json()
        print(f"\n  Method: {method:10} | Chunks: {result.get('num_chunks', 0)} | Embedding: {result['embedding'][:3]}...")


def test_return_chunks():
    """Test returning individual chunk embeddings."""
    print_section("7. Return Individual Chunks")
    
    text = "Python is great for data science. " * 60
    print(f"Text length: {len(text)} characters")
    
    response = requests.post(
        f"{BASE_URL}/embed",
        headers=headers,
        json={
            "text": text,
            "auto_chunk": True,
            "return_chunks": True,  # Get individual chunks
        }
    )
    
    result = response.json()
    print(f"\n✅ Response:")
    print(f"  Number of chunks: {result.get('num_chunks', 0)}")
    print(f"  Chunk embeddings returned: {len(result.get('chunk_embeddings', []))}")
    print(f"  Chunks text returned: {len(result.get('chunks', []))}")
    
    if result.get('chunks'):
        for i, chunk in enumerate(result['chunks']):
            print(f"\n  Chunk {i+1}: {chunk[:80]}... ({len(chunk)} chars)")


def main():
    """Run all tests."""
    print("\n🚀 Text Chunking Demo")
    print("=" * 70)
    
    try:
        test_short_text()
        test_long_text_without_chunking()
        test_long_text_with_chunking()
        test_very_long_text()
        test_check_endpoint()
        test_combine_methods()
        test_return_chunks()
        
        print_section("✨ Demo Complete!")
        print("Auto-chunking features:")
        print("  ✅ Automatic text splitting")
        print("  ✅ Configurable chunk size & overlap")
        print("  ✅ Multiple combination methods")
        print("  ✅ Truncation warnings")
        print("  ✅ Chunking preview endpoint")
        print("  ✅ Individual chunk embeddings")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
