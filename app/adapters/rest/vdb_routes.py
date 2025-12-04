"""REST API routes for Vector Database Service."""

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
from ...auth import get_current_user


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
        current_user: str = Depends(get_current_user),
    ):
        """Create a new project.
        
        Creates a new isolated project for storing vector collections.
        Each project has its own directory and metadata.
        """
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
    def list_projects(current_user: str = Depends(get_current_user)):
        """List all projects.
        
        Returns a list of all project IDs in the vector database.
        """
        try:
            return list_projects_uc.execute()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.get("/projects/{project_id}/collections")
    def list_collections(
        project_id: str,
        current_user: str = Depends(get_current_user),
    ):
        """List all collections in a project.
        
        Returns a list of collection names for the specified project.
        """
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
        current_user: str = Depends(get_current_user),
    ):
        """Create a new collection in a project.
        
        Creates a new vector collection with the specified configuration.
        The collection will be automatically sharded for scalability.
        """
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
        current_user: str = Depends(get_current_user),
    ):
        """Add a vector to a collection.
        
        Adds a new vector to the specified collection. The vector will be
        automatically assigned to the appropriate shard based on its ID.
        """
        try:
            return add_vector_uc.execute(
                project_id=project_id,
                collection=collection,
                vector_id=req.id,
                embedding=req.embedding,
                metadata=req.metadata,
                document=req.document,
                include_debug=include_debug,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.post("/projects/{project_id}/collections/{collection}/search")
    def search_vectors(
        project_id: str,
        collection: str,
        req: SearchRequest,
        include_debug: bool = Query(default=False, description="Include debug information"),
        current_user: str = Depends(get_current_user),
    ):
        """Search for similar vectors.
        
        Performs similarity search across all shards in the collection
        and returns the top-k most similar vectors.
        """
        try:
            return search_vectors_uc.execute(
                project_id=project_id,
                collection=collection,
                query_vector=req.query_vector,
                limit=req.limit,
                include_debug=include_debug,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    @router.delete("/projects/{project_id}/collections/{collection}/vectors/{vector_id}")
    def delete_vector(
        project_id: str,
        collection: str,
        vector_id: str,
        current_user: str = Depends(get_current_user),
    ):
        """Delete a vector from a collection.
        
        Soft-deletes the specified vector. The vector will no longer
        appear in search results.
        """
        try:
            return delete_vector_uc.execute(
                project_id=project_id,
                collection=collection,
                vector_id=vector_id,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    return router
