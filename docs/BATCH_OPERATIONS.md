# Batch Operations API Documentation

## Overview

Batch operations allow you to add, update, or delete multiple vectors in a single API request. This is significantly more efficient than making individual requests for each vector, especially for bulk data operations.

**Key Benefits:**
- **Performance**: Process up to 1000 vectors per request
- **Efficiency**: Reduced network overhead and latency
- **Tracking**: Individual success/failure status for each vector
- **Quota Management**: Pre-operation quota validation
- **Resilience**: Partial success handling - continues even if some vectors fail

## API Endpoints

### 1. Batch Add Vectors

Add multiple vectors to a collection in one request.

```
POST /vdb/projects/{project_id}/collections/{collection}/batch/add
```

**Request Body:**
```json
{
  "vectors": [
    {
      "id": "vec-1",
      "embedding": [0.1, 0.2, ...],
      "metadata": {"category": "tech", "year": 2024},
      "document": "Optional text document"
    },
    {
      "id": "vec-2",
      "embedding": [0.3, 0.4, ...],
      "metadata": {"category": "science"},
      "document": null
    }
  ]
}
```

**Response:**
```json
{
  "total": 2,
  "successful": 2,
  "failed": 0,
  "duration_ms": 450,
  "results": [
    {"success": true, "vector_id": "vec-1"},
    {"success": true, "vector_id": "vec-2"}
  ]
}
```

**Features:**
- Accepts 1-1000 vectors per request
- Quota enforcement before processing
- Each vector processed independently
- Returns detailed results for each vector

### 2. Batch Update Vectors (Upsert)

Update existing vectors or insert new ones in bulk.

```
PUT /vdb/projects/{project_id}/collections/{collection}/batch/update
```

**Request Body:**
```json
{
  "vectors": [
    {
      "id": "vec-1",
      "embedding": [0.5, 0.6, ...],
      "metadata": {"category": "tech", "updated": true},
      "document": "Updated document"
    }
  ]
}
```

**Response:**
```json
{
  "total": 1,
  "successful": 1,
  "failed": 0,
  "duration_ms": 250,
  "results": [
    {"success": true, "vector_id": "vec-1"}
  ]
}
```

**Upsert Semantics:**
- If vector exists: Deletes old version, adds new version (update)
- If vector doesn't exist: Adds new vector (insert)
- Usage metadata tracks count of updates vs inserts

### 3. Batch Delete Vectors

Delete multiple vectors by their IDs.

```
DELETE /vdb/projects/{project_id}/collections/{collection}/batch/delete
```

**Request Body:**
```json
{
  "vector_ids": ["vec-1", "vec-2", "vec-3"]
}
```

**Response:**
```json
{
  "total": 3,
  "successful": 2,
  "failed": 1,
  "duration_ms": 180,
  "results": [
    {"success": true, "vector_id": "vec-1"},
    {"success": true, "vector_id": "vec-2"},
    {"success": false, "vector_id": "vec-3", "error": "Vector not found"}
  ]
}
```

**Features:**
- Deletes 1-1000 vectors per request
- Continues even if some deletions fail (e.g., vector doesn't exist)
- Returns detailed results for each deletion attempt

## Request Models

### BatchVectorItem
```python
{
  "id": str,                              # Required: Unique vector identifier
  "embedding": List[float],               # Required: Vector embedding
  "metadata": Optional[Dict[str, Any]],   # Optional: Metadata dictionary
  "document": Optional[str]               # Optional: Raw text document
}
```

### BatchAddRequest
```python
{
  "vectors": List[BatchVectorItem]  # 1-1000 vectors
}
```

### BatchUpdateRequest
```python
{
  "vectors": List[BatchVectorItem]  # 1-1000 vectors
}
```

### BatchDeleteRequest
```python
{
  "vector_ids": List[str]  # 1-1000 vector IDs
}
```

## Response Model

### BatchOperationResponse
```python
{
  "total": int,                           # Total number of vectors processed
  "successful": int,                      # Number of successful operations
  "failed": int,                          # Number of failed operations
  "duration_ms": int,                     # Total operation duration in milliseconds
  "results": List[BatchOperationResult]   # Detailed results for each vector
}
```

### BatchOperationResult
```python
{
  "success": bool,                # Whether this specific operation succeeded
  "vector_id": str,               # The vector ID
  "error": Optional[str]          # Error message if failed (null if successful)
}
```

## Usage Examples

### Python Example

```python
import requests

api_key = "your-api-key"
base_url = "http://localhost:8000"
headers = {"Authorization": f"Bearer {api_key}"}

# 1. Batch Add
vectors = [
    {
        "id": f"doc-{i}",
        "embedding": [0.1] * 384,  # Your actual embeddings
        "metadata": {"source": "batch-import", "index": i},
        "document": f"Document {i} content"
    }
    for i in range(100)
]

response = requests.post(
    f"{base_url}/vdb/projects/my-project/collections/docs/batch/add",
    headers=headers,
    json={"vectors": vectors}
)

result = response.json()
print(f"Added {result['successful']}/{result['total']} vectors")
print(f"Duration: {result['duration_ms']}ms")

# 2. Batch Update
updates = [
    {
        "id": f"doc-{i}",
        "embedding": [0.2] * 384,  # Updated embeddings
        "metadata": {"source": "batch-update", "version": 2}
    }
    for i in range(50)
]

response = requests.put(
    f"{base_url}/vdb/projects/my-project/collections/docs/batch/update",
    headers=headers,
    json={"vectors": updates}
)

# 3. Batch Delete
vector_ids = [f"doc-{i}" for i in range(10, 30)]

response = requests.delete(
    f"{base_url}/vdb/projects/my-project/collections/docs/batch/delete",
    headers=headers,
    json={"vector_ids": vector_ids}
)
```

### cURL Examples

```bash
# Batch Add
curl -X POST http://localhost:8000/vdb/projects/my-proj/collections/docs/batch/add \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [
      {
        "id": "vec-1",
        "embedding": [0.1, 0.2, 0.3],
        "metadata": {"category": "test"}
      }
    ]
  }'

# Batch Update
curl -X PUT http://localhost:8000/vdb/projects/my-proj/collections/docs/batch/update \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": [
      {
        "id": "vec-1",
        "embedding": [0.4, 0.5, 0.6],
        "metadata": {"category": "updated"}
      }
    ]
  }'

# Batch Delete
curl -X DELETE http://localhost:8000/vdb/projects/my-proj/collections/docs/batch/delete \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "vector_ids": ["vec-1", "vec-2", "vec-3"]
  }'
```

## Usage Tracking

All batch operations are tracked in the usage database with detailed metrics:

### Tracked Metrics
- **operation_type**: `"batch_add_vector"`, `"batch_update_vector"`, or `"batch_delete_vector"`
- **vector_count**: Total number of vectors in the batch
- **payload_size**: Total size of all embeddings
- **duration_ms**: Time taken for the entire batch operation
- **status**: `"success"` (all succeeded) or `"partial_failure"` (some failed)
- **metadata**: Additional details
  - `total`: Total vectors processed
  - `successful`: Number of successful operations
  - `failed`: Number of failed operations
  - `updates`: (batch_update only) Number of updates
  - `inserts`: (batch_update only) Number of inserts

### Query Usage Stats

```python
from app.adapters.infra.auth_storage import AuthDatabase, UsageTrackingStorage

db = AuthDatabase("./data/auth.db")
usage = UsageTrackingStorage(db)

stats = usage.get_usage_stats(
    user_id=1,
    project_id="my-project"
)

# View batch operation statistics
for op_type, counts in stats['by_operation'].items():
    if 'batch' in op_type:
        print(f"{op_type}:")
        print(f"  Operations: {counts['count']}")
        print(f"  Vectors: {counts['vectors']}")
        print(f"  Avg duration: {counts['avg_duration_ms']:.1f}ms")
```

## Quota Management

### Pre-Operation Quota Check

Before processing a batch, the system checks if the user/project has sufficient quota:

```python
# Quota check happens automatically before batch operations
# If quota exceeded, returns 429 Too Many Requests with reason
```

**Enforced Quotas:**
- `max_vectors_per_project`: Total vector limit for the project
- `max_searches_per_day`: Daily search limit (not applicable to batch add/update/delete)
- `max_operations_per_minute`: Rate limiting
- `max_operations_per_hour`: Rate limiting

### Quota Exceeded Response

```json
{
  "detail": "Quota exceeded: Maximum vectors per project limit reached (10000/10000)",
  "status_code": 429
}
```

The failed operation is still recorded in usage tracking with `status="quota_exceeded"`.

## Error Handling

### Individual Vector Failures

Batch operations continue processing even if some vectors fail:

```json
{
  "total": 5,
  "successful": 3,
  "failed": 2,
  "results": [
    {"success": true, "vector_id": "vec-1"},
    {"success": true, "vector_id": "vec-2"},
    {"success": false, "vector_id": "vec-3", "error": "Dimension mismatch: expected 384, got 256"},
    {"success": true, "vector_id": "vec-4"},
    {"success": false, "vector_id": "vec-5", "error": "Invalid metadata format"}
  ]
}
```

### Common Error Types

1. **Dimension Mismatch**: Embedding dimension doesn't match collection dimension
2. **Invalid Metadata**: Metadata cannot be serialized
3. **Duplicate ID**: Vector ID already exists (batch add only)
4. **Vector Not Found**: Vector doesn't exist (batch delete)
5. **Invalid Vector ID**: Malformed vector identifier

### HTTP Status Codes

- **200 OK**: Batch operation completed (check `results` for individual failures)
- **400 Bad Request**: Invalid request format or parameters
- **401 Unauthorized**: Invalid or expired API key
- **403 Forbidden**: Insufficient permissions for project
- **429 Too Many Requests**: Quota exceeded
- **500 Internal Server Error**: Unexpected server error

## Performance Characteristics

### Throughput

Typical performance on modern hardware:

- **Batch Add**: 50-200 vectors/second (depends on embedding dimension)
- **Batch Update**: 40-150 vectors/second (includes delete + add)
- **Batch Delete**: 200-500 vectors/second

### Optimization Tips

1. **Batch Size**: Use batches of 100-500 vectors for optimal performance
2. **Parallel Requests**: Can send multiple batch requests in parallel
3. **Metadata Size**: Keep metadata small (< 1KB per vector) for better performance
4. **Network**: Use persistent connections for multiple batch requests

### Comparison: Batch vs Individual

Adding 1000 vectors:

| Method | Requests | Duration | Throughput |
|--------|----------|----------|------------|
| Individual | 1000 | ~60s | 16 vec/s |
| Batch (100) | 10 | ~8s | 125 vec/s |
| Batch (500) | 2 | ~6s | 167 vec/s |

**Batch operations are 8-10x faster** for bulk data operations.

## Best Practices

### 1. Choose Appropriate Batch Sizes
```python
# Good: Manageable batches
batch_size = 200
for i in range(0, len(vectors), batch_size):
    batch = vectors[i:i+batch_size]
    response = add_batch(batch)
    
# Avoid: Too small (inefficient)
batch_size = 10  # Too many requests

# Avoid: Too large (long request time, risk of timeout)
batch_size = 1000  # Maximum, but may be slow
```

### 2. Handle Partial Failures
```python
response = add_batch(vectors)
if response['failed'] > 0:
    # Retry failed vectors
    failed_ids = [r['vector_id'] for r in response['results'] if not r['success']]
    failed_vectors = [v for v in vectors if v['id'] in failed_ids]
    
    # Retry with exponential backoff
    retry_batch(failed_vectors)
```

### 3. Monitor Usage
```python
# Check usage before large batch operations
stats = usage.get_usage_stats(user_id, project_id)
current_vectors = stats['total_vectors']
quota = quota_storage.get_quota(user_id, project_id)

if current_vectors + len(batch) > quota['max_vectors_per_project']:
    print("Warning: Batch will exceed quota")
```

### 4. Use Batch Update for Replacements
```python
# Good: Use batch update to replace embeddings
updated_vectors = [
    {"id": old_id, "embedding": new_embedding, ...}
    for old_id, new_embedding in updates
]
batch_update(updated_vectors)

# Avoid: Delete then add separately (less efficient)
batch_delete([v['id'] for v in vectors])
batch_add(vectors)
```

### 5. Validate Before Batching
```python
# Validate dimension before sending
collection_dim = 384
valid_vectors = [
    v for v in vectors 
    if len(v['embedding']) == collection_dim
]

if len(valid_vectors) < len(vectors):
    print(f"Warning: {len(vectors) - len(valid_vectors)} vectors have wrong dimension")

response = add_batch(valid_vectors)
```

## Troubleshooting

### Problem: All vectors failing with dimension mismatch

**Solution**: Check collection dimension and ensure all embeddings match
```python
collection_info = get_collection(project_id, collection_name)
required_dim = collection_info['dimension']

# Verify all vectors
for v in vectors:
    assert len(v['embedding']) == required_dim
```

### Problem: Quota exceeded on large batches

**Solution**: Split into smaller batches or request quota increase
```python
# Check quota before batch
quota = get_quota(user_id, project_id)
available = quota['max_vectors_per_project'] - current_count

if len(vectors) > available:
    # Process only what fits
    vectors = vectors[:available]
```

### Problem: Slow batch operations

**Solution**: Optimize batch size and use parallel requests
```python
from concurrent.futures import ThreadPoolExecutor

def process_batch(batch):
    return add_batch(batch)

# Process multiple batches in parallel
batch_size = 200
batches = [vectors[i:i+batch_size] for i in range(0, len(vectors), batch_size)]

with ThreadPoolExecutor(max_workers=4) as executor:
    results = list(executor.map(process_batch, batches))
```

## Limits and Constraints

- **Maximum vectors per batch**: 1000
- **Minimum vectors per batch**: 1
- **Maximum embedding dimension**: 2048 (configurable per collection)
- **Maximum metadata size per vector**: 10KB (recommended < 1KB)
- **Maximum document size per vector**: 1MB
- **Request timeout**: 60 seconds (configurable)
- **Maximum concurrent batch requests**: Based on server capacity

## Migration from Individual Operations

If you're currently using individual operations, migrating to batch operations is straightforward:

### Before (Individual Operations)
```python
for vector in vectors:
    response = requests.post(
        f"{base_url}/vdb/projects/{project}/collections/{coll}/add",
        headers=headers,
        json=vector
    )
```

### After (Batch Operations)
```python
# Process in batches of 200
batch_size = 200
for i in range(0, len(vectors), batch_size):
    batch = vectors[i:i+batch_size]
    response = requests.post(
        f"{base_url}/vdb/projects/{project}/collections/{coll}/batch/add",
        headers=headers,
        json={"vectors": batch}
    )
```

**Benefits**: 8-10x faster, reduced network overhead, better error tracking.

## Summary

Batch operations provide a powerful and efficient way to manage large numbers of vectors:

✅ **3 endpoints**: batch add, batch update, batch delete  
✅ **Up to 1000 vectors per request**  
✅ **Individual result tracking**  
✅ **Quota enforcement**  
✅ **Usage tracking**  
✅ **Partial failure handling**  
✅ **8-10x performance improvement**

For bulk data operations, batch APIs are the recommended approach over individual vector operations.
