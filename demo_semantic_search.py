#!/usr/bin/env python3
"""
Demo script for semantic search / similar items feature.
Shows how to search collections using natural language queries.
"""

import requests
import random
from typing import List, Dict

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "sk-admin-m1YHp13elEvafGYLT27H0gmD"
headers = {"Authorization": f"Bearer {API_KEY}"}

def create_sample_data():
    """Create sample product/document data with embeddings."""
    print("="*80)
    print("SETTING UP SAMPLE DATA FOR SEMANTIC SEARCH")
    print("="*80)
    
    project_id = "semantic_search_demo"
    collection = "products"
    
    # Create project
    print(f"\n1. Creating project: {project_id}")
    resp = requests.post(
        f"{BASE_URL}/vdb/projects",
        headers=headers,
        json={"project_id": project_id}
    )
    if resp.status_code in [200, 400]:
        print(f"   ✅ Project ready")
    
    # Create collection
    print(f"\n2. Creating collection: {collection}")
    resp = requests.post(
        f"{BASE_URL}/vdb/projects/{project_id}/collections",
        headers=headers,
        json={"name": collection, "dimension": 768}  # Using actual model dimension
    )
    if resp.status_code in [200, 400]:
        print(f"   ✅ Collection ready")
    
    # Sample product data
    products = [
        {
            "id": "prod-001",
            "name": "Red Running Shoes",
            "text": "Comfortable red running shoes with breathable mesh and cushioned sole",
            "category": "footwear",
            "price": 89.99,
            "color": "red"
        },
        {
            "id": "prod-002",
            "name": "Blue Athletic Sneakers",
            "text": "High-performance blue sneakers for sports and training activities",
            "category": "footwear",
            "price": 79.99,
            "color": "blue"
        },
        {
            "id": "prod-003",
            "name": "Black Casual Shoes",
            "text": "Stylish black casual shoes perfect for everyday wear and office",
            "category": "footwear",
            "price": 69.99,
            "color": "black"
        },
        {
            "id": "prod-004",
            "name": "Yoga Mat",
            "text": "Premium yoga mat with extra cushioning and non-slip surface",
            "category": "fitness",
            "price": 39.99,
            "color": "purple"
        },
        {
            "id": "prod-005",
            "name": "Dumbbell Set",
            "text": "Adjustable dumbbell weight set for home workout and strength training",
            "category": "fitness",
            "price": 149.99,
            "color": "black"
        },
        {
            "id": "prod-006",
            "name": "Running Watch",
            "text": "GPS running watch with heart rate monitor and fitness tracking",
            "category": "electronics",
            "price": 199.99,
            "color": "black"
        },
        {
            "id": "prod-007",
            "name": "White Tennis Shoes",
            "text": "Classic white tennis shoes with excellent court grip and ankle support",
            "category": "footwear",
            "price": 94.99,
            "color": "white"
        },
        {
            "id": "prod-008",
            "name": "Exercise Bike",
            "text": "Stationary exercise bike for cardio workout at home with adjustable resistance",
            "category": "fitness",
            "price": 399.99,
            "color": "gray"
        },
    ]
    
    print(f"\n3. Adding {len(products)} sample products...")
    
    # Generate embeddings for each product and add to collection
    for i, product in enumerate(products):
        # Generate embedding from product text
        embed_resp = requests.post(
            f"{BASE_URL}/embed",
            headers=headers,
            json={"text": product["text"], "task_type": "passage", "normalize": True}
        )
        
        if embed_resp.status_code == 200:
            embedding = embed_resp.json()["embedding"]
            
            # Add to collection with metadata
            add_resp = requests.post(
                f"{BASE_URL}/vdb/projects/{project_id}/collections/{collection}/add",
                headers=headers,
                json={
                    "id": product["id"],
                    "embedding": embedding,
                    "metadata": {
                        "name": product["name"],
                        "category": product["category"],
                        "price": product["price"],
                        "color": product["color"]
                    },
                    "document": product["text"]
                }
            )
            
            if add_resp.status_code == 200:
                print(f"   ✅ Added: {product['name']}")
            else:
                print(f"   ❌ Failed to add: {product['name']}")
        else:
            print(f"   ❌ Failed to generate embedding for: {product['name']}")
    
    print(f"\n✅ Sample data setup complete!")
    return project_id, collection


def demo_semantic_search(project_id: str, collection: str):
    """Demonstrate semantic search with various queries."""
    print("\n" + "="*80)
    print("SEMANTIC SEARCH DEMONSTRATIONS")
    print("="*80)
    
    queries = [
        {
            "query": "shoes for running",
            "description": "Finding running shoes"
        },
        {
            "query": "equipment for home fitness workout",
            "description": "Finding fitness equipment"
        },
        {
            "query": "red footwear",
            "description": "Finding red shoes",
            "metadata_filter": {"color": "red"}
        },
        {
            "query": "sports gear",
            "description": "Finding sports-related items"
        },
    ]
    
    for i, query_config in enumerate(queries, 1):
        print(f"\n{'─'*80}")
        print(f"Query #{i}: \"{query_config['query']}\"")
        print(f"Purpose: {query_config['description']}")
        print(f"{'─'*80}")
        
        # Build request
        request_data = {
            "query": query_config["query"],
            "limit": 5,
            "include_text": True,
            "include_metadata": True,
            "min_score": 0.0  # Show all results
        }
        
        # Add metadata filter if specified
        if "metadata_filter" in query_config:
            request_data["metadata_filter"] = query_config["metadata_filter"]
            print(f"Filter: {query_config['metadata_filter']}")
        
        # Perform semantic search
        resp = requests.post(
            f"{BASE_URL}/vdb/projects/{project_id}/collections/{collection}/similar",
            headers=headers,
            json=request_data
        )
        
        if resp.status_code == 200:
            result = resp.json()
            # Handle both "results" and "data" keys for compatibility
            results = result.get("results", result.get("data", []))
            
            print(f"\nFound {len(results)} similar items:\n")
            
            for j, item in enumerate(results, 1):
                score = item.get("score", 0)
                metadata = item.get("metadata", {})
                text = item.get("text", "")
                
                print(f"  {j}. {metadata.get('name', 'Unknown')} (Score: {score:.3f})")
                print(f"     Category: {metadata.get('category', 'N/A')}")
                print(f"     Price: ${metadata.get('price', 0):.2f}")
                print(f"     Color: {metadata.get('color', 'N/A')}")
                print(f"     Description: {text[:80]}...")
                print()
        else:
            print(f"   ❌ Search failed: {resp.status_code}")
            print(f"   {resp.text}")


def show_comparison():
    """Show comparison between regular search and semantic search."""
    print("\n" + "="*80)
    print("COMPARISON: Regular Search vs Semantic Search")
    print("="*80)
    
    print("""
┌─────────────────────────────────────────────────────────────────────────────┐
│ REGULAR SEARCH (Vector-based)                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Endpoint: POST /vdb/projects/{project}/collections/{collection}/search     │
│                                                                             │
│ Input:                                                                      │
│   • query_vector: [0.123, -0.456, ...] (384-dim vector)                   │
│   • limit: 10                                                              │
│                                                                             │
│ Use Case:                                                                   │
│   • You already have the embedding vector                                  │
│   • Direct vector similarity search                                        │
│   • Lower-level API                                                        │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ SEMANTIC SEARCH (Text-based) ⭐ NEW!                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ Endpoint: POST /vdb/projects/{project}/collections/{collection}/similar    │
│                                                                             │
│ Input:                                                                      │
│   • query: "shoes for running" (natural language text)                     │
│   • limit: 10                                                              │
│   • metadata_filter: {"category": "footwear"} (optional)                  │
│   • min_score: 0.5 (optional)                                              │
│   • include_text: true                                                     │
│   • include_metadata: true                                                 │
│                                                                             │
│ Output (Rich Data):                                                         │
│   • id: "prod-001"                                                         │
│   • score: 0.87                                                            │
│   • metadata: {name, category, price, color, ...}                          │
│   • text: "Comfortable red running shoes..."                              │
│                                                                             │
│ Use Case:                                                                   │
│   • User types text search query                                           │
│   • "Find similar products"                                                │
│   • Natural language queries                                               │
│   • Returns full item data (not just vectors)                              │
│   • Perfect for end-user applications                                      │
└─────────────────────────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    print("\n🔍 Semantic Search Demo")
    print("This shows how to search your collections using natural language!\n")
    
    try:
        # Setup sample data
        project_id, collection = create_sample_data()
        
        # Run semantic search demos
        demo_semantic_search(project_id, collection)
        
        # Show comparison
        show_comparison()
        
        print("\n" + "="*80)
        print("✅ DEMO COMPLETE!")
        print("="*80)
        print(f"\n📚 Try it yourself:")
        print(f"   curl -X POST '{BASE_URL}/vdb/projects/{project_id}/collections/{collection}/similar' \\")
        print(f"     -H 'Authorization: Bearer {API_KEY}' \\")
        print(f"     -H 'Content-Type: application/json' \\")
        print(f"     -d '{{\"query\": \"your search text here\", \"limit\": 5}}'")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
