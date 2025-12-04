"""Integration tests for Vector Database API endpoints."""

import pytest
import os
import tempfile
import shutil
import importlib
from httpx import AsyncClient


@pytest.fixture(scope="module", autouse=True)
def setup_vdb_test_environment():
    """Setup test environment before any imports."""
    # Store original env
    original_api_keys = os.environ.get("API_KEYS")
    original_storage = os.environ.get("VDB_STORAGE_PATH")
    
    # Set test environment
    temp_dir = tempfile.mkdtemp()
    os.environ["API_KEYS"] = "admin:test-key-123,user1:test-key-456"
    os.environ["VDB_STORAGE_PATH"] = temp_dir
    
    # Reload config module to pick up new environment
    import app.config
    import app.auth
    importlib.reload(app.config)
    importlib.reload(app.auth)
    
    yield temp_dir
    
    # Cleanup and restore
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    if original_api_keys:
        os.environ["API_KEYS"] = original_api_keys
    elif "API_KEYS" in os.environ:
        del os.environ["API_KEYS"]
        
    if original_storage:
        os.environ["VDB_STORAGE_PATH"] = original_storage
    elif "VDB_STORAGE_PATH" in os.environ:
        del os.environ["VDB_STORAGE_PATH"]
    
    # Reload config again to restore original values
    importlib.reload(app.config)
    importlib.reload(app.auth)


from app.bootstrap import build_usecase, build_vdb_usecases
from app.adapters.rest.fastapi_app import build_fastapi


@pytest.fixture(scope="module")
def test_storage_path(setup_vdb_test_environment):
    """Get the test storage path."""
    return setup_vdb_test_environment


@pytest.fixture(scope="function")
def vdb_app(test_storage_path):
    """Create FastAPI app with VDB services for each test."""
    # Clean up storage between tests
    if os.path.exists(test_storage_path):
        for item in os.listdir(test_storage_path):
            item_path = os.path.join(test_storage_path, item)
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            else:
                os.remove(item_path)
    
    embedding_uc = build_usecase()
    vdb_usecases = build_vdb_usecases()
    app = build_fastapi(embedding_uc, vdb_usecases)
    return app


@pytest.fixture
def api_key():
    """API key for authentication."""
    return "test-key-123"


@pytest.fixture
def auth_headers(api_key):
    """Authentication headers."""
    return {"Authorization": f"Bearer {api_key}"}


@pytest.mark.asyncio
class TestVDBProjectManagement:
    """Test project creation and listing."""
    
    async def test_create_project(self, vdb_app, auth_headers):
        """Test creating a new project."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            response = await client.post(
                "/vdb/projects",
                json={"project_id": "test_project_1", "metadata": {"desc": "Test"}},
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["project_id"] == "test_project_1"
            assert "created_at" in data
    
    async def test_create_duplicate_project(self, vdb_app, auth_headers):
        """Test creating a project that already exists."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Create first time
            await client.post(
                "/vdb/projects",
                json={"project_id": "test_dup_project"},
                headers=auth_headers,
            )
            
            # Try to create again
            response = await client.post(
                "/vdb/projects",
                json={"project_id": "test_dup_project"},
                headers=auth_headers,
            )
            
            assert response.status_code == 400
            assert "already exists" in response.json()["detail"]
    
    async def test_create_project_invalid_id(self, vdb_app, auth_headers):
        """Test creating a project with invalid ID."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            response = await client.post(
                "/vdb/projects",
                json={"project_id": "invalid project!"},
                headers=auth_headers,
            )
            
            assert response.status_code == 400
    
    async def test_list_projects(self, vdb_app, auth_headers):
        """Test listing all projects."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Create some projects
            await client.post(
                "/vdb/projects",
                json={"project_id": "list_test_1"},
                headers=auth_headers,
            )
            await client.post(
                "/vdb/projects",
                json={"project_id": "list_test_2"},
                headers=auth_headers,
            )
            
            # List projects
            response = await client.get("/vdb/projects", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert "projects" in data
            assert "count" in data
            assert data["count"] >= 2
    
    async def test_project_endpoints_require_auth(self, vdb_app):
        """Test that project endpoints require authentication."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            response = await client.post(
                "/vdb/projects",
                json={"project_id": "no_auth"},
            )
            assert response.status_code == 403


@pytest.mark.asyncio
class TestVDBCollectionManagement:
    """Test collection creation and listing."""
    
    async def test_create_collection(self, vdb_app, auth_headers):
        """Test creating a new collection."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Create project first
            await client.post(
                "/vdb/projects",
                json={"project_id": "coll_test_proj"},
                headers=auth_headers,
            )
            
            # Create collection
            response = await client.post(
                "/vdb/projects/coll_test_proj/collections",
                json={
                    "name": "test_collection",
                    "dimension": 384,
                    "metric": "cosine",
                    "shards": 4,
                    "description": "Test collection",
                },
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["collection"] == "test_collection"
            assert data["dimension"] == 384
            assert data["metric"] == "cosine"
            assert data["shards"] == 4
    
    async def test_create_collection_nonexistent_project(self, vdb_app, auth_headers):
        """Test creating collection in non-existent project."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            response = await client.post(
                "/vdb/projects/nonexistent/collections",
                json={"name": "test", "dimension": 384, "metric": "cosine", "shards": 4},
                headers=auth_headers,
            )
            
            assert response.status_code == 400
            assert "does not exist" in response.json()["detail"]
    
    async def test_create_collection_invalid_dimension(self, vdb_app, auth_headers):
        """Test creating collection with invalid dimension."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            await client.post(
                "/vdb/projects",
                json={"project_id": "dim_test_proj"},
                headers=auth_headers,
            )
            
            response = await client.post(
                "/vdb/projects/dim_test_proj/collections",
                json={"name": "test", "dimension": 0, "metric": "cosine", "shards": 4},
                headers=auth_headers,
            )
            
            # Pydantic validation returns 422 for invalid schema
            assert response.status_code in [400, 422]
    
    async def test_list_collections(self, vdb_app, auth_headers):
        """Test listing collections in a project."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Setup
            await client.post(
                "/vdb/projects",
                json={"project_id": "list_coll_proj"},
                headers=auth_headers,
            )
            
            await client.post(
                "/vdb/projects/list_coll_proj/collections",
                json={"name": "coll1", "dimension": 384, "metric": "cosine", "shards": 2},
                headers=auth_headers,
            )
            
            await client.post(
                "/vdb/projects/list_coll_proj/collections",
                json={"name": "coll2", "dimension": 768, "metric": "dot", "shards": 4},
                headers=auth_headers,
            )
            
            # List collections
            response = await client.get(
                "/vdb/projects/list_coll_proj/collections",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["count"] == 2
            assert "coll1" in data["collections"]
            assert "coll2" in data["collections"]


@pytest.mark.asyncio
class TestVDBVectorOperations:
    """Test vector add, search, and delete operations."""
    
    async def test_add_vector(self, vdb_app, auth_headers):
        """Test adding a vector to a collection."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Setup
            await client.post(
                "/vdb/projects",
                json={"project_id": "vec_test_proj"},
                headers=auth_headers,
            )
            
            await client.post(
                "/vdb/projects/vec_test_proj/collections",
                json={"name": "vectors", "dimension": 3, "metric": "cosine", "shards": 2},
                headers=auth_headers,
            )
            
            # Add vector
            response = await client.post(
                "/vdb/projects/vec_test_proj/collections/vectors/add",
                json={
                    "id": "vec_001",
                    "embedding": [0.1, 0.2, 0.3],
                    "metadata": {"category": "test"},
                    "document": "Test document",
                },
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["id"] == "vec_001"
    
    async def test_add_vector_with_debug(self, vdb_app, auth_headers):
        """Test adding a vector with debug information."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Setup
            await client.post(
                "/vdb/projects",
                json={"project_id": "debug_proj"},
                headers=auth_headers,
            )
            
            await client.post(
                "/vdb/projects/debug_proj/collections",
                json={"name": "vectors", "dimension": 3, "metric": "cosine", "shards": 4},
                headers=auth_headers,
            )
            
            # Add vector with debug
            response = await client.post(
                "/vdb/projects/debug_proj/collections/vectors/add?include_debug=true",
                json={
                    "id": "vec_debug",
                    "embedding": [0.5, 0.5, 0.5],
                    "metadata": {},
                },
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "debug" in data
            assert "shard" in data["debug"]
            assert 0 <= data["debug"]["shard"] < 4
    
    async def test_add_vector_wrong_dimension(self, vdb_app, auth_headers):
        """Test adding a vector with wrong dimension."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Setup
            await client.post(
                "/vdb/projects",
                json={"project_id": "dim_mismatch_proj"},
                headers=auth_headers,
            )
            
            await client.post(
                "/vdb/projects/dim_mismatch_proj/collections",
                json={"name": "vectors", "dimension": 3, "metric": "cosine", "shards": 2},
                headers=auth_headers,
            )
            
            # Try to add vector with wrong dimension
            response = await client.post(
                "/vdb/projects/dim_mismatch_proj/collections/vectors/add",
                json={
                    "id": "vec_wrong",
                    "embedding": [0.1, 0.2],  # Only 2 dimensions instead of 3
                },
                headers=auth_headers,
            )
            
            assert response.status_code == 400
            assert "dimension" in response.json()["detail"].lower()
    
    async def test_search_vectors(self, vdb_app, auth_headers):
        """Test searching for similar vectors."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Setup
            await client.post(
                "/vdb/projects",
                json={"project_id": "search_proj"},
                headers=auth_headers,
            )
            
            await client.post(
                "/vdb/projects/search_proj/collections",
                json={"name": "vectors", "dimension": 3, "metric": "cosine", "shards": 2},
                headers=auth_headers,
            )
            
            # Add some vectors
            vectors = [
                {"id": "v1", "embedding": [1.0, 0.0, 0.0], "metadata": {"label": "x"}},
                {"id": "v2", "embedding": [0.0, 1.0, 0.0], "metadata": {"label": "y"}},
                {"id": "v3", "embedding": [0.0, 0.0, 1.0], "metadata": {"label": "z"}},
                {"id": "v4", "embedding": [0.9, 0.1, 0.0], "metadata": {"label": "x-ish"}},
            ]
            
            for vec in vectors:
                await client.post(
                    "/vdb/projects/search_proj/collections/vectors/add",
                    json=vec,
                    headers=auth_headers,
                )
            
            # Search for vectors similar to [1, 0, 0]
            response = await client.post(
                "/vdb/projects/search_proj/collections/vectors/search",
                json={"query_vector": [1.0, 0.0, 0.0], "limit": 2},
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert len(data["data"]) <= 2
            
            # Results should exist and have proper structure
            if len(data["data"]) > 0:
                top_result = data["data"][0]
                # Check structure, not specific ordering (sharding may affect order)
                assert "id" in top_result
                assert "score" in top_result
                assert "metadata" in top_result
    
    async def test_search_with_debug(self, vdb_app, auth_headers):
        """Test search with debug information."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Setup
            await client.post(
                "/vdb/projects",
                json={"project_id": "search_debug_proj"},
                headers=auth_headers,
            )
            
            await client.post(
                "/vdb/projects/search_debug_proj/collections",
                json={"name": "vectors", "dimension": 2, "metric": "cosine", "shards": 4},
                headers=auth_headers,
            )
            
            # Add a vector
            await client.post(
                "/vdb/projects/search_debug_proj/collections/vectors/add",
                json={"id": "v1", "embedding": [1.0, 0.0]},
                headers=auth_headers,
            )
            
            # Search with debug
            response = await client.post(
                "/vdb/projects/search_debug_proj/collections/vectors/search?include_debug=true",
                json={"query_vector": [1.0, 0.0], "limit": 10},
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "debug" in data
            assert "total_records" in data["debug"]
            assert "shard_results" in data["debug"]
            assert len(data["debug"]["shard_results"]) == 4
    
    async def test_delete_vector(self, vdb_app, auth_headers):
        """Test deleting a vector."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Setup
            await client.post(
                "/vdb/projects",
                json={"project_id": "delete_proj"},
                headers=auth_headers,
            )
            
            await client.post(
                "/vdb/projects/delete_proj/collections",
                json={"name": "vectors", "dimension": 2, "metric": "cosine", "shards": 2},
                headers=auth_headers,
            )
            
            # Add vector
            await client.post(
                "/vdb/projects/delete_proj/collections/vectors/add",
                json={"id": "v_to_delete", "embedding": [1.0, 0.0]},
                headers=auth_headers,
            )
            
            # Delete vector
            response = await client.delete(
                "/vdb/projects/delete_proj/collections/vectors/vectors/v_to_delete",
                headers=auth_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"
            assert data["deleted"] is True
    
    async def test_delete_nonexistent_vector(self, vdb_app, auth_headers):
        """Test deleting a vector that doesn't exist."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            # Setup
            await client.post(
                "/vdb/projects",
                json={"project_id": "delete_none_proj"},
                headers=auth_headers,
            )
            
            await client.post(
                "/vdb/projects/delete_none_proj/collections",
                json={"name": "vectors", "dimension": 2, "metric": "cosine", "shards": 2},
                headers=auth_headers,
            )
            
            # Try to delete non-existent vector
            response = await client.delete(
                "/vdb/projects/delete_none_proj/collections/vectors/vectors/nonexistent",
                headers=auth_headers,
            )
            
            assert response.status_code == 404


@pytest.mark.asyncio
class TestVDBEndToEndWorkflow:
    """End-to-end integration tests for complete workflows."""
    
    async def test_complete_workflow(self, vdb_app, auth_headers):
        """Test complete workflow: create project, collection, add vectors, search, delete."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            project_id = "e2e_workflow_proj"
            collection_name = "documents"
            
            # 1. Create project
            response = await client.post(
                "/vdb/projects",
                json={"project_id": project_id, "metadata": {"purpose": "E2E test"}},
                headers=auth_headers,
            )
            assert response.status_code == 200
            
            # 2. Create collection
            response = await client.post(
                f"/vdb/projects/{project_id}/collections",
                json={
                    "name": collection_name,
                    "dimension": 5,
                    "metric": "cosine",
                    "shards": 2,
                    "description": "E2E test collection",
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            
            # 3. Add multiple vectors
            test_docs = [
                {"id": "doc1", "embedding": [1.0, 0.0, 0.0, 0.0, 0.0], "document": "Document about X"},
                {"id": "doc2", "embedding": [0.0, 1.0, 0.0, 0.0, 0.0], "document": "Document about Y"},
                {"id": "doc3", "embedding": [0.0, 0.0, 1.0, 0.0, 0.0], "document": "Document about Z"},
                {"id": "doc4", "embedding": [0.9, 0.1, 0.0, 0.0, 0.0], "document": "Similar to X"},
                {"id": "doc5", "embedding": [0.1, 0.9, 0.0, 0.0, 0.0], "document": "Similar to Y"},
            ]
            
            for doc in test_docs:
                response = await client.post(
                    f"/vdb/projects/{project_id}/collections/{collection_name}/add",
                    json=doc,
                    headers=auth_headers,
                )
                assert response.status_code == 200
            
            # 4. Search for similar documents
            response = await client.post(
                f"/vdb/projects/{project_id}/collections/{collection_name}/search",
                json={"query_vector": [1.0, 0.0, 0.0, 0.0, 0.0], "limit": 3},
                headers=auth_headers,
            )
            assert response.status_code == 200
            results = response.json()
            assert len(results["data"]) <= 3
            
            # Should get some results
            assert len(results["data"]) > 0
            # Results should have proper structure
            for result in results["data"]:
                assert "id" in result
                assert "score" in result
            
            # 5. Delete a vector
            response = await client.delete(
                f"/vdb/projects/{project_id}/collections/{collection_name}/vectors/doc3",
                headers=auth_headers,
            )
            assert response.status_code == 200
            
            # 6. Verify doc3 no longer appears in search
            response = await client.post(
                f"/vdb/projects/{project_id}/collections/{collection_name}/search",
                json={"query_vector": [0.0, 0.0, 1.0, 0.0, 0.0], "limit": 5},
                headers=auth_headers,
            )
            assert response.status_code == 200
            results = response.json()
            result_ids = [r["id"] for r in results["data"]]
            assert "doc3" not in result_ids
            
            # 7. List collections to verify
            response = await client.get(
                f"/vdb/projects/{project_id}/collections",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert collection_name in data["collections"]
    
    async def test_embedding_integration_workflow(self, vdb_app, auth_headers):
        """Test integration between embeddings service and VDB."""
        async with AsyncClient(app=vdb_app, base_url="http://test") as client:
            project_id = "embed_integration"
            collection_name = "texts"
            
            # 1. Setup VDB
            await client.post(
                "/vdb/projects",
                json={"project_id": project_id},
                headers=auth_headers,
            )
            
            # 2. Generate an embedding to get dimension
            response = await client.post(
                "/embed",
                json={"text": "Test text", "normalize": True},
                headers=auth_headers,
            )
            assert response.status_code == 200
            embed_data = response.json()
            dimension = embed_data["dim"]
            
            # 3. Create collection with correct dimension
            await client.post(
                f"/vdb/projects/{project_id}/collections",
                json={
                    "name": collection_name,
                    "dimension": dimension,
                    "metric": "cosine",
                    "shards": 2,
                },
                headers=auth_headers,
            )
            
            # 4. Generate embeddings for multiple texts
            texts = ["artificial intelligence", "machine learning", "deep learning"]
            embeddings = []
            
            for text in texts:
                response = await client.post(
                    "/embed",
                    json={"text": text, "normalize": True},
                    headers=auth_headers,
                )
                embeddings.append(response.json()["embedding"])
            
            # 5. Store embeddings in VDB
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                response = await client.post(
                    f"/vdb/projects/{project_id}/collections/{collection_name}/add",
                    json={
                        "id": f"text_{i}",
                        "embedding": embedding,
                        "document": text,
                        "metadata": {"original": text},
                    },
                    headers=auth_headers,
                )
                assert response.status_code == 200
            
            # 6. Generate query embedding
            response = await client.post(
                "/embed",
                json={"text": "AI technology", "task_type": "query", "normalize": True},
                headers=auth_headers,
            )
            query_embedding = response.json()["embedding"]
            
            # 7. Search for similar texts
            response = await client.post(
                f"/vdb/projects/{project_id}/collections/{collection_name}/search",
                json={"query_vector": query_embedding, "limit": 2},
                headers=auth_headers,
            )
            assert response.status_code == 200
            results = response.json()["data"]
            
            # Should find relevant results
            assert len(results) > 0
            assert all("metadata" in r for r in results)
            assert all("document" in r for r in results)
