#!/usr/bin/env python3
"""Test script for the /embed/chunked endpoint"""

import requests
import json
import time

url = "http://127.0.0.1:8000/embed/chunked"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-admin-REPLACE-WITH-SECURE-KEY"
}

# Test cases with different text lengths
test_cases = [
    {
        "name": "Short text (no chunking needed)",
        "text": "This is a short text that doesn't need chunking.",
        "chunk_size": 1000,
        "chunk_overlap": 100,
    },
    {
        "name": "Medium text (2-3 chunks)",
        "text": "Machine learning is transforming the world. " * 50,
        "chunk_size": 1000,
        "chunk_overlap": 100,
    },
    {
        "name": "Long text (8-10 chunks)",
        "text": "Artificial intelligence and machine learning are revolutionizing technology. " * 200,
        "chunk_size": 1000,
        "chunk_overlap": 100,
    },
    {
        "name": "Very long text (20+ chunks)",
        "text": "Deep learning neural networks are powerful tools for pattern recognition and data analysis. " * 500,
        "chunk_size": 1500,
        "chunk_overlap": 150,
    },
    {
        "name": "Extremely long text (50+ chunks)",
        "text": "Natural language processing enables computers to understand human language through advanced algorithms. " * 1000,
        "chunk_size": 2000,
        "chunk_overlap": 200,
    },
]

print("Testing /embed/chunked endpoint\n")
print("=" * 80)

for test in test_cases:
    print(f"\n{test['name']}")
    print("-" * 80)
    
    data = {
        "text": test["text"],
        "chunk_size": test["chunk_size"],
        "chunk_overlap": test["chunk_overlap"],
        "task_type": "passage",
        "normalize": True
    }
    
    try:
        start = time.time()
        response = requests.post(url, headers=headers, json=data, timeout=60)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Success in {elapsed:.2f}s")
            print(f"  Model: {result['model_id']}")
            print(f"  Dimension: {result['dim']}")
            print(f"  Chunk count: {result['chunk_count']}")
            print(f"  Aggregation: {result['aggregation']}")
            print(f"  Text length: {len(test['text'])} chars")
            print(f"  Embedding length: {len(result['embedding'])}")
            
            # Show chunk details
            for chunk in result['chunks']:
                print(f"    Chunk {chunk['index']}: {chunk['length']} chars - \"{chunk['text_preview']}\"")
        else:
            print(f"✗ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"✗ Exception: {str(e)}")

print("\n" + "=" * 80)
print("Testing complete!")
