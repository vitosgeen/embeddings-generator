@Copilot commented on this pull request.
Pull request overview

This PR introduces a simplified API for beginners that abstracts away vector operations, allowing users to add and search text documents without understanding embeddings or machine learning concepts. The PR adds three main components: a get_vector method for retrieving vectors by ID, a find_similar endpoint for similarity-based recommendations, and two simplified endpoints (simple_add_text, simple_search_text) that handle embedding generation automatically.

Key changes:

    Added get_vector method to the VectorDB port interface and LanceDB storage implementation for retrieving individual vectors by ID
    Implemented find_similar endpoint that uses an existing vector as a reference to find similar items
    Created simplified "beginner-friendly" API endpoints that automatically handle text-to-vector conversion and similarity scoring

Reviewed changes

Copilot reviewed 5 out of 5 changed files in this pull request and generated 22 comments.
Show a summary per file
File 	Description
app/ports/vdb_port.py 	Adds get_vector method to port interface for retrieving vectors by ID
app/adapters/infra/vdb_storage.py 	Implements get_vector method with shard routing and LanceDB query logic
app/adapters/rest/vdb_routes.py 	Adds FindSimilarRequest, SimpleAddTextRequest, SimpleSearchTextRequest models and three new endpoints: find_similar, simple_add_text, simple_search_text
README.md 	Documents the new Simple API with examples, use cases, and quick start guide
Embeddings_Service.postman_collection.json 	Adds Postman collection examples for the Simple API endpoints and workflows

Critical Issues Found:

    Missing explicit permission checks (require_permission) in simple API endpoints - security risk
    Incorrect attribute names (embedding vs vector) causing runtime errors in get_vector and find_similar
    Uncaught PermissionError exceptions from require_project_access will return 500 instead of 403
    Inconsistent similarity score handling between endpoints may produce incorrect results
    Inconsistent operation_type naming between quota checks and usage recording
    SQL injection risk in WHERE clause string interpolation
    No test coverage for new functionality

💡 Add Copilot custom instructions for smarter, more guided reviews. Learn how to get started.

In app/adapters/rest/vdb_routes.py:

> +                project_id=ProjectId(project_id),
+                collection=CollectionName(collection),
+                vector_id=req.vector_id,
+            )
+            
+            if not vector_record:
+                raise HTTPException(
+                    status_code=404,
+                    detail=f"Vector '{req.vector_id}' not found in collection '{collection}'"
+                )
+            
+            # Search for similar vectors (request limit + 1 to account for the reference vector)
+            result = search_vectors_uc.execute(
+                project_id=project_id,
+                collection=collection,
+                query_vector=vector_record.embedding,

The embedding attribute is accessed on VectorRecord, but according to the domain model in app/domain/vdb.py, the attribute is named vector, not embedding. This will cause an AttributeError at runtime.

Change vector_record.embedding to vector_record.vector.
⬇️ Suggested change

-                query_vector=vector_record.embedding,
+                query_vector=vector_record.vector,

In app/adapters/rest/vdb_routes.py:

> +        3. Make it searchable
+        
+        Args:
+            project_id: Your project name
+            collection: Collection name to store the text
+            req: Text content with ID and optional metadata
+            auth: Authentication (automatic)
+            
+        Returns:
+            Success response with vector ID
+        """
+        start_time = time.time()
+        
+        # Check permissions and project access
+        auth.require_project_access(project_id)
+        

This endpoint is missing an explicit permission check with auth.require_permission(). Other endpoints in the codebase that add vectors use auth.require_permission("write:vectors") (see line 295). The simple API should follow the same permission model for consistency and security.

Add auth.require_permission("write:vectors") after line 1369 and before the quota check.
⬇️ Suggested change

-        
+        auth.require_permission("write:vectors")

In app/adapters/rest/vdb_routes.py:

> +                operation_type="add_vector",
+                vector_count=1
+            )
+            if not quota_ok:
+                usage_storage = get_usage_storage()
+                if usage_storage:
+                    usage_storage.record_operation(
+                        user_id=auth.user_id,
+                        project_id=project_id,
+                        operation_type="simple_add_text",
+                        collection_name=collection,
+                        status="quota_exceeded",
+                        metadata={"reason": reason}
+                    )
+                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
+        
+        try:
+            # Generate embedding from text
+            from ...usecases.generate_embedding import GenerateEmbeddingUC
+            from ...bootstrap import build_usecase
+            
+            embedding_uc = build_usecase()
+            
+            # Use 'document' task type for storing documents
+            embedding_result = embedding_uc.embed(req.text, task_type="document", normalize=True)
+            vector = embedding_result["embedding"]
+            
+            # Add vector to collection
+            result = add_vector_uc.execute(
+                project_id=project_id,
+                collection=collection,
+                vector_id=req.id,
+                embedding=vector,
+                metadata=req.metadata,
+                document=req.text,  # Store original text
+            )
+            
+            # Record usage
+            duration_ms = int((time.time() - start_time) * 1000)
+            usage_storage = get_usage_storage()
+            if usage_storage:
+                usage_storage.record_operation(
+                    user_id=auth.user_id,
+                    project_id=project_id,
+                    operation_type="simple_add_text",

Inconsistent operation type naming between quota check and usage recording. The quota check uses operation_type="add_vector" (line 1377) while usage recording uses operation_type="simple_add_text" (line 1386 and 1421). This inconsistency may cause issues with quota tracking and usage analytics.

For consistency, use the same operation_type value in both places. Consider using "simple_add_text" in the quota check as well to distinguish simple API usage from regular vector additions.

In app/adapters/rest/vdb_routes.py:

> +                operation_type="search_vectors"
+            )
+            if not quota_ok:
+                usage_storage = get_usage_storage()
+                if usage_storage:
+                    usage_storage.record_operation(
+                        user_id=auth.user_id,
+                        project_id=project_id,
+                        operation_type="simple_search_text",
+                        collection_name=collection,
+                        status="quota_exceeded",
+                        metadata={"reason": reason}
+                    )
+                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
+        
+        try:
+            # Generate embedding from query text
+            from ...usecases.generate_embedding import GenerateEmbeddingUC
+            from ...bootstrap import build_usecase
+            
+            embedding_uc = build_usecase()
+            
+            # Use 'query' task type for search queries
+            embedding_result = embedding_uc.embed(req.query, task_type="query", normalize=True)
+            query_vector = embedding_result["embedding"]
+            
+            # Perform vector search
+            result = search_vectors_uc.execute(
+                project_id=project_id,
+                collection=collection,
+                query_vector=query_vector,
+                limit=req.limit,
+                include_debug=False,
+            )
+            
+            # Apply minimum score filter and format results
+            filtered_results = []
+            if "data" in result:
+                for item in result["data"]:
+                    score = item.get("score", 0.0)
+                    
+                    # Convert distance to similarity (for cosine: similarity = 1 - distance)
+                    # LanceDB returns distance, where lower = more similar
+                    # We convert to similarity where higher = more similar (0.0 to 1.0)
+                    similarity = max(0.0, min(1.0, 1.0 - score))
+                    
+                    # Apply minimum score threshold
+                    if req.min_score and similarity < req.min_score:
+                        continue
+                    
+                    filtered_results.append({
+                        "id": item.get("id"),
+                        "text": item.get("document", ""),
+                        "metadata": item.get("metadata", {}),
+                        "similarity": round(similarity, 4),  # Similarity score (0.0 to 1.0)
+                    })
+            
+            # Record usage
+            duration_ms = int((time.time() - start_time) * 1000)
+            usage_storage = get_usage_storage()
+            if usage_storage:
+                usage_storage.record_operation(
+                    user_id=auth.user_id,
+                    project_id=project_id,
+                    operation_type="simple_search_text",

Inconsistent operation type naming between quota check and usage recording. The quota check uses operation_type="search_vectors" (line 1491) while usage recording uses operation_type="simple_search_text" (lines 1499, 1555). This inconsistency may cause issues with quota tracking and usage analytics.

For consistency, use the same operation_type value in both places. Consider using "simple_search_text" in the quota check as well to distinguish simple API usage from regular vector searches.

In app/adapters/infra/vdb_storage.py:

> +    def get_vector(
+        self,
+        project_id: ProjectId,
+        collection: CollectionName,
+        vector_id: str,
+    ) -> Optional[VectorRecord]:
+        """Get a specific vector by ID.
+        
+        Args:
+            project_id: Project identifier
+            collection: Collection name
+            vector_id: ID of vector to retrieve
+            
+        Returns:
+            VectorRecord if found, None otherwise
+        """
+        config = self._load_config(project_id, collection)
+        
+        # Compute which shard contains this vector
+        shard_id = self.sharding.compute_shard(vector_id, config.shards)
+        shard_path = self._shard_path(project_id, collection, shard_id)
+        
+        if not shard_path.exists():
+            return None
+        
+        try:
+            db = self._get_db(shard_path)
+            table = db.open_table("vectors")
+            
+            # Query for the specific vector
+            results = table.search().where(f"id = '{vector_id}'").limit(1).to_list()
+            
+            if not results or results[0].get("deleted", False):
+                return None
+            
+            row = results[0]
+            return VectorRecord(
+                id=row["id"],
+                embedding=row["vector"].tolist() if hasattr(row["vector"], 'tolist') else list(row["vector"]),
+                metadata=json.loads(row.get("metadata", "{}")),
+                document=row.get("document") if row.get("document") else None,
+            )
+        
+        except Exception:
+            return None
+    

The new get_vector implementation lacks test coverage. The repository has comprehensive test coverage for other VDB storage operations (see tests/unit/test_vdb.py and tests/integration/test_vdb_api.py). Consider adding tests to verify:

    Successful vector retrieval
    Handling of non-existent vectors
    Handling of deleted vectors
    Proper shard computation and routing
    Error handling for malformed data

In app/adapters/rest/vdb_routes.py:

> +            return {
+                "success": True,
+                "id": req.id,
+                "project_id": project_id,
+                "collection": collection,
+                "text_length": len(req.text),
+                "embedding_dimension": len(vector),
+                "message": "Text successfully stored and made searchable!"
+            }
+            
+        except ValueError as e:
+            raise HTTPException(status_code=400, detail=str(e))
+        except Exception as e:
+            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
+    
+    @router.post("/simple/{project_id}/collections/{collection}/search")

[nitpick] The API path uses /simple/{project_id}/... which is inconsistent with other endpoints that use /projects/{project_id}/.... This creates two different URL patterns for accessing projects.

Consider using /projects/{project_id}/simple/collections/{collection}/search to maintain consistency with the existing URL structure, or document this intentional divergence clearly in the API documentation.
⬇️ Suggested change

-    @router.post("/simple/{project_id}/collections/{collection}/search")
+    @router.post("/projects/{project_id}/simple/collections/{collection}/search")

In app/adapters/rest/vdb_routes.py:

> +                    # Convert distance to similarity (for cosine: similarity = 1 - distance)
+                    # LanceDB returns distance, where lower = more similar
+                    # We convert to similarity where higher = more similar (0.0 to 1.0)
+                    similarity = max(0.0, min(1.0, 1.0 - score))

The comment and code indicate that LanceDB returns "distance" and this is being converted to "similarity" with 1.0 - score. However, this conversion logic is inconsistent with how other endpoints (like semantic_search at line 588) handle scores - they use the score directly without conversion.

Additionally, the sorting in vdb_storage.py line 300 uses reverse=True, which suggests higher scores are better (similarity semantics), not distance semantics where lower is better.

This inconsistency could lead to incorrect similarity scores being returned. Please verify whether LanceDB returns distance or similarity scores for the configured metric (cosine), and ensure consistent handling across all endpoints.
⬇️ Suggested change

-                    # Convert distance to similarity (for cosine: similarity = 1 - distance)
-                    # LanceDB returns distance, where lower = more similar
-                    # We convert to similarity where higher = more similar (0.0 to 1.0)
-                    similarity = max(0.0, min(1.0, 1.0 - score))
+                    # Use score directly as similarity (LanceDB returns similarity for cosine metric)
+                    # Clamp similarity to [0.0, 1.0] if necessary
+                    similarity = max(0.0, min(1.0, score))

In app/adapters/infra/vdb_storage.py:

> +            return None
+        
+        try:
+            db = self._get_db(shard_path)
+            table = db.open_table("vectors")
+            
+            # Query for the specific vector
+            results = table.search().where(f"id = '{vector_id}'").limit(1).to_list()
+            
+            if not results or results[0].get("deleted", False):
+                return None
+            
+            row = results[0]
+            return VectorRecord(
+                id=row["id"],
+                embedding=row["vector"].tolist() if hasattr(row["vector"], 'tolist') else list(row["vector"]),

The VectorRecord constructor is called with embedding= parameter, but according to the domain model in app/domain/vdb.py line 87, the parameter name is vector, not embedding. This will cause a TypeError at runtime.

Change embedding=row["vector"]... to vector=row["vector"]...
⬇️ Suggested change

-                embedding=row["vector"].tolist() if hasattr(row["vector"], 'tolist') else list(row["vector"]),
+                vector=row["vector"].tolist() if hasattr(row["vector"], 'tolist') else list(row["vector"]),

In README.md:

> +}'
+
+# Search for answers
+curl -X POST .../simple/support/collections/faq/search -d '{
+  "query": "how to change password",
+  "limit": 3
+}'
+```
+
+**Document Search:**
+```bash
+# Store documents
+curl -X POST .../simple/docs/collections/articles/add -d '{
+  "id": "article_42",
+  "text": "Machine learning enables computers to learn from data...",
+  "metadata": {"topic": "AI", "date": "2024-12-06"}

[nitpick] The metadata date "2024-12-06" is over a year old (current date is December 8, 2025). Consider updating to a more recent date or using a relative/example date to keep documentation current.
⬇️ Suggested change

-  "metadata": {"topic": "AI", "date": "2024-12-06"}
+  "metadata": {"topic": "AI", "date": "YYYY-MM-DD"}

In app/adapters/rest/vdb_routes.py:

> +        
+        Returns matching documents sorted by similarity (1.0 = perfect match, 0.0 = no match).
+        
+        Args:
+            project_id: Your project name
+            collection: Collection to search in
+            req: Search query text and options
+            auth: Authentication (automatic)
+            
+        Returns:
+            List of matching documents with similarity scores
+        """
+        start_time = time.time()
+        
+        # Check permissions and project access
+        auth.require_project_access(project_id)

This endpoint is missing an explicit permission check with auth.require_permission(). Other search endpoints in the codebase use auth.require_permission("read:vectors") (see lines 399, 520, 684). The simple API should follow the same permission model for consistency and security.

Add auth.require_permission("read:vectors") after line 1483 and before the quota check.
⬇️ Suggested change

-        auth.require_project_access(project_id)
+        auth.require_project_access(project_id)
+        auth.require_permission("read:vectors")

In app/ports/vdb_port.py:

> +    def get_vector(
+        self,
+        project_id: ProjectId,
+        collection: CollectionName,
+        vector_id: str,
+    ) -> Optional[VectorRecord]:
+        """Get a specific vector by ID.
+        
+        Args:
+            project_id: Project identifier
+            collection: Collection name
+            vector_id: ID of vector to retrieve
+            
+        Returns:
+            VectorRecord if found, None otherwise
+        """
+        ...

The new get_vector method in the port interface lacks test coverage. The repository has comprehensive test coverage for other VDB operations (see tests/integration/test_vdb_api.py). Consider adding tests for this new method to maintain consistency with the existing test suite.

In app/adapters/rest/vdb_routes.py:

> +            # Search for similar vectors (request limit + 1 to account for the reference vector)
+            result = search_vectors_uc.execute(
+                project_id=project_id,
+                collection=collection,
+                query_vector=vector_record.embedding,
+                limit=req.limit + 1,  # Get one extra to exclude the reference
+                include_debug=False,
+            )
+            
+            # Filter out the reference vector and apply metadata filters
+            if "data" in result:
+                filtered_results = []
+                for item in result["data"]:
+                    # Skip the reference vector itself
+                    if item.get("id") == req.vector_id:
+                        continue
+                    
+                    # Apply metadata filter if provided
+                    if req.metadata_filter and "metadata" in item and item["metadata"]:
+                        match = all(
+                            item["metadata"].get(k) == v 
+                            for k, v in req.metadata_filter.items()
+                        )
+                        if not match:
+                            continue
+                    
+                    # Apply minimum score filter
+                    if req.min_score is not None and item.get("score", 0.0) < req.min_score:
+                        continue
+                    
+                    # Filter output fields based on request
+                    filtered_item = {
+                        "id": item["id"],
+                        "score": item.get("score", 0.0),
+                    }
+                    
+                    if req.include_metadata and "metadata" in item:
+                        filtered_item["metadata"] = item["metadata"]
+                    
+                    if req.include_text and "document" in item:
+                        filtered_item["document"] = item["document"]
+                    
+                    filtered_results.append(filtered_item)
+                    
+                    # Stop if we have enough results
+                    if len(filtered_results) >= req.limit:
+                        break
+                
+                result["data"] = filtered_results
+                result["count"] = len(filtered_results)
+                result["reference_vector_id"] = req.vector_id
+                if req.include_metadata and vector_record.metadata:
+                    result["reference_metadata"] = vector_record.metadata
+            
+            # Record usage
+            duration_ms = int((time.time() - start_time) * 1000)
+            usage_storage = get_usage_storage()
+            if usage_storage:
+                usage_storage.record_operation(
+                    user_id=auth.user_id,
+                    project_id=project_id,
+                    operation_type="find_similar",
+                    collection_name=collection,
+                    duration_ms=duration_ms,
+                    status="success",
+                    metadata={
+                        "result_count": result.get("count", 0),
+                        "vector_id": req.vector_id,
+                        "had_filter": req.metadata_filter is not None,
+                        "min_score": req.min_score
+                    }
+                )
+            
+            return result
+        except HTTPException:
+            raise
+        except ValueError as e:
+            usage_storage = get_usage_storage()
+            if usage_storage:
+                usage_storage.record_operation(
+                    user_id=auth.user_id,
+                    project_id=project_id,
+                    operation_type="find_similar",
+                    collection_name=collection,
+                    status="failure",
+                    metadata={"error": str(e), "vector_id": req.vector_id}
+                )
+            raise HTTPException(status_code=400, detail=str(e))
+        except Exception as e:
+            usage_storage = get_usage_storage()
+            if usage_storage:
+                usage_storage.record_operation(
+                    user_id=auth.user_id,
+                    project_id=project_id,
+                    operation_type="find_similar",
+                    collection_name=collection,
+                    status="failure",
+                    metadata={"error": str(e), "vector_id": req.vector_id}
+                )
+            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

The new find_similar endpoint lacks test coverage. The repository has comprehensive test coverage for other VDB endpoints (see tests/integration/test_vdb_api.py). Consider adding integration tests for this new endpoint to verify functionality, error handling, and edge cases (e.g., vector not found, quota exceeded, permission denied).

In app/adapters/rest/vdb_routes.py:

> +          "text": "Python is a programming language",
+          "metadata": {"category": "programming", "level": "beginner"}
+        }
+        ```
+        
+        The system will:
+        1. Automatically convert your text to a vector (embedding)
+        2. Store it in the collection
+        3. Make it searchable
+        
+        Args:
+            project_id: Your project name
+            collection: Collection name to store the text
+            req: Text content with ID and optional metadata
+            auth: Authentication (automatic)
+            
+        Returns:
+            Success response with vector ID
+        """
+        start_time = time.time()
+        
+        # Check permissions and project access
+        auth.require_project_access(project_id)
+        
+        # Check quota
+        quota_storage = get_quota_storage()
+        if quota_storage:
+            quota_ok, reason = quota_storage.check_quota(
+                user_id=auth.user_id,
+                project_id=project_id,
+                operation_type="add_vector",
+                vector_count=1
+            )
+            if not quota_ok:
+                usage_storage = get_usage_storage()
+                if usage_storage:
+                    usage_storage.record_operation(
+                        user_id=auth.user_id,
+                        project_id=project_id,
+                        operation_type="simple_add_text",
+                        collection_name=collection,
+                        status="quota_exceeded",
+                        metadata={"reason": reason}
+                    )
+                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
+        
+        try:
+            # Generate embedding from text
+            from ...usecases.generate_embedding import GenerateEmbeddingUC
+            from ...bootstrap import build_usecase
+            
+            embedding_uc = build_usecase()
+            
+            # Use 'document' task type for storing documents
+            embedding_result = embedding_uc.embed(req.text, task_type="document", normalize=True)
+            vector = embedding_result["embedding"]
+            
+            # Add vector to collection
+            result = add_vector_uc.execute(
+                project_id=project_id,
+                collection=collection,
+                vector_id=req.id,
+                embedding=vector,
+                metadata=req.metadata,
+                document=req.text,  # Store original text
+            )
+            
+            # Record usage
+            duration_ms = int((time.time() - start_time) * 1000)
+            usage_storage = get_usage_storage()
+            if usage_storage:
+                usage_storage.record_operation(
+                    user_id=auth.user_id,
+                    project_id=project_id,
+                    operation_type="simple_add_text",
+                    collection_name=collection,
+                    vector_count=1,
+                    duration_ms=duration_ms,
+                    status="success",
+                    metadata={
+                        "text_length": len(req.text),
+                        "embedding_model": embedding_result.get("model", "unknown"),
+                        "embedding_dimension": len(vector)
+                    }
+                )
+            
+            return {
+                "success": True,
+                "id": req.id,
+                "project_id": project_id,
+                "collection": collection,
+                "text_length": len(req.text),
+                "embedding_dimension": len(vector),
+                "message": "Text successfully stored and made searchable!"
+            }
+            
+        except ValueError as e:
+            raise HTTPException(status_code=400, detail=str(e))
+        except Exception as e:
+            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

The new simple_add_text endpoint lacks test coverage. The repository has comprehensive test coverage for other VDB endpoints (see tests/integration/test_vdb_api.py). Consider adding integration tests to verify:

    Text embedding generation
    Vector storage with correct parameters
    Error handling for invalid inputs
    Permission and quota checks
    Response format correctness

In app/adapters/rest/vdb_routes.py:

> +            List of matching documents with similarity scores
+        """
+        start_time = time.time()
+        
+        # Check permissions and project access
+        auth.require_project_access(project_id)
+        
+        # Check quota
+        quota_storage = get_quota_storage()
+        if quota_storage:
+            quota_ok, reason = quota_storage.check_quota(
+                user_id=auth.user_id,
+                project_id=project_id,
+                operation_type="search_vectors"
+            )
+            if not quota_ok:
+                usage_storage = get_usage_storage()
+                if usage_storage:
+                    usage_storage.record_operation(
+                        user_id=auth.user_id,
+                        project_id=project_id,
+                        operation_type="simple_search_text",
+                        collection_name=collection,
+                        status="quota_exceeded",
+                        metadata={"reason": reason}
+                    )
+                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
+        
+        try:
+            # Generate embedding from query text
+            from ...usecases.generate_embedding import GenerateEmbeddingUC
+            from ...bootstrap import build_usecase
+            
+            embedding_uc = build_usecase()
+            
+            # Use 'query' task type for search queries
+            embedding_result = embedding_uc.embed(req.query, task_type="query", normalize=True)
+            query_vector = embedding_result["embedding"]
+            
+            # Perform vector search
+            result = search_vectors_uc.execute(
+                project_id=project_id,
+                collection=collection,
+                query_vector=query_vector,
+                limit=req.limit,
+                include_debug=False,
+            )
+            
+            # Apply minimum score filter and format results
+            filtered_results = []
+            if "data" in result:
+                for item in result["data"]:
+                    score = item.get("score", 0.0)
+                    
+                    # Convert distance to similarity (for cosine: similarity = 1 - distance)
+                    # LanceDB returns distance, where lower = more similar
+                    # We convert to similarity where higher = more similar (0.0 to 1.0)
+                    similarity = max(0.0, min(1.0, 1.0 - score))
+                    
+                    # Apply minimum score threshold
+                    if req.min_score and similarity < req.min_score:
+                        continue
+                    
+                    filtered_results.append({
+                        "id": item.get("id"),
+                        "text": item.get("document", ""),
+                        "metadata": item.get("metadata", {}),
+                        "similarity": round(similarity, 4),  # Similarity score (0.0 to 1.0)
+                    })
+            
+            # Record usage
+            duration_ms = int((time.time() - start_time) * 1000)
+            usage_storage = get_usage_storage()
+            if usage_storage:
+                usage_storage.record_operation(
+                    user_id=auth.user_id,
+                    project_id=project_id,
+                    operation_type="simple_search_text",
+                    collection_name=collection,
+                    duration_ms=duration_ms,
+                    status="success",
+                    metadata={
+                        "query_length": len(req.query),
+                        "results_count": len(filtered_results),
+                        "min_score": req.min_score
+                    }
+                )
+            
+            return {
+                "success": True,
+                "query": req.query,
+                "results": filtered_results,
+                "count": len(filtered_results),
+                "message": f"Found {len(filtered_results)} similar documents"
+            }
+            
+        except ValueError as e:
+            raise HTTPException(status_code=400, detail=str(e))
+        except Exception as e:
+            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

The new simple_search_text endpoint lacks test coverage. The repository has comprehensive test coverage for other VDB endpoints (see tests/integration/test_vdb_api.py). Consider adding integration tests to verify:

    Query embedding generation
    Search functionality and result ordering
    Similarity score calculation and filtering
    min_score threshold application
    Error handling for edge cases

In app/adapters/rest/vdb_routes.py:

> +        2. Store it in the collection
+        3. Make it searchable
+        
+        Args:
+            project_id: Your project name
+            collection: Collection name to store the text
+            req: Text content with ID and optional metadata
+            auth: Authentication (automatic)
+            
+        Returns:
+            Success response with vector ID
+        """
+        start_time = time.time()
+        
+        # Check permissions and project access
+        auth.require_project_access(project_id)

The require_project_access method from AuthContext raises a PermissionError, but this exception is not being caught in the error handling. This will result in a 500 Internal Server Error instead of the appropriate 403 Forbidden error.

Consider catching PermissionError and converting it to an HTTPException with status code 403, or follow the pattern used in other endpoints where auth.can_access_project is checked explicitly and an HTTPException is raised directly.
⬇️ Suggested change

-        auth.require_project_access(project_id)
+        try:
+            auth.require_project_access(project_id)
+        except PermissionError as e:
+            raise HTTPException(status_code=403, detail=str(e))

In app/adapters/rest/vdb_routes.py:

> +            if not quota_ok:
+                usage_storage = get_usage_storage()
+                if usage_storage:
+                    usage_storage.record_operation(
+                        user_id=auth.user_id,
+                        project_id=project_id,
+                        operation_type="simple_add_text",
+                        collection_name=collection,
+                        status="quota_exceeded",
+                        metadata={"reason": reason}
+                    )
+                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
+        
+        try:
+            # Generate embedding from text
+            from ...usecases.generate_embedding import GenerateEmbeddingUC

The build_usecase() function is called but its return type is GenerateEmbeddingUC, not a use case that has an embed method. Looking at the bootstrap code, build_usecase() returns GenerateEmbeddingUC(encoder), which should have the embed method.

However, the import statement imports both GenerateEmbeddingUC and build_usecase but only uses build_usecase(). The GenerateEmbeddingUC import is unused. Consider removing it or documenting why it's there.
⬇️ Suggested change

-            from ...usecases.generate_embedding import GenerateEmbeddingUC

In app/adapters/rest/vdb_routes.py:

> +            if not quota_ok:
+                usage_storage = get_usage_storage()
+                if usage_storage:
+                    usage_storage.record_operation(
+                        user_id=auth.user_id,
+                        project_id=project_id,
+                        operation_type="simple_search_text",
+                        collection_name=collection,
+                        status="quota_exceeded",
+                        metadata={"reason": reason}
+                    )
+                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
+        
+        try:
+            # Generate embedding from query text
+            from ...usecases.generate_embedding import GenerateEmbeddingUC

The GenerateEmbeddingUC import is unused. Only build_usecase is actually used to create the embedding use case. Consider removing the unused import.
⬇️ Suggested change

-            from ...usecases.generate_embedding import GenerateEmbeddingUC

In Embeddings_Service.postman_collection.json:

> +					},
+					"response": []
+				},
+				{
+					"name": "Add FAQ Entry",
+					"request": {
+						"method": "POST",
+						"header": [
+							{
+								"key": "Content-Type",
+								"value": "application/json"
+							}
+						],
+						"body": {
+							"mode": "raw",
+							"raw": "{\n  \"id\": \"faq_password_reset\",\n  \"text\": \"To reset your password, click on 'Forgot Password' on the login page. You will receive an email with instructions to create a new password.\",\n  \"metadata\": {\n    \"category\": \"account\",\n    \"priority\": \"high\",\n    \"updated\": \"2024-12-06\"\n  }\n}"

[nitpick] The description says "updated: 2024-12-06" but the current date is December 8, 2025 according to the system context. Using dates from over a year ago in example metadata may be confusing. Consider using a more recent or relative date, or remove the date field from the example.
⬇️ Suggested change

-							"raw": "{\n  \"id\": \"faq_password_reset\",\n  \"text\": \"To reset your password, click on 'Forgot Password' on the login page. You will receive an email with instructions to create a new password.\",\n  \"metadata\": {\n    \"category\": \"account\",\n    \"priority\": \"high\",\n    \"updated\": \"2024-12-06\"\n  }\n}"
+							"raw": "{\n  \"id\": \"faq_password_reset\",\n  \"text\": \"To reset your password, click on 'Forgot Password' on the login page. You will receive an email with instructions to create a new password.\",\n  \"metadata\": {\n    \"category\": \"account\",\n    \"priority\": \"high\",\n    \"updated\": \"2025-12-08\"\n  }\n}"

In app/adapters/rest/vdb_routes.py:

> @@ -1132,4 +1324,256 @@ def batch_delete_vectors(
             duration_ms=duration_ms
         )
     
+    # ============================================================================
+    # SIMPLE API FOR BEGINNERS (No Vector Knowledge Required)
+    # ============================================================================
+    
+    @router.post("/simple/{project_id}/collections/{collection}/add")

[nitpick] The API path uses /simple/{project_id}/... which is inconsistent with other endpoints that use /projects/{project_id}/.... This creates two different URL patterns for accessing projects, which could be confusing for API consumers.

Consider using /projects/{project_id}/simple/collections/{collection}/add to maintain consistency with the existing URL structure, or document this intentional divergence clearly in the API documentation.

In app/adapters/rest/vdb_routes.py:

> +        
+        Returns matching documents sorted by similarity (1.0 = perfect match, 0.0 = no match).
+        
+        Args:
+            project_id: Your project name
+            collection: Collection to search in
+            req: Search query text and options
+            auth: Authentication (automatic)
+            
+        Returns:
+            List of matching documents with similarity scores
+        """
+        start_time = time.time()
+        
+        # Check permissions and project access
+        auth.require_project_access(project_id)

The require_project_access method from AuthContext raises a PermissionError, but this exception is not being caught in the error handling. This will result in a 500 Internal Server Error instead of the appropriate 403 Forbidden error.

Consider catching PermissionError and converting it to an HTTPException with status code 403, or follow the pattern used in other endpoints where auth.can_access_project is checked explicitly and an HTTPException is raised directly.
⬇️ Suggested change

-        auth.require_project_access(project_id)
+        try:
+            auth.require_project_access(project_id)
+        except PermissionError as e:
+            raise HTTPException(status_code=403, detail=str(e))

In app/adapters/infra/vdb_storage.py:

> +        """
+        config = self._load_config(project_id, collection)
+        
+        # Compute which shard contains this vector
+        shard_id = self.sharding.compute_shard(vector_id, config.shards)
+        shard_path = self._shard_path(project_id, collection, shard_id)
+        
+        if not shard_path.exists():
+            return None
+        
+        try:
+            db = self._get_db(shard_path)
+            table = db.open_table("vectors")
+            
+            # Query for the specific vector
+            results = table.search().where(f"id = '{vector_id}'").limit(1).to_list()

The SQL-like WHERE clause uses string interpolation (f"id = '{vector_id}'") which could be vulnerable to injection attacks if vector_id contains special characters like single quotes. While vector_id comes from a validated request parameter, it's better to use parameterized queries if LanceDB supports them, or at minimum, escape the vector_id properly to prevent potential issues.
⬇️ Suggested change

-            results = table.search().where(f"id = '{vector_id}'").limit(1).to_list()
+            safe_vector_id = vector_id.replace("'", "''")
+            results = table.search().where(f"id = '{safe_vector_id}'").limit(1).to_list()

In app/adapters/rest/vdb_routes.py:

> +                    )
+                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
+        
+        try:
+            # Generate embedding from text
+            from ...usecases.generate_embedding import GenerateEmbeddingUC
+            from ...bootstrap import build_usecase
+            
+            embedding_uc = build_usecase()
+            
+            # Use 'document' task type for storing documents
+            embedding_result = embedding_uc.embed(req.text, task_type="document", normalize=True)
+            vector = embedding_result["embedding"]
+            
+            # Add vector to collection
+            result = add_vector_uc.execute(

Variable result is not used.
⬇️ Suggested change

-            result = add_vector_uc.execute(
+            add_vector_uc.execute(

—