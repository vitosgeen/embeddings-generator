#!/usr/bin/env python3
"""
Manual test for /embed/chunks endpoint.

This endpoint returns individual chunks with their full text and embeddings,
useful for detailed analysis, moderation pipelines, or fragment-level processing.
"""

import requests
import json

BASE_URL = "http://localhost:8000"
API_KEY = "sk-admin-abc123xyz789"  # Replace with your actual API key

def test_embed_chunks():
    """Test the /embed/chunks endpoint with a sample text."""
    
    # Sample text that will be split into multiple chunks
    sample_text = """
    Artificial intelligence is rapidly transforming the world. Machine learning models
    are becoming more sophisticated each year. Deep learning has revolutionized computer
    vision and natural language processing. Large language models can now generate
    human-like text and assist with various tasks. 
    
    However, these powerful technologies also raise important ethical questions about
    privacy, bias, and accountability. We must carefully consider how to develop and
    deploy AI systems responsibly. The future of AI depends on our ability to address
    these challenges while continuing to innovate.
    
    Research in AI continues to accelerate, with new breakthroughs happening regularly.
    From healthcare to finance, from education to entertainment, AI is finding applications
    in nearly every domain of human activity.
    """
    
    # Request payload
    payload = {
        "text": sample_text,
        "chunk_size": 200,  # Small chunks to demonstrate splitting
        "chunk_overlap": 50,
        "task_type": "passage",
        "normalize": True
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print("🔹 Testing /embed/chunks endpoint...")
    print(f"📝 Text length: {len(sample_text)} characters")
    print(f"⚙️  Chunk size: {payload['chunk_size']}, Overlap: {payload['chunk_overlap']}")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/embed/chunks",
            json=payload,
            headers=headers
        )
        
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Request successful!")
        print(f"📊 Model: {data['model_id']}")
        print(f"📏 Dimensions: {data['dim']}")
        print(f"📦 Number of chunks: {data['chunk_count']}")
        print(f"👤 Requested by: {data['requested_by']}")
        print()
        
        # Display each chunk
        for i, chunk in enumerate(data['chunks']):
            chunk_text, embedding, chunk_num = chunk
            
            print(f"--- Chunk {chunk_num} ---")
            print(f"Text length: {len(chunk_text)} chars")
            print(f"Text preview: {chunk_text[:100]}...")
            print(f"Embedding: [{embedding[0]:.4f}, {embedding[1]:.4f}, ..., {embedding[-1]:.4f}]")
            print(f"Embedding dimensions: {len(embedding)}")
            print()
        
        # Verify structure
        print("✅ Verification:")
        print(f"   - All chunks have full text (not previews): {all(len(c[0]) > 100 for c in data['chunks'])}")
        print(f"   - All embeddings have correct dimensions: {all(len(c[1]) == data['dim'] for c in data['chunks'])}")
        print(f"   - Chunk numbers are sequential: {[c[2] for c in data['chunks']] == list(range(1, data['chunk_count'] + 1))}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")


def compare_endpoints():
    """Compare /embed/chunked vs /embed/chunks responses."""
    
    sample_text = "First sentence. Second sentence. Third sentence."
    
    payload = {
        "text": sample_text,
        "chunk_size": 30,
        "chunk_overlap": 5,
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print("\n" + "="*70)
    print("🔹 Comparing /embed/chunked vs /embed/chunks")
    print("="*70 + "\n")
    
    # Test /embed/chunked
    print("1️⃣  /embed/chunked (aggregated embedding):")
    try:
        response = requests.post(f"{BASE_URL}/embed/chunked", json=payload, headers=headers)
        response.raise_for_status()
        chunked_data = response.json()
        
        print(f"   ✓ Has aggregated embedding: {'embedding' in chunked_data}")
        print(f"   ✓ Has aggregation method: {chunked_data.get('aggregation', 'N/A')}")
        print(f"   ✓ Chunks have text_preview: {all('text_preview' in c for c in chunked_data['chunks'])}")
        print(f"   ✓ Preview length: {len(chunked_data['chunks'][0]['text_preview'])} chars")
        print()
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
    
    # Test /embed/chunks
    print("2️⃣  /embed/chunks (individual chunks with full text):")
    try:
        response = requests.post(f"{BASE_URL}/embed/chunks", json=payload, headers=headers)
        response.raise_for_status()
        chunks_data = response.json()
        
        print(f"   ✓ Has aggregated embedding: {'embedding' in chunks_data}")
        print(f"   ✓ Chunks are arrays [text, emb, num]: {isinstance(chunks_data['chunks'][0], list)}")
        print(f"   ✓ Has full chunk text: {len(chunks_data['chunks'][0][0])} chars")
        print(f"   ✓ Text content: '{chunks_data['chunks'][0][0][:50]}...'")
        print()
    except Exception as e:
        print(f"   ❌ Failed: {e}\n")
    
    print("💡 Use Case Guide:")
    print("   • /embed/chunked → Document similarity search (save aggregated embedding)")
    print("   • /embed/chunks  → Detailed analysis, moderation, fragment processing")
    print()


if __name__ == "__main__":
    print("🧪 Manual Test: /embed/chunks Endpoint\n")
    
    # Test basic functionality
    test_embed_chunks()
    
    # Compare with /embed/chunked
    compare_endpoints()
    
    print("\n✅ Manual test completed!")
