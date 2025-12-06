#!/bin/bash
# Example usage of the Vector Database Service
# This script demonstrates the complete workflow: generate embeddings and store/search them

set -e

# Get API key from .env file or use default
if [ -f ".env" ]; then
  API_KEY=$(grep "^API_KEYS=" .env | cut -d'=' -f2 | cut -d',' -f1 | cut -d':' -f2)
else
  API_KEY="sk-admin-your-secret-key"
fi

BASE_URL="http://localhost:8000"
PROJECT="demo_project"
COLLECTION="documents"

echo "🚀 Vector Database Service - Demo Script"
echo "=========================================="
echo ""

# 1. Create a project
echo "📁 Creating project '$PROJECT'..."
curl -s -X POST "$BASE_URL/vdb/projects" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{
    \"project_id\": \"$PROJECT\",
    \"metadata\": {\"description\": \"Demo project for testing\"}
  }" | jq '.'

echo ""

# 2. Create a collection
echo "📚 Creating collection '$COLLECTION'..."
curl -s -X POST "$BASE_URL/vdb/projects/$PROJECT/collections" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{
    \"name\": \"$COLLECTION\",
    \"dimension\": 768,
    \"metric\": \"cosine\",
    \"shards\": 4,
    \"description\": \"Demo document embeddings\"
  }" | jq '.'

echo ""

# 3. Generate and store embeddings for multiple documents
echo "🧠 Generating embeddings and storing documents..."

documents=(
  "Artificial intelligence is transforming the world"
  "Machine learning enables computers to learn from data"
  "Deep neural networks can process complex patterns"
  "Natural language processing helps computers understand text"
  "Computer vision allows machines to interpret images"
)

for i in "${!documents[@]}"; do
  doc="${documents[$i]}"
  doc_id="doc_$(printf "%03d" $i)"
  
  echo "  Processing: $doc_id"
  
  # Generate embedding
  embedding=$(curl -s -X POST "$BASE_URL/embed" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d "{\"text\": \"$doc\", \"normalize\": true}" \
    | jq -c '.embedding')
  
  # Store in VDB
  curl -s -X POST "$BASE_URL/vdb/projects/$PROJECT/collections/$COLLECTION/add" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d "{
      \"id\": \"$doc_id\",
      \"embedding\": $embedding,
      \"metadata\": {
        \"title\": \"Document $i\",
        \"category\": \"ai\"
      },
      \"document\": \"$doc\"
    }" | jq -c '.status' > /dev/null
done

echo ""

# 4. Search for similar documents
echo "🔍 Searching for documents similar to 'What is AI?'..."

# Generate query embedding
query_embedding=$(curl -s -X POST "$BASE_URL/embed" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"text": "What is AI?", "task_type": "query", "normalize": true}' \
  | jq -c '.embedding')

# Search
echo ""
echo "Search results:"
curl -s -X POST "$BASE_URL/vdb/projects/$PROJECT/collections/$COLLECTION/search?include_debug=true" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{\"query_vector\": $query_embedding, \"limit\": 3}" \
  | jq '.data[] | {id, score, document: .metadata.title, text: .document}'

echo ""

# 5. List all collections
echo "📋 Listing all collections in project..."
curl -s -X GET "$BASE_URL/vdb/projects/$PROJECT/collections" \
  -H "Authorization: Bearer $API_KEY" \
  | jq '.'

echo ""
echo "✅ Demo complete!"
echo ""
echo "To clean up:"
echo "  rm -rf ./vdb-data/$PROJECT"
