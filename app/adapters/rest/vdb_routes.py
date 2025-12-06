"""REST API routes for Vector Database Service."""

import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from ...usecases.vdb_usecases import (
    CreateProjectUC,
    ListProjectsUC,
    CreateCollectionUC,
    ListCollectionsUC,
    AddVectorUC,
    SearchVectorsUC,
    DeleteVectorUC,
)
from ...domain.auth import AuthContext
from .auth_middleware import get_current_user, get_auth_storages

# Global usage and quota storage (will be initialized)
_usage_storage = None
_quota_storage = None


def initialize_usage_tracking():
    """Initialize usage tracking storage."""
    global _usage_storage, _quota_storage
    if _usage_storage is None:
        from ...adapters.infra.auth_storage import UsageTrackingStorage, QuotaStorage
        user_storage, key_storage, audit_storage, project_storage = get_auth_storages()
        db = user_storage.db if user_storage else None
        if db:
            _usage_storage = UsageTrackingStorage(db)
            _quota_storage = QuotaStorage(db)


def get_usage_storage():
    """Get usage tracking storage instance."""
    if _usage_storage is None:
        initialize_usage_tracking()
    return _usage_storage


def get_quota_storage():
    """Get quota storage instance."""
    if _quota_storage is None:
        initialize_usage_tracking()
    return _quota_storage


# Request/Response Models
class CreateProjectRequest(BaseModel):
    project_id: str = Field(..., description="Unique project identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional project metadata")


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., description="Collection name")
    dimension: int = Field(..., description="Vector dimension", gt=0)
    metric: str = Field(default="cosine", description="Distance metric (cosine, dot, L2)")
    shards: int = Field(default=4, description="Number of shards", gt=0)
    description: Optional[str] = Field(default=None, description="Optional description")


class AddVectorRequest(BaseModel):
    id: str = Field(..., description="Unique vector identifier")
    embedding: List[float] = Field(..., description="Vector embedding")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")
    document: Optional[str] = Field(default=None, description="Optional raw text document")


class SearchRequest(BaseModel):
    query_vector: List[float] = Field(..., description="Query vector for similarity search")
    limit: int = Field(default=10, description="Maximum number of results", gt=0, le=100)
    metadata_filter: Optional[Dict[str, Any]] = Field(default=None, description="Filter results by metadata fields")


class SemanticSearchRequest(BaseModel):
    """Request model for semantic search by text query."""
    query: str = Field(..., description="Text query for semantic search", min_length=1, max_length=10000)
    limit: int = Field(default=10, description="Maximum number of results", gt=0, le=100)
    metadata_filter: Optional[Dict[str, Any]] = Field(default=None, description="Filter results by metadata fields")
    min_score: Optional[float] = Field(default=None, description="Minimum similarity score (0.0 to 1.0)", ge=0.0, le=1.0)
    include_text: bool = Field(default=True, description="Include document text in results")
    include_metadata: bool = Field(default=True, description="Include metadata in results")


class FindSimilarRequest(BaseModel):
    """Request model for finding similar vectors based on an existing vector ID."""
    vector_id: str = Field(..., description="ID of the reference vector to find similar items for", min_length=1)
    limit: int = Field(default=10, description="Maximum number of results (excluding the reference vector)", gt=0, le=100)
    metadata_filter: Optional[Dict[str, Any]] = Field(default=None, description="Filter results by metadata fields")
    min_score: Optional[float] = Field(default=None, description="Minimum similarity score (0.0 to 1.0)", ge=0.0, le=1.0)
    include_metadata: bool = Field(default=True, description="Include metadata in results")
    include_text: bool = Field(default=True, description="Include document text in results")


class SimpleAddTextRequest(BaseModel):
    """Simplified request for beginners - just add text without dealing with vectors."""
    id: str = Field(..., description="Unique identifier for this text document", min_length=1, max_length=500)
    text: str = Field(..., description="Text content to store", min_length=1, max_length=50000)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata (e.g., {'category': 'news', 'author': 'John'})")


class SimpleSearchTextRequest(BaseModel):
    """Simplified search request for beginners - just search by text."""
    query: str = Field(..., description="Text to search for", min_length=1, max_length=10000)
    limit: int = Field(default=10, description="How many results to return", gt=0, le=100)
    min_score: Optional[float] = Field(default=0.5, description="Minimum similarity (0.0-1.0, higher = more similar)", ge=0.0, le=1.0)


class UpsertVectorRequest(BaseModel):
    id: str = Field(..., description="Unique vector identifier")
    embedding: List[float] = Field(..., description="Vector embedding")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")
    document: Optional[str] = Field(default=None, description="Optional raw text document")


# Batch operation models
class BatchVectorItem(BaseModel):
    id: str = Field(..., description="Unique vector identifier")
    embedding: List[float] = Field(..., description="Vector embedding")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata")
    document: Optional[str] = Field(default=None, description="Optional raw text document")


class BatchAddRequest(BaseModel):
    vectors: List[BatchVectorItem] = Field(..., description="List of vectors to add", min_items=1, max_items=1000)


class BatchUpdateRequest(BaseModel):
    vectors: List[BatchVectorItem] = Field(..., description="List of vectors to update (upsert)", min_items=1, max_items=1000)


class BatchDeleteRequest(BaseModel):
    vector_ids: List[str] = Field(..., description="List of vector IDs to delete", min_items=1, max_items=1000)


class BatchOperationResult(BaseModel):
    success: bool
    vector_id: str
    error: Optional[str] = None


class BatchOperationResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: List[BatchOperationResult]
    duration_ms: int


def build_vdb_router(
    create_project_uc: CreateProjectUC,
    list_projects_uc: ListProjectsUC,
    create_collection_uc: CreateCollectionUC,
    list_collections_uc: ListCollectionsUC,
    add_vector_uc: AddVectorUC,
    search_vectors_uc: SearchVectorsUC,
    delete_vector_uc: DeleteVectorUC,
) -> APIRouter:
    """Build the VDB API router with all endpoints."""
    
    router = APIRouter(prefix="/vdb", tags=["Vector Database"])
    
    @router.post("/projects")
    def create_project(
        req: CreateProjectRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Create a new project.
        
        Creates a new isolated project for storing vector collections.
        Each project has its own directory and metadata.
        Requires admin or service-app role.
        """
        # Check permissions
        auth.require_permission("write:projects")
        
        try:
            return create_project_uc.execute(
                project_id=req.project_id,
                metadata=req.metadata,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.get("/projects")
    def list_projects(auth: AuthContext = Depends(get_current_user)):
        """List accessible projects.
        
        Returns a list of project IDs the user can access.
        Admin users see all projects, others see only their accessible projects.
        Requires read:projects permission.
        """
        auth.require_permission("read:projects")
        
        try:
            all_projects = list_projects_uc.execute()
            
            # Admin can see all projects
            if auth.role == "admin":
                return all_projects
            
            # Filter to only accessible projects
            accessible_project_ids = set(auth.accessible_projects)
            filtered_projects = [
                p for p in all_projects.get("projects", [])
                if p in accessible_project_ids
            ]
            
            return {"projects": filtered_projects}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.get("/projects/{project_id}/collections")
    def list_collections(
        project_id: str,
        auth: AuthContext = Depends(get_current_user),
    ):
        """List all collections in a project.
        
        Returns a list of collection names for the specified project.
        Requires read:collections permission and project access.
        """
        auth.require_permission("read:collections")
        
        # Check project access
        if not auth.can_access_project(project_id):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to project '{project_id}'",
            )
        
        try:
            return list_collections_uc.execute(project_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.post("/projects/{project_id}/collections")
    def create_collection(
        project_id: str,
        req: CreateCollectionRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Create a new collection in a project.
        
        Creates a new vector collection with the specified configuration.
        The collection will be automatically sharded for scalability.
        Requires write:collections permission and project access.
        """
        auth.require_permission("write:collections")
        
        # Check project access
        if not auth.can_access_project(project_id):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to project '{project_id}'",
            )
        
        try:
            return create_collection_uc.execute(
                project_id=project_id,
                name=req.name,
                dimension=req.dimension,
                metric=req.metric,
                shards=req.shards,
                description=req.description,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.post("/projects/{project_id}/collections/{collection}/add")
    def add_vector(
        project_id: str,
        collection: str,
        req: AddVectorRequest,
        include_debug: bool = Query(default=False, description="Include debug information"),
        auth: AuthContext = Depends(get_current_user),
    ):
        """Add a vector to a collection.
        
        Adds a new vector to the specified collection. The vector will be
        automatically assigned to the appropriate shard based on its ID.
        Requires write:vectors permission and project access.
        """
        start_time = time.time()
        auth.require_permission("write:vectors")
        
        # Check project access
        if not auth.can_access_project(project_id):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to project '{project_id}'",
            )
        
        # Check quota
        quota_storage = get_quota_storage()
        if quota_storage:
            allowed, reason = quota_storage.check_quota(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="add_vector",
                vector_count=1
            )
            if not allowed:
                # Record quota exceeded
                usage_storage = get_usage_storage()
                if usage_storage:
                    usage_storage.record_operation(
                        user_id=auth.user_id,
                        project_id=project_id,
                        operation_type="add_vector",
                        vector_count=1,
                        collection_name=collection,
                        status="quota_exceeded",
                        metadata={"reason": reason}
                    )
                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
        
        try:
            result = add_vector_uc.execute(
                project_id=project_id,
                collection=collection,
                vector_id=req.id,
                embedding=req.embedding,
                metadata=req.metadata,
                document=req.document,
                include_debug=include_debug,
            )
            
            # Record usage
            duration_ms = int((time.time() - start_time) * 1000)
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="add_vector",
                    vector_count=1,
                    collection_name=collection,
                    payload_size=len(str(req.embedding)),
                    duration_ms=duration_ms,
                    status="success"
                )
            
            return result
        except ValueError as e:
            # Record failure
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="add_vector",
                    vector_count=1,
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="add_vector",
                    vector_count=1,
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.post("/projects/{project_id}/collections/{collection}/search")
    def search_vectors(
        project_id: str,
        collection: str,
        req: SearchRequest,
        include_debug: bool = Query(default=False, description="Include debug information"),
        auth: AuthContext = Depends(get_current_user),
    ):
        """Search for similar vectors.
        
        Performs similarity search across all shards in the collection
        and returns the top-k most similar vectors.
        Supports metadata filtering to narrow results.
        Requires read:vectors permission and project access.
        """
        start_time = time.time()
        auth.require_permission("read:vectors")
        
        # Check project access
        if not auth.can_access_project(project_id):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to project '{project_id}'",
            )
        
        # Check quota
        quota_storage = get_quota_storage()
        if quota_storage:
            allowed, reason = quota_storage.check_quota(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="search",
                vector_count=1
            )
            if not allowed:
                usage_storage = get_usage_storage()
                if usage_storage:
                    usage_storage.record_operation(
                        user_id=auth.user_id,
                        project_id=project_id,
                        operation_type="search",
                        collection_name=collection,
                        status="quota_exceeded",
                        metadata={"reason": reason}
                    )
                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
        
        try:
            result = search_vectors_uc.execute(
                project_id=project_id,
                collection=collection,
                query_vector=req.query_vector,
                limit=req.limit,
                include_debug=include_debug,
            )
            
            # Apply metadata filtering if provided
            if req.metadata_filter and "results" in result:
                filtered_results = []
                for item in result["results"]:
                    if "metadata" in item and item["metadata"]:
                        # Check if all filter criteria match
                        match = all(
                            item["metadata"].get(k) == v 
                            for k, v in req.metadata_filter.items()
                        )
                        if match:
                            filtered_results.append(item)
                result["results"] = filtered_results
                result["count"] = len(filtered_results)
                if include_debug:
                    result["debug"]["metadata_filter_applied"] = req.metadata_filter
                    result["debug"]["results_before_filter"] = len(result.get("results", []))
            
            # Record usage
            duration_ms = int((time.time() - start_time) * 1000)
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="search",
                    collection_name=collection,
                    duration_ms=duration_ms,
                    status="success",
                    metadata={
                        "result_count": result.get("count", 0),
                        "had_filter": req.metadata_filter is not None
                    }
                )
            
            return result
        except ValueError as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="search",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="search",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.post("/projects/{project_id}/collections/{collection}/similar")
    def semantic_search(
        project_id: str,
        collection: str,
        req: SemanticSearchRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Semantic search by text query.
        
        Automatically converts text query to embedding and searches for similar items.
        Returns full item data including id, metadata, document text, and similarity scores.
        
        This is perfect for:
        - "Find products similar to 'red running shoes'"
        - "Show documents related to 'machine learning'"
        - "Get recommendations based on this description"
        
        Requires read:vectors permission and project access.
        """
        start_time = time.time()
        auth.require_permission("read:vectors")
        
        # Check project access
        if not auth.can_access_project(project_id):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to project '{project_id}'",
            )
        
        # Check quota
        quota_storage = get_quota_storage()
        if quota_storage:
            allowed, reason = quota_storage.check_quota(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="search",
                vector_count=1
            )
            if not allowed:
                usage_storage = get_usage_storage()
                if usage_storage:
                    usage_storage.record_operation(
                        user_id=auth.user_id,
                        project_id=project_id,
                        operation_type="semantic_search",
                        collection_name=collection,
                        status="quota_exceeded",
                        metadata={"reason": reason}
                    )
                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
        
        try:
            # Generate embedding from query text
            from ...usecases.generate_embedding import GenerateEmbeddingUC
            from ...bootstrap import build_usecase
            
            embedding_uc = build_usecase()
            
            # Use 'query' task type for search queries (optimized for search)
            embedding_result = embedding_uc.embed(req.query, task_type="query", normalize=True)
            query_vector = embedding_result["embedding"]
            
            # Perform vector search
            result = search_vectors_uc.execute(
                project_id=project_id,
                collection=collection,
                query_vector=query_vector,
                limit=req.limit,
                include_debug=False,
            )
            
            # Apply metadata filtering if provided
            if req.metadata_filter and "data" in result:
                filtered_results = []
                for item in result["data"]:
                    if "metadata" in item and item["metadata"]:
                        match = all(
                            item["metadata"].get(k) == v 
                            for k, v in req.metadata_filter.items()
                        )
                        if match:
                            filtered_results.append(item)
                result["data"] = filtered_results
            
            # Apply minimum score filter if provided
            if req.min_score is not None and "data" in result:
                filtered_results = [
                    item for item in result["data"]
                    if item.get("score", 0) >= req.min_score
                ]
                result["data"] = filtered_results
            
            # Format results with rich data
            if "data" in result:
                formatted_results = []
                for item in result["data"]:
                    formatted_item = {
                        "id": item.get("id"),
                        "score": item.get("score"),
                    }
                    
                    # Include metadata if requested
                    if req.include_metadata and "metadata" in item:
                        formatted_item["metadata"] = item["metadata"]
                    
                    # Include document text if requested  
                    if req.include_text and "document" in item:
                        formatted_item["document"] = item["document"]
                    
                    formatted_results.append(formatted_item)
                
                result["data"] = formatted_results
            
            # Add query info and count to response
            result["query"] = req.query
            result["query_embedding_dim"] = len(query_vector)
            result["count"] = len(result.get("data", []))
            
            # Record usage
            duration_ms = int((time.time() - start_time) * 1000)
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="semantic_search",
                    collection_name=collection,
                    duration_ms=duration_ms,
                    status="success",
                    metadata={
                        "result_count": result.get("count", 0),
                        "query_length": len(req.query),
                        "had_filter": req.metadata_filter is not None,
                        "min_score": req.min_score
                    }
                )
            
            return result
        except ValueError as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="semantic_search",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="semantic_search",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.post("/projects/{project_id}/collections/{collection}/find-similar")
    def find_similar(
        project_id: str,
        collection: str,
        req: FindSimilarRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Find similar vectors based on an existing vector ID.
        
        This endpoint retrieves a vector by ID and finds other similar vectors in the collection.
        Perfect for "more like this" functionality or recommendation systems.
        
        Use cases:
        - "Show me products similar to this one"
        - "Find documents related to this article"
        - "Get recommendations based on this item"
        
        The reference vector is excluded from results.
        Requires read:vectors permission and project access.
        """
        start_time = time.time()
        auth.require_permission("read:vectors")
        
        # Check project access
        if not auth.can_access_project(project_id):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to project '{project_id}'",
            )
        
        # Check quota
        quota_storage = get_quota_storage()
        if quota_storage:
            allowed, reason = quota_storage.check_quota(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="search",
                vector_count=1
            )
            if not allowed:
                usage_storage = get_usage_storage()
                if usage_storage:
                    usage_storage.record_operation(
                        user_id=auth.user_id,
                        project_id=project_id,
                        operation_type="find_similar",
                        collection_name=collection,
                        status="quota_exceeded",
                        metadata={"reason": reason, "vector_id": req.vector_id}
                    )
                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
        
        try:
            # Get the reference vector
            from ...domain.vdb import ProjectId, CollectionName
            vector_record = search_vectors_uc.storage.get_vector(
                project_id=ProjectId(project_id),
                collection=CollectionName(collection),
                vector_id=req.vector_id,
            )
            
            if not vector_record:
                raise HTTPException(
                    status_code=404,
                    detail=f"Vector '{req.vector_id}' not found in collection '{collection}'"
                )
            
            # Search for similar vectors (request limit + 1 to account for the reference vector)
            result = search_vectors_uc.execute(
                project_id=project_id,
                collection=collection,
                query_vector=vector_record.embedding,
                limit=req.limit + 1,  # Get one extra to exclude the reference
                include_debug=False,
            )
            
            # Filter out the reference vector and apply metadata filters
            if "data" in result:
                filtered_results = []
                for item in result["data"]:
                    # Skip the reference vector itself
                    if item.get("id") == req.vector_id:
                        continue
                    
                    # Apply metadata filter if provided
                    if req.metadata_filter and "metadata" in item and item["metadata"]:
                        match = all(
                            item["metadata"].get(k) == v 
                            for k, v in req.metadata_filter.items()
                        )
                        if not match:
                            continue
                    
                    # Apply minimum score filter
                    if req.min_score is not None and item.get("score", 0.0) < req.min_score:
                        continue
                    
                    # Filter output fields based on request
                    filtered_item = {
                        "id": item["id"],
                        "score": item.get("score", 0.0),
                    }
                    
                    if req.include_metadata and "metadata" in item:
                        filtered_item["metadata"] = item["metadata"]
                    
                    if req.include_text and "document" in item:
                        filtered_item["document"] = item["document"]
                    
                    filtered_results.append(filtered_item)
                    
                    # Stop if we have enough results
                    if len(filtered_results) >= req.limit:
                        break
                
                result["data"] = filtered_results
                result["count"] = len(filtered_results)
                result["reference_vector_id"] = req.vector_id
                if req.include_metadata and vector_record.metadata:
                    result["reference_metadata"] = vector_record.metadata
            
            # Record usage
            duration_ms = int((time.time() - start_time) * 1000)
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="find_similar",
                    collection_name=collection,
                    duration_ms=duration_ms,
                    status="success",
                    metadata={
                        "result_count": result.get("count", 0),
                        "vector_id": req.vector_id,
                        "had_filter": req.metadata_filter is not None,
                        "min_score": req.min_score
                    }
                )
            
            return result
        except HTTPException:
            raise
        except ValueError as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="find_similar",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e), "vector_id": req.vector_id}
                )
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="find_similar",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e), "vector_id": req.vector_id}
                )
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.delete("/projects/{project_id}/collections/{collection}/vectors/{vector_id}")
    def delete_vector(
        project_id: str,
        collection: str,
        vector_id: str,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Delete a vector from a collection.
        
        Soft-deletes the specified vector. The vector will no longer
        appear in search results.
        Requires write:vectors permission and project access.
        """
        start_time = time.time()
        auth.require_permission("write:vectors")
        
        # Check project access
        if not auth.can_access_project(project_id):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to project '{project_id}'",
            )
        
        try:
            result = delete_vector_uc.execute(
                project_id=project_id,
                collection=collection,
                vector_id=vector_id,
            )
            
            # Record usage
            duration_ms = int((time.time() - start_time) * 1000)
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="delete_vector",
                    collection_name=collection,
                    duration_ms=duration_ms,
                    status="success"
                )
            
            return result
        except ValueError as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="delete_vector",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="delete_vector",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.put("/projects/{project_id}/collections/{collection}/vectors/{vector_id}")
    def upsert_vector(
        project_id: str,
        collection: str,
        vector_id: str,
        req: UpsertVectorRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Upsert (update or insert) a vector.
        
        Updates the vector if it exists, inserts it if it doesn't.
        Useful for maintaining up-to-date embeddings.
        Requires write:vectors permission and project access.
        """
        start_time = time.time()
        auth.require_permission("write:vectors")
        
        # Check project access
        if not auth.can_access_project(project_id):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied to project '{project_id}'",
            )
        
        # Check quota
        quota_storage = get_quota_storage()
        if quota_storage:
            allowed, reason = quota_storage.check_quota(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="add_vector",
                vector_count=1
            )
            if not allowed:
                usage_storage = get_usage_storage()
                if usage_storage:
                    usage_storage.record_operation(
                        user_id=auth.user_id,
                        project_id=project_id,
                        operation_type="upsert_vector",
                        collection_name=collection,
                        status="quota_exceeded",
                        metadata={"reason": reason}
                    )
                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
        
        try:
            # Try to delete existing vector first (soft delete)
            try:
                delete_vector_uc.execute(
                    project_id=project_id,
                    collection=collection,
                    vector_id=vector_id,
                )
                was_update = True
            except:
                was_update = False
            
            # Add the new/updated vector
            result = add_vector_uc.execute(
                project_id=project_id,
                collection=collection,
                vector_id=req.id if req.id else vector_id,
                embedding=req.embedding,
                metadata=req.metadata,
                document=req.document,
                include_debug=False,
            )
            
            # Record usage
            duration_ms = int((time.time() - start_time) * 1000)
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="upsert_vector",
                    collection_name=collection,
                    payload_size=len(str(req.embedding)),
                    duration_ms=duration_ms,
                    status="success",
                    metadata={"was_update": was_update}
                )
            
            return {
                "status": "ok",
                "operation": "update" if was_update else "insert",
                "vector_id": vector_id,
                **result
            }
        except ValueError as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="upsert_vector",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="upsert_vector",
                    collection_name=collection,
                    status="failure",
                    metadata={"error": str(e)}
                )
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.post("/projects/{project_id}/collections/{collection}/batch/add")
    def batch_add_vectors(
        project_id: str,
        collection: str,
        req: BatchAddRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Add multiple vectors in a single batch operation.
        
        Adds multiple vectors to a collection efficiently. Each vector is processed
        independently - some may succeed while others fail. Returns detailed results
        for each vector.
        
        Features:
        - Processes up to 1000 vectors per request
        - Individual success/failure tracking
        - Quota enforcement before batch execution
        - Usage tracking for batch operation
        - Continues processing even if some vectors fail
        
        Args:
            project_id: Project identifier
            collection: Collection name
            req: Batch request with list of vectors
            auth: Authentication context
            
        Returns:
            BatchOperationResponse with success/failure details
        """
        start_time = time.time()
        
        # Check permissions
        auth.require_project_access(project_id)
        
        # Check quota before batch operation
        quota_storage = get_quota_storage()
        if quota_storage:
            allowed, reason = quota_storage.check_quota(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="add_vector",
                vector_count=len(req.vectors)
            )
            if not allowed:
                # Record quota exceeded
                usage_storage = get_usage_storage()
                if usage_storage:
                    usage_storage.record_operation(
                        user_id=auth.user_id,
                        project_id=project_id,
                        operation_type="batch_add_vector",
                        collection_name=collection,
                        vector_count=len(req.vectors),
                        status="quota_exceeded",
                        metadata={"reason": reason}
                    )
                raise HTTPException(status_code=429, detail=reason)
        
        # Process each vector
        results = []
        successful = 0
        failed = 0
        
        for vector in req.vectors:
            try:
                add_vector_uc.execute(
                    project_id=project_id,
                    collection=collection,
                    vector_id=vector.id,
                    embedding=vector.embedding,
                    metadata=vector.metadata,
                    document=vector.document,
                    include_debug=False,
                )
                results.append(BatchOperationResult(
                    success=True,
                    vector_id=vector.id
                ))
                successful += 1
            except Exception as e:
                results.append(BatchOperationResult(
                    success=False,
                    vector_id=vector.id,
                    error=str(e)
                ))
                failed += 1
        
        # Record usage
        duration_ms = int((time.time() - start_time) * 1000)
        usage_storage = get_usage_storage()
        if usage_storage:
            total_payload_size = sum(len(str(v.embedding)) for v in req.vectors)
            usage_storage.record_operation(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="batch_add_vector",
                collection_name=collection,
                vector_count=len(req.vectors),
                payload_size=total_payload_size,
                duration_ms=duration_ms,
                status="success" if failed == 0 else "partial_failure",
                metadata={
                    "total": len(req.vectors),
                    "successful": successful,
                    "failed": failed
                }
            )
        
        return BatchOperationResponse(
            total=len(req.vectors),
            successful=successful,
            failed=failed,
            results=results,
            duration_ms=duration_ms
        )
    
    @router.put("/projects/{project_id}/collections/{collection}/batch/update")
    def batch_update_vectors(
        project_id: str,
        collection: str,
        req: BatchUpdateRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Update multiple vectors in a single batch operation (upsert semantics).
        
        Updates or inserts multiple vectors. For each vector, attempts to delete
        the existing version (if any) then adds the new version. This provides
        upsert semantics for bulk operations.
        
        Features:
        - Processes up to 1000 vectors per request
        - Upsert semantics (update if exists, insert if not)
        - Individual success/failure tracking
        - Usage tracking for batch operation
        - Continues processing even if some vectors fail
        
        Args:
            project_id: Project identifier
            collection: Collection name
            req: Batch request with list of vectors
            auth: Authentication context
            
        Returns:
            BatchOperationResponse with success/failure details
        """
        start_time = time.time()
        
        # Check permissions
        auth.require_project_access(project_id)
        
        # Process each vector (upsert = delete + add)
        results = []
        successful = 0
        failed = 0
        updates = 0
        inserts = 0
        
        for vector in req.vectors:
            try:
                # Try to delete first (silently fail if not exists)
                was_update = False
                try:
                    delete_vector_uc.execute(
                        project_id=project_id,
                        collection=collection,
                        vector_id=vector.id,
                    )
                    was_update = True
                    updates += 1
                except:
                    inserts += 1
                
                # Add the vector
                add_vector_uc.execute(
                    project_id=project_id,
                    collection=collection,
                    vector_id=vector.id,
                    embedding=vector.embedding,
                    metadata=vector.metadata,
                    document=vector.document,
                    include_debug=False,
                )
                
                results.append(BatchOperationResult(
                    success=True,
                    vector_id=vector.id
                ))
                successful += 1
            except Exception as e:
                results.append(BatchOperationResult(
                    success=False,
                    vector_id=vector.id,
                    error=str(e)
                ))
                failed += 1
        
        # Record usage
        duration_ms = int((time.time() - start_time) * 1000)
        usage_storage = get_usage_storage()
        if usage_storage:
            total_payload_size = sum(len(str(v.embedding)) for v in req.vectors)
            usage_storage.record_operation(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="batch_update_vector",
                collection_name=collection,
                vector_count=len(req.vectors),
                payload_size=total_payload_size,
                duration_ms=duration_ms,
                status="success" if failed == 0 else "partial_failure",
                metadata={
                    "total": len(req.vectors),
                    "successful": successful,
                    "failed": failed,
                    "updates": updates,
                    "inserts": inserts
                }
            )
        
        return BatchOperationResponse(
            total=len(req.vectors),
            successful=successful,
            failed=failed,
            results=results,
            duration_ms=duration_ms
        )
    
    @router.delete("/projects/{project_id}/collections/{collection}/batch/delete")
    def batch_delete_vectors(
        project_id: str,
        collection: str,
        req: BatchDeleteRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Delete multiple vectors in a single batch operation.
        
        Deletes multiple vectors by their IDs. Each deletion is processed
        independently - some may succeed while others fail (e.g., if vector
        doesn't exist). Returns detailed results for each vector.
        
        Features:
        - Processes up to 1000 vectors per request
        - Individual success/failure tracking
        - Usage tracking for batch operation
        - Continues processing even if some deletions fail
        
        Args:
            project_id: Project identifier
            collection: Collection name
            req: Batch request with list of vector IDs
            auth: Authentication context
            
        Returns:
            BatchOperationResponse with success/failure details
        """
        start_time = time.time()
        
        # Check permissions
        auth.require_project_access(project_id)
        
        # Process each deletion
        results = []
        successful = 0
        failed = 0
        
        for vector_id in req.vector_ids:
            try:
                delete_vector_uc.execute(
                    project_id=project_id,
                    collection=collection,
                    vector_id=vector_id,
                )
                results.append(BatchOperationResult(
                    success=True,
                    vector_id=vector_id
                ))
                successful += 1
            except Exception as e:
                results.append(BatchOperationResult(
                    success=False,
                    vector_id=vector_id,
                    error=str(e)
                ))
                failed += 1
        
        # Record usage
        duration_ms = int((time.time() - start_time) * 1000)
        usage_storage = get_usage_storage()
        if usage_storage:
            usage_storage.record_operation(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="batch_delete_vector",
                collection_name=collection,
                vector_count=len(req.vector_ids),
                duration_ms=duration_ms,
                status="success" if failed == 0 else "partial_failure",
                metadata={
                    "total": len(req.vector_ids),
                    "successful": successful,
                    "failed": failed
                }
            )
        
        return BatchOperationResponse(
            total=len(req.vector_ids),
            successful=successful,
            failed=failed,
            results=results,
            duration_ms=duration_ms
        )
    
    # ============================================================================
    # SIMPLE API FOR BEGINNERS (No Vector Knowledge Required)
    # ============================================================================
    
    @router.post("/simple/{project_id}/collections/{collection}/add")
    def simple_add_text(
        project_id: str,
        collection: str,
        req: SimpleAddTextRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """🚀 Simple API: Add text without dealing with vectors.
        
        **For Beginners**: This endpoint automatically converts your text into vectors.
        You don't need to understand embeddings or machine learning - just send text!
        
        Example:
        ```json
        {
          "id": "doc_123",
          "text": "Python is a programming language",
          "metadata": {"category": "programming", "level": "beginner"}
        }
        ```
        
        The system will:
        1. Automatically convert your text to a vector (embedding)
        2. Store it in the collection
        3. Make it searchable
        
        Args:
            project_id: Your project name
            collection: Collection name to store the text
            req: Text content with ID and optional metadata
            auth: Authentication (automatic)
            
        Returns:
            Success response with vector ID
        """
        start_time = time.time()
        
        # Check permissions and project access
        auth.require_project_access(project_id)
        
        # Check quota
        quota_storage = get_quota_storage()
        if quota_storage:
            quota_ok, reason = quota_storage.check_quota(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="add_vector",
                vector_count=1
            )
            if not quota_ok:
                usage_storage = get_usage_storage()
                if usage_storage:
                    usage_storage.record_operation(
                        user_id=auth.user_id,
                        project_id=project_id,
                        operation_type="simple_add_text",
                        collection_name=collection,
                        status="quota_exceeded",
                        metadata={"reason": reason}
                    )
                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
        
        try:
            # Generate embedding from text
            from ...usecases.generate_embedding import GenerateEmbeddingUC
            from ...bootstrap import build_usecase
            
            embedding_uc = build_usecase()
            
            # Use 'document' task type for storing documents
            embedding_result = embedding_uc.embed(req.text, task_type="document", normalize=True)
            vector = embedding_result["embedding"]
            
            # Add vector to collection
            result = add_vector_uc.execute(
                project_id=project_id,
                collection=collection,
                vector_id=req.id,
                embedding=vector,
                metadata=req.metadata,
                document=req.text,  # Store original text
            )
            
            # Record usage
            duration_ms = int((time.time() - start_time) * 1000)
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="simple_add_text",
                    collection_name=collection,
                    vector_count=1,
                    duration_ms=duration_ms,
                    status="success",
                    metadata={
                        "text_length": len(req.text),
                        "embedding_model": embedding_result.get("model", "unknown"),
                        "embedding_dimension": len(vector)
                    }
                )
            
            return {
                "success": True,
                "id": req.id,
                "project_id": project_id,
                "collection": collection,
                "text_length": len(req.text),
                "embedding_dimension": len(vector),
                "message": "Text successfully stored and made searchable!"
            }
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.post("/simple/{project_id}/collections/{collection}/search")
    def simple_search_text(
        project_id: str,
        collection: str,
        req: SimpleSearchTextRequest,
        auth: AuthContext = Depends(get_current_user),
    ):
        """🔍 Simple API: Search by text without dealing with vectors.
        
        **For Beginners**: Just send your search query as text, and we'll find similar documents.
        No need to understand vectors or embeddings!
        
        Example:
        ```json
        {
          "query": "programming languages",
          "limit": 5,
          "min_score": 0.7
        }
        ```
        
        Returns matching documents sorted by similarity (1.0 = perfect match, 0.0 = no match).
        
        Args:
            project_id: Your project name
            collection: Collection to search in
            req: Search query text and options
            auth: Authentication (automatic)
            
        Returns:
            List of matching documents with similarity scores
        """
        start_time = time.time()
        
        # Check permissions and project access
        auth.require_project_access(project_id)
        
        # Check quota
        quota_storage = get_quota_storage()
        if quota_storage:
            quota_ok, reason = quota_storage.check_quota(
                user_id=auth.user_id,
                project_id=project_id,
                operation_type="search_vectors"
            )
            if not quota_ok:
                usage_storage = get_usage_storage()
                if usage_storage:
                    usage_storage.record_operation(
                        user_id=auth.user_id,
                        project_id=project_id,
                        operation_type="simple_search_text",
                        collection_name=collection,
                        status="quota_exceeded",
                        metadata={"reason": reason}
                    )
                raise HTTPException(status_code=429, detail=f"Quota exceeded: {reason}")
        
        try:
            # Generate embedding from query text
            from ...usecases.generate_embedding import GenerateEmbeddingUC
            from ...bootstrap import build_usecase
            
            embedding_uc = build_usecase()
            
            # Use 'query' task type for search queries
            embedding_result = embedding_uc.embed(req.query, task_type="query", normalize=True)
            query_vector = embedding_result["embedding"]
            
            # Perform vector search
            result = search_vectors_uc.execute(
                project_id=project_id,
                collection=collection,
                query_vector=query_vector,
                limit=req.limit,
                include_debug=False,
            )
            
            # Apply minimum score filter and format results
            filtered_results = []
            if "data" in result:
                for item in result["data"]:
                    score = item.get("score", 0.0)
                    
                    # Convert distance to similarity (for cosine: similarity = 1 - distance)
                    # LanceDB returns distance, where lower = more similar
                    # We convert to similarity where higher = more similar (0.0 to 1.0)
                    similarity = max(0.0, min(1.0, 1.0 - score))
                    
                    # Apply minimum score threshold
                    if req.min_score and similarity < req.min_score:
                        continue
                    
                    filtered_results.append({
                        "id": item.get("id"),
                        "text": item.get("document", ""),
                        "metadata": item.get("metadata", {}),
                        "similarity": round(similarity, 4),  # Similarity score (0.0 to 1.0)
                    })
            
            # Record usage
            duration_ms = int((time.time() - start_time) * 1000)
            usage_storage = get_usage_storage()
            if usage_storage:
                usage_storage.record_operation(
                    user_id=auth.user_id,
                    project_id=project_id,
                    operation_type="simple_search_text",
                    collection_name=collection,
                    duration_ms=duration_ms,
                    status="success",
                    metadata={
                        "query_length": len(req.query),
                        "results_count": len(filtered_results),
                        "min_score": req.min_score
                    }
                )
            
            return {
                "success": True,
                "query": req.query,
                "results": filtered_results,
                "count": len(filtered_results),
                "message": f"Found {len(filtered_results)} similar documents"
            }
            
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    return router
