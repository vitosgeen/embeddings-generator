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
    
    return router
