# New Feature: `/embed/chunks` Endpoint

## 📋 Summary

Added a new REST API endpoint `/embed/chunks` that returns individual text chunks with their **full text** and embeddings, designed for detailed analysis, moderation pipelines, and fragment-level processing.

## 🎯 Motivation

The existing `/embed/chunked` endpoint returns:
- An **aggregated** embedding (mean of all chunks)
- Chunk metadata with **text previews** (first 100 characters)

This is perfect for document similarity search, but doesn't provide full chunk text needed for:
- **Moderation pipelines** (toxicity detection per fragment)
- **Fragment-level analysis** (analyzing specific parts of documents)
- **Detailed content processing** (where full chunk text is required)

## 🆕 What's New

### New Endpoint: `POST /embed/chunks`

**Request Format:**
```json
{
  "text": "Long text to split into chunks...",
  "chunk_size": 1000,
  "chunk_overlap": 100,
  "task_type": "passage",
  "normalize": true
}
```

**Response Format:**
```json
{
  "model_id": "BAAI/bge-m3",
  "dim": 1024,
  "chunk_count": 2,
  "chunks": [
    [
      "Full text of first chunk here...",
      [0.123, -0.456, ...],
      1
    ],
    [
      "Full text of second chunk here...",
      [0.789, -0.012, ...],
      2
    ]
  ],
  "requested_by": "admin"
}
```

### Key Differences from `/embed/chunked`

| Feature | `/embed/chunked` | `/embed/chunks` |
|---------|------------------|-----------------|
| **Purpose** | Document similarity search | Detailed analysis, moderation |
| **Aggregated embedding** | ✅ Yes (mean of chunks) | ❌ No |
| **Chunk text** | Preview (first 100 chars) | Full text |
| **Chunk embeddings** | Yes (in metadata) | Yes (in array) |
| **Response format** | Object with chunks array | Array of [text, embedding, number] |
| **Use case** | Save 1 vector for search | Process/analyze each fragment |

## 📝 Changes Made

### 1. API Implementation (`app/adapters/rest/fastapi_app.py`)
- Added new endpoint `POST /embed/chunks`
- Reuses existing `embed_chunked()` business logic
- Calls `_chunk_text()` to get full chunk texts
- Returns simplified format: `[[text, embedding, chunk_num], ...]`
- Validates overlap ratio (max 50% of chunk_size)
- Requires Bearer token authentication

### 2. Tests (`tests/integration/test_rest_api.py`)
- Added 8 comprehensive test cases:
  - `test_embed_chunks_short_text` - Single chunk handling
  - `test_embed_chunks_long_text` - Multiple chunks
  - `test_embed_chunks_full_text_not_preview` - Verifies full text
  - `test_embed_chunks_empty_text` - Empty input validation
  - `test_embed_chunks_whitespace_only` - Whitespace handling
  - `test_embed_chunks_custom_parameters` - Custom chunk settings
  - `test_embed_chunks_excessive_overlap_validation` - Overlap limit
  - `test_embed_chunks_response_format` - Response structure

**Test Results:** ✅ **104 tests passing** (96 original + 8 new)

### 3. Documentation Updates

#### README.md
- Added endpoint to API endpoints table
- Added usage example with curl command
- Added response format examples
- Added comparison table explaining differences

#### templates/index.html
- Added endpoint to API endpoints list
- Added usage example section
- Added response format example
- Added explanatory note about use cases

#### Manual Test
- Created `tests/manual/manual_test_embed_chunks.py`
- Demonstrates endpoint usage
- Compares `/embed/chunked` vs `/embed/chunks`
- Shows verification of response structure

## 🔍 Usage Examples

### For Document Similarity (use `/embed/chunked`)
```bash
curl -X POST http://localhost:8000/embed/chunked \
  -H "Authorization: Bearer sk-admin-key" \
  -d '{"text": "Long document..."}'

# Save the aggregated embedding for similarity search
# Store: embedding vector for cosine similarity
```

### For Moderation Pipeline (use `/embed/chunks`)
```bash
curl -X POST http://localhost:8000/embed/chunks \
  -H "Authorization: Bearer sk-admin-key" \
  -d '{"text": "Long document..."}'

# Process each chunk individually:
# For each chunk: [full_text, embedding, chunk_number]
#   1. Send full_text to moderation API (toxicity detection)
#   2. Use embedding for semantic analysis
#   3. Track chunk_number for reporting
```

## 🧪 Testing

Run all tests:
```bash
.venv/bin/python -m pytest tests/ -v
```

Run only new endpoint tests:
```bash
.venv/bin/python -m pytest tests/ -k "test_embed_chunks" -v
```

Run manual test (requires running service):
```bash
# Terminal 1: Start service
make run

# Terminal 2: Run manual test
.venv/bin/python tests/manual/manual_test_embed_chunks.py
```

## 📊 Test Coverage

All tests passing: **104/104** ✅

New tests added: **8**
- Integration tests: 8
- Manual test script: 1

Coverage areas:
- ✅ Short text (single chunk)
- ✅ Long text (multiple chunks)
- ✅ Full text verification (not previews)
- ✅ Empty/whitespace validation
- ✅ Custom parameters
- ✅ Overlap validation
- ✅ Response structure
- ✅ Authentication

## 🚀 Deployment

No additional deployment steps required. The new endpoint:
- Uses existing infrastructure
- Reuses existing business logic
- Requires same authentication
- No new dependencies

Simply deploy the updated code and the endpoint will be available.

## 💡 Architecture Notes

### Clean Implementation
- **No code duplication**: Reuses `embed_chunked()` and `_chunk_text()`
- **Consistent validation**: Same overlap limits as other endpoints
- **Standard authentication**: Uses existing Bearer token system
- **Same error handling**: Consistent 400/422/401 responses

### Performance Considerations
- Same performance as `/embed/chunked` (identical processing)
- Returns more data (full text vs previews)
- Slightly larger response size (~10-20% more)
- No additional compute cost

## 🎓 When to Use Each Endpoint

### Use `/embed` (no chunking)
✅ Short texts (< model limit)  
✅ Single embedding per text  
✅ No chunk metadata needed

### Use `/embed/chunked` (aggregated)
✅ Long texts (> model limit)  
✅ Document-level similarity search  
✅ Save 1 embedding per document  
✅ Chunk previews sufficient

### Use `/embed/chunks` (individual)
✅ Long texts (> model limit)  
✅ Fragment-level analysis  
✅ Moderation pipelines  
✅ Need full chunk text  
✅ Process each chunk separately

## 📚 Related Documentation

- Main README: `/README.md`
- API Documentation: `http://localhost:8000/docs`
- Web Interface: `http://localhost:8000/`
- Manual Test: `/tests/manual/manual_test_embed_chunks.py`

## ✅ Checklist

- [x] Endpoint implemented
- [x] Tests added (8 new tests)
- [x] All tests passing (104/104)
- [x] README updated
- [x] HTML documentation updated
- [x] Manual test script created
- [x] Authentication working
- [x] Validation working (overlap limits)
- [x] Error handling consistent
- [x] Response format documented

## 🎉 Status

**READY FOR PRODUCTION** ✅

All implementation, testing, and documentation complete.
