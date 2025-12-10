#!/usr/bin/env python3
# NOTE: Set your API key in the environment variable 'API_KEY' before running this script.
# Example: export API_KEY=sk-admin-REPLACE-WITH-SECURE-KEY
# Or run: API_KEY=sk-admin-REPLACE-WITH-SECURE-KEY python3 tests/manual/manual_test_embed_with_chunking.py
"""Test the /embed endpoint with chunking parameter"""

import os
import requests

url = "http://127.0.0.1:8000/embed"
api_key = os.getenv('API_KEY', 'sk-admin-REPLACE-WITH-SECURE-KEY')
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}"
}

long_text = "Machine learning is transforming the world. " * 50

print("Testing /embed endpoint with chunking parameter\n")
print("=" * 80)

# Test 1: Without chunking (default)
print("\n1. Without chunking (default)")
print("-" * 80)
data = {
    "text": long_text,
    "task_type": "passage",
    "normalize": True,
}
response = requests.post(url, headers=headers, json=data)
if response.status_code == 200:
    result = response.json()
    print(f"✓ Status: {response.status_code}")
    print(f"  Model: {result['model_id']}")
    print(f"  Dimension: {result['dim']}")
    print(f"  Has chunk_count: {'chunk_count' in result}")
    if 'chunk_count' in result:
        print(f"  Chunk count: {result['chunk_count']}")
        print(f"  Aggregation: {result.get('aggregation', 'N/A')}")
else:
    print(f"✗ Error {response.status_code}: {response.text}")

# Test 2: With chunking explicitly enabled
print("\n2. With chunking explicitly enabled")
print("-" * 80)
data = {
    "text": long_text,
    "task_type": "passage",
    "normalize": True,
    "chunking": True,
    "chunk_size": 500,
    "chunk_overlap": 50,
}
response = requests.post(url, headers=headers, json=data)
if response.status_code == 200:
    result = response.json()
    print(f"✓ Status: {response.status_code}")
    print(f"  Chunk count: {result.get('chunk_count', 'N/A')}")
    print(f"  Chunk size setting: 500")
else:
    print(f"✗ Error {response.status_code}: {response.text}")

# Test 3: With chunking disabled
print("\n3. With chunking disabled")
print("-" * 80)
data = {
    "text": long_text,
    "task_type": "passage",
    "normalize": True,
    "chunking": False,
}
response = requests.post(url, headers=headers, json=data)
if response.status_code == 200:
    result = response.json()
    print(f"✓ Status: {response.status_code}")
    print(f"  Model: {result['model_id']}")
    print(f"  Dimension: {result['dim']}")
    print(f"  Has chunk_count: {'chunk_count' in result}")
    if 'chunk_count' not in result:
        print(f"  ✓ Chunking disabled - no chunk metadata")
else:
    print(f"✗ Error {response.status_code}: {response.text}")

# Test 4: Short text with chunking enabled
print("\n4. Short text with chunking enabled (should create 1 chunk)")
print("-" * 80)
data = {
    "text": "This is a short text.",
    "task_type": "passage",
    "normalize": True,
    "chunking": True,
}
response = requests.post(url, headers=headers, json=data)
if response.status_code == 200:
    result = response.json()
    print(f"✓ Status: {response.status_code}")
    print(f"  Chunk count: {result.get('chunk_count', 'N/A')}")
else:
    print(f"✗ Error {response.status_code}: {response.text}")

print("\n" + "=" * 80)
print("Testing complete!")
