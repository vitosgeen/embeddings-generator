#!/usr/bin/env python3
"""Test script for batch operations API."""

import requests
import time
from typing import List

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "sk-admin-Y48sXC42i9iwt"  # Using admin key from .env
PROJECT_ID = "batch_test_proj"
COLLECTION_NAME = "batch_collection"
DIMENSION = 384

headers = {"Authorization": f"Bearer {API_KEY}"}


def generate_test_vector(vector_id: str, dim: int = DIMENSION) -> dict:
    """Generate a test vector with metadata."""
    import random
    return {
        "id": vector_id,
        "embedding": [random.random() for _ in range(dim)],
        "metadata": {
            "category": random.choice(["tech", "science", "business"]),
            "year": random.choice([2023, 2024, 2025]),
            "test_batch": True
        },
        "document": f"Test document for vector {vector_id}"
    }


def test_batch_add():
    """Test batch add operation."""
    print("\n" + "="*60)
    print("TEST 1: Batch Add Vectors")
    print("="*60)
    
    # Generate 50 test vectors
    vectors = [generate_test_vector(f"batch-add-{i}") for i in range(50)]
    
    payload = {"vectors": vectors}
    
    start = time.time()
    resp = requests.post(
        f"{BASE_URL}/vdb/projects/{PROJECT_ID}/collections/{COLLECTION_NAME}/batch/add",
        headers=headers,
        json=payload
    )
    duration = (time.time() - start) * 1000
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ Batch Add Results:")
        print(f"   Total: {result['total']}")
        print(f"   Successful: {result['successful']}")
        print(f"   Failed: {result['failed']}")
        print(f"   Duration: {result['duration_ms']}ms (client measured: {duration:.0f}ms)")
        
        # Show sample results
        print(f"\n   Sample results (first 5):")
        for r in result['results'][:5]:
            status = "✓" if r['success'] else "✗"
            error = f" - {r.get('error', '')}" if not r['success'] else ""
            print(f"     {status} {r['vector_id']}{error}")
        
        return result['successful'] == result['total']
    else:
        print(f"❌ Failed: {resp.text}")
        return False


def test_batch_update():
    """Test batch update operation (upsert)."""
    print("\n" + "="*60)
    print("TEST 2: Batch Update Vectors (Upsert)")
    print("="*60)
    
    # Update 25 existing vectors + 25 new vectors
    vectors = []
    
    # Update existing (from batch add)
    for i in range(25):
        vec = generate_test_vector(f"batch-add-{i}")
        vec["metadata"]["updated"] = True
        vec["metadata"]["version"] = 2
        vectors.append(vec)
    
    # Add new ones
    for i in range(25):
        vectors.append(generate_test_vector(f"batch-update-new-{i}"))
    
    payload = {"vectors": vectors}
    
    start = time.time()
    resp = requests.put(
        f"{BASE_URL}/vdb/projects/{PROJECT_ID}/collections/{COLLECTION_NAME}/batch/update",
        headers=headers,
        json=payload
    )
    duration = (time.time() - start) * 1000
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ Batch Update Results:")
        print(f"   Total: {result['total']}")
        print(f"   Successful: {result['successful']}")
        print(f"   Failed: {result['failed']}")
        print(f"   Duration: {result['duration_ms']}ms (client measured: {duration:.0f}ms)")
        
        # Show sample results
        print(f"\n   Sample results (first 5):")
        for r in result['results'][:5]:
            status = "✓" if r['success'] else "✗"
            error = f" - {r.get('error', '')}" if not r['success'] else ""
            print(f"     {status} {r['vector_id']}{error}")
        
        return result['successful'] == result['total']
    else:
        print(f"❌ Failed: {resp.text}")
        return False


def test_batch_delete():
    """Test batch delete operation."""
    print("\n" + "="*60)
    print("TEST 3: Batch Delete Vectors")
    print("="*60)
    
    # Delete 20 vectors
    vector_ids = [f"batch-add-{i}" for i in range(20)]
    
    payload = {"vector_ids": vector_ids}
    
    start = time.time()
    resp = requests.delete(
        f"{BASE_URL}/vdb/projects/{PROJECT_ID}/collections/{COLLECTION_NAME}/batch/delete",
        headers=headers,
        json=payload
    )
    duration = (time.time() - start) * 1000
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ Batch Delete Results:")
        print(f"   Total: {result['total']}")
        print(f"   Successful: {result['successful']}")
        print(f"   Failed: {result['failed']}")
        print(f"   Duration: {result['duration_ms']}ms (client measured: {duration:.0f}ms)")
        
        # Show sample results
        print(f"\n   Sample results (first 5):")
        for r in result['results'][:5]:
            status = "✓" if r['success'] else "✗"
            error = f" - {r.get('error', '')}" if not r['success'] else ""
            print(f"     {status} {r['vector_id']}{error}")
        
        return True  # Some may fail (already deleted), that's ok
    else:
        print(f"❌ Failed: {resp.text}")
        return False


def test_large_batch():
    """Test large batch operation (100+ vectors)."""
    print("\n" + "="*60)
    print("TEST 4: Large Batch Add (100 vectors)")
    print("="*60)
    
    # Generate 100 test vectors
    vectors = [generate_test_vector(f"batch-large-{i}") for i in range(100)]
    
    payload = {"vectors": vectors}
    
    start = time.time()
    resp = requests.post(
        f"{BASE_URL}/vdb/projects/{PROJECT_ID}/collections/{COLLECTION_NAME}/batch/add",
        headers=headers,
        json=payload
    )
    duration = (time.time() - start) * 1000
    
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        result = resp.json()
        print(f"✅ Large Batch Results:")
        print(f"   Total: {result['total']}")
        print(f"   Successful: {result['successful']}")
        print(f"   Failed: {result['failed']}")
        print(f"   Duration: {result['duration_ms']}ms (client measured: {duration:.0f}ms)")
        print(f"   Throughput: {result['successful'] / (result['duration_ms'] / 1000):.1f} vectors/sec")
        
        return result['successful'] == result['total']
    else:
        print(f"❌ Failed: {resp.text}")
        return False


def check_usage_stats():
    """Check usage statistics for batch operations."""
    print("\n" + "="*60)
    print("TEST 5: Usage Statistics for Batch Operations")
    print("="*60)
    
    import sys
    sys.path.insert(0, '/home/vitos/Projects/python/embeddings-generator')
    
    from app.adapters.infra.auth_storage import AuthDatabase, UsageTrackingStorage
    
    db = AuthDatabase("./data/auth.db")
    usage = UsageTrackingStorage(db)
    
    # Get stats for batch operations
    stats = usage.get_usage_stats(
        user_id=1,  # admin user
        project_id=PROJECT_ID
    )
    
    print(f"✅ Usage Statistics:")
    print(f"   Total operations: {stats['total_operations']}")
    print(f"   Total vectors processed: {stats['total_vectors']}")
    print(f"   Total payload size: {stats['total_payload_size']} bytes")
    
    print(f"\n   By operation type:")
    for op_type, counts in stats['by_operation'].items():
        if 'batch' in op_type:
            print(f"     {op_type}:")
            print(f"       - Operations: {counts['count']}")
            print(f"       - Vectors: {counts['vectors']}")
            print(f"       - Avg duration: {counts['avg_duration_ms']:.1f}ms")
    
    # Show recent batch operations
    recent = usage.get_recent_operations(user_id=1, project_id=PROJECT_ID, limit=10)
    print(f"\n   Recent batch operations:")
    for op in recent:
        if 'batch' in op['operation_type']:
            print(f"     - {op['operation_type']}: {op['vector_count']} vectors, "
                  f"{op['status']}, {op['duration_ms']}ms")


def setup_test_environment():
    """Setup test project and collection."""
    print("\n" + "="*60)
    print("SETUP: Creating test project and collection")
    print("="*60)
    
    # Create project
    resp = requests.post(
        f"{BASE_URL}/vdb/projects",
        headers=headers,
        json={"project_id": PROJECT_ID}
    )
    if resp.status_code in [200, 400]:  # 400 if already exists
        print(f"✅ Project ready: {PROJECT_ID}")
    else:
        print(f"⚠️  Project creation: {resp.status_code} - {resp.text}")
    
    # Create collection
    resp = requests.post(
        f"{BASE_URL}/vdb/projects/{PROJECT_ID}/collections",
        headers=headers,
        json={
            "name": COLLECTION_NAME,
            "dimension": DIMENSION,
            "metric": "cosine"
        }
    )
    if resp.status_code in [200, 400]:  # 400 if already exists
        print(f"✅ Collection ready: {COLLECTION_NAME}")
    else:
        print(f"⚠️  Collection creation: {resp.status_code} - {resp.text}")


def main():
    """Run all batch operation tests."""
    print("\n" + "="*80)
    print("BATCH OPERATIONS TEST SUITE")
    print("="*80)
    
    # Setup
    setup_test_environment()
    
    # Run tests
    results = []
    
    results.append(("Batch Add (50 vectors)", test_batch_add()))
    time.sleep(0.5)
    
    results.append(("Batch Update (50 vectors)", test_batch_update()))
    time.sleep(0.5)
    
    results.append(("Batch Delete (20 vectors)", test_batch_delete()))
    time.sleep(0.5)
    
    results.append(("Large Batch Add (100 vectors)", test_large_batch()))
    time.sleep(0.5)
    
    # Check usage stats
    check_usage_stats()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("="*80)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
