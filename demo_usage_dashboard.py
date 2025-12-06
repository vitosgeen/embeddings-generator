#!/usr/bin/env python3
"""
Demo script to populate usage data and display dashboard access info.
"""

import requests
import random
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "sk-admin-m1YHp13elEvafGYLT27H0gmD"
headers = {"Authorization": f"Bearer {API_KEY}"}

def generate_sample_usage():
    """Generate sample usage data by performing various operations."""
    print("="*80)
    print("GENERATING SAMPLE USAGE DATA FOR DASHBOARD")
    print("="*80)
    
    project_id = "usage_demo"
    collection = "demo_vectors"
    
    # Create project
    print(f"\n1. Creating project: {project_id}")
    resp = requests.post(
        f"{BASE_URL}/vdb/projects",
        headers=headers,
        json={"project_id": project_id}
    )
    if resp.status_code in [200, 400]:  # 400 if exists
        print(f"   ✅ Project ready")
    
    # Create collection
    print(f"\n2. Creating collection: {collection}")
    resp = requests.post(
        f"{BASE_URL}/vdb/projects/{project_id}/collections",
        headers=headers,
        json={"name": collection, "dimension": 384}
    )
    if resp.status_code in [200, 400]:
        print(f"   ✅ Collection ready")
    
    # Add various vectors
    print(f"\n3. Adding individual vectors (creates usage records)")
    for i in range(10):
        resp = requests.post(
            f"{BASE_URL}/vdb/projects/{project_id}/collections/{collection}/add",
            headers=headers,
            json={
                "id": f"demo-vec-{i}",
                "embedding": [random.random() for _ in range(384)],
                "metadata": {"type": "demo", "index": i}
            }
        )
        if resp.status_code == 200:
            print(f"   ✅ Added vector {i+1}/10", end="\r")
    print()
    
    # Batch add
    print(f"\n4. Batch adding vectors (50)")
    batch_vectors = [
        {
            "id": f"batch-{i}",
            "embedding": [random.random() for _ in range(384)],
            "metadata": {"type": "batch", "index": i}
        }
        for i in range(50)
    ]
    resp = requests.post(
        f"{BASE_URL}/vdb/projects/{project_id}/collections/{collection}/batch/add",
        headers=headers,
        json={"vectors": batch_vectors}
    )
    if resp.status_code == 200:
        result = resp.json()
        print(f"   ✅ Batch added {result['successful']}/{result['total']} vectors")
    
    # Perform searches
    print(f"\n5. Performing searches (10 queries)")
    for i in range(10):
        query_vector = [random.random() for _ in range(384)]
        resp = requests.post(
            f"{BASE_URL}/vdb/projects/{project_id}/collections/{collection}/search",
            headers=headers,
            json={"query_vector": query_vector, "limit": 5}
        )
        if resp.status_code == 200:
            print(f"   ✅ Search {i+1}/10", end="\r")
    print()
    
    # Update vectors
    print(f"\n6. Updating vectors (batch update)")
    update_vectors = [
        {
            "id": f"demo-vec-{i}",
            "embedding": [random.random() for _ in range(384)],
            "metadata": {"type": "demo", "index": i, "updated": True}
        }
        for i in range(5)
    ]
    resp = requests.put(
        f"{BASE_URL}/vdb/projects/{project_id}/collections/{collection}/batch/update",
        headers=headers,
        json={"vectors": update_vectors}
    )
    if resp.status_code == 200:
        result = resp.json()
        print(f"   ✅ Batch updated {result['successful']}/{result['total']} vectors")
    
    # Delete some vectors
    print(f"\n7. Deleting vectors (batch delete)")
    delete_ids = [f"batch-{i}" for i in range(10)]
    resp = requests.delete(
        f"{BASE_URL}/vdb/projects/{project_id}/collections/{collection}/batch/delete",
        headers=headers,
        json={"vector_ids": delete_ids}
    )
    if resp.status_code == 200:
        result = resp.json()
        print(f"   ✅ Batch deleted {result['successful']}/{result['total']} vectors")
    
    print("\n" + "="*80)
    print("✅ SAMPLE USAGE DATA GENERATED")
    print("="*80)


def display_dashboard_info():
    """Display information about accessing the dashboard."""
    print("\n" + "="*80)
    print("USAGE DASHBOARD ACCESS INFORMATION")
    print("="*80)
    
    print(f"\n📊 Dashboard URL: http://localhost:8000/admin/usage")
    print(f"\n🔑 Authentication Required:")
    print(f"   - Login with admin credentials")
    print(f"   - Or use API key: {API_KEY}")
    
    print(f"\n📈 Dashboard Features:")
    print(f"   ✅ Total operations and vectors")
    print(f"   ✅ Data volume and success rate")
    print(f"   ✅ Operations breakdown chart")
    print(f"   ✅ Top users and projects")
    print(f"   ✅ Quota status with progress bars")
    print(f"   ✅ Recent operations table")
    print(f"   ✅ Time range filter (24h, 7d, 30d, all)")
    
    print(f"\n📊 Current Statistics:")
    
    # Get usage stats via Python API
    import sys
    sys.path.insert(0, '/home/vitos/Projects/python/embeddings-generator')
    from app.adapters.infra.auth_storage import AuthDatabase, UsageTrackingStorage
    
    db = AuthDatabase("./data/auth.db")
    usage = UsageTrackingStorage(db)
    
    stats = usage.get_usage_stats()
    
    print(f"   Total Operations: {stats['total_operations']:,}")
    print(f"   Total Vectors: {stats['total_vectors']:,}")
    print(f"   Total Payload: {stats['total_payload_size'] / 1024 / 1024:.2f} MB")
    
    print(f"\n   By Operation Type:")
    for op_type, counts in stats['by_operation'].items():
        print(f"      {op_type}: {counts['count']} operations, {counts['vectors']} vectors")
    
    print(f"\n🌐 To view the dashboard:")
    print(f"   1. Open browser: http://localhost:8000/admin")
    print(f"   2. Click 'Usage' in navigation")
    print(f"   3. View real-time metrics and charts")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    print("\n🚀 Usage Dashboard Demo")
    print("This script will generate sample data and show dashboard info\n")
    
    try:
        # Generate usage data
        generate_sample_usage()
        
        # Display dashboard access info
        display_dashboard_info()
        
        print("\n✅ Demo complete! Visit http://localhost:8000/admin/usage to see the dashboard")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
