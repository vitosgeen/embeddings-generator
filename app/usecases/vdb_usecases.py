"""Use cases for Vector Database operations."""

from typing import Dict, Any, List, Optional
from datetime import datetime

from ..domain.vdb import (
    ProjectId,
    CollectionName,
    CollectionConfig,
    VectorRecord,
    SearchResult,
    DistanceMetric,
)
from ..ports.vdb_port import VectorStoragePort, ProjectStoragePort


class CreateProjectUC:
    """Use case for creating a new project."""
    
    def __init__(self, project_storage: ProjectStoragePort):
        self.project_storage = project_storage
    
    def execute(self, project_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new project.
        
        Args:
            project_id: Unique project identifier
            metadata: Optional project metadata
            
        Returns:
            Dictionary with project creation status
            
        Raises:
            ValueError: If project already exists or invalid ID
        """
        pid = ProjectId(project_id)
        
        if self.project_storage.project_exists(pid):
            raise ValueError(f"Project '{project_id}' already exists")
        
        self.project_storage.create_project(pid, metadata or {})
        
        return {
            "status": "ok",
            "project_id": project_id,
            "created_at": int(datetime.now().timestamp()),
        }


class ListProjectsUC:
    """Use case for listing all projects."""
    
    def __init__(self, project_storage: ProjectStoragePort):
        self.project_storage = project_storage
    
    def execute(self) -> Dict[str, Any]:
        """List all projects.
        
        Returns:
            Dictionary with list of project IDs
        """
        projects = self.project_storage.list_projects()
        return {
            "status": "ok",
            "projects": projects,
            "count": len(projects),
        }


class CreateCollectionUC:
    """Use case for creating a new collection."""
    
    def __init__(
        self,
        vector_storage: VectorStoragePort,
        project_storage: ProjectStoragePort,
    ):
        self.vector_storage = vector_storage
        self.project_storage = project_storage
    
    def execute(
        self,
        project_id: str,
        name: str,
        dimension: int,
        metric: str = "cosine",
        shards: int = 4,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new collection.
        
        Args:
            project_id: Project identifier
            name: Collection name
            dimension: Vector dimension
            metric: Distance metric (cosine, dot, L2)
            shards: Number of shards
            description: Optional description
            
        Returns:
            Dictionary with collection creation status
            
        Raises:
            ValueError: If project doesn't exist or collection already exists
        """
        pid = ProjectId(project_id)
        
        if not self.project_storage.project_exists(pid):
            raise ValueError(f"Project '{project_id}' does not exist")
        
        cname = CollectionName(name)
        
        if self.vector_storage.collection_exists(pid, cname):
            raise ValueError(f"Collection '{name}' already exists in project '{project_id}'")
        
        config = CollectionConfig(
            name=cname,
            dimension=dimension,
            metric=DistanceMetric(metric),
            shards=shards,
            description=description,
        )
        
        self.vector_storage.create_collection(pid, config)
        
        return {
            "status": "ok",
            "collection": name,
            "dimension": dimension,
            "metric": metric,
            "shards": shards,
        }


class ListCollectionsUC:
    """Use case for listing collections in a project."""
    
    def __init__(
        self,
        vector_storage: VectorStoragePort,
        project_storage: ProjectStoragePort,
    ):
        self.vector_storage = vector_storage
        self.project_storage = project_storage
    
    def execute(self, project_id: str) -> Dict[str, Any]:
        """List all collections in a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Dictionary with list of collections
            
        Raises:
            ValueError: If project doesn't exist
        """
        pid = ProjectId(project_id)
        
        if not self.project_storage.project_exists(pid):
            raise ValueError(f"Project '{project_id}' does not exist")
        
        collections = self.vector_storage.list_collections(pid)
        
        return {
            "status": "ok",
            "project_id": project_id,
            "collections": collections,
            "count": len(collections),
        }


class AddVectorUC:
    """Use case for adding a vector to a collection."""
    
    def __init__(
        self,
        vector_storage: VectorStoragePort,
        project_storage: ProjectStoragePort,
    ):
        self.vector_storage = vector_storage
        self.project_storage = project_storage
    
    def execute(
        self,
        project_id: str,
        collection: str,
        vector_id: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        document: Optional[str] = None,
        include_debug: bool = False,
    ) -> Dict[str, Any]:
        """Add a vector to a collection.
        
        Args:
            project_id: Project identifier
            collection: Collection name
            vector_id: Unique vector identifier
            embedding: Vector embedding
            metadata: Optional metadata
            document: Optional raw text document
            include_debug: Include debug info in response
            
        Returns:
            Dictionary with addition status
            
        Raises:
            ValueError: If project/collection doesn't exist
        """
        pid = ProjectId(project_id)
        cname = CollectionName(collection)
        
        if not self.project_storage.project_exists(pid):
            raise ValueError(f"Project '{project_id}' does not exist")
        
        if not self.vector_storage.collection_exists(pid, cname):
            raise ValueError(f"Collection '{collection}' does not exist")
        
        record = VectorRecord(
            id=vector_id,
            vector=embedding,
            metadata=metadata or {},
            document=document,
        )
        
        shard_id = self.vector_storage.add_vector(pid, cname, record)
        
        result = {
            "status": "ok",
            "id": vector_id,
        }
        
        if include_debug:
            collection_info = self.vector_storage.get_collection_info(pid, cname)
            result["debug"] = {
                "shard": shard_id,
                "total_records_in_shard": collection_info.get("shard_counts", {}).get(str(shard_id), 0),
            }
        
        return result


class SearchVectorsUC:
    """Use case for searching similar vectors."""
    
    def __init__(
        self,
        vector_storage: VectorStoragePort,
        project_storage: ProjectStoragePort,
    ):
        self.vector_storage = vector_storage
        self.project_storage = project_storage
    
    def execute(
        self,
        project_id: str,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        include_debug: bool = False,
    ) -> Dict[str, Any]:
        """Search for similar vectors.
        
        Args:
            project_id: Project identifier
            collection: Collection name
            query_vector: Query vector
            limit: Maximum results to return
            include_debug: Include debug info in response
            
        Returns:
            Dictionary with search results
            
        Raises:
            ValueError: If project/collection doesn't exist
        """
        pid = ProjectId(project_id)
        cname = CollectionName(collection)
        
        if not self.project_storage.project_exists(pid):
            raise ValueError(f"Project '{project_id}' does not exist")
        
        if not self.vector_storage.collection_exists(pid, cname):
            raise ValueError(f"Collection '{collection}' does not exist")
        
        results, shard_info = self.vector_storage.search_vectors(
            pid, cname, query_vector, limit
        )
        
        response = {
            "data": [r.to_dict() for r in results],
        }
        
        if include_debug:
            collection_info = self.vector_storage.get_collection_info(pid, cname)
            response["debug"] = {
                "total_records": sum(collection_info.get("shard_counts", {}).values()),
                "shard_results": [s.to_dict() for s in shard_info],
            }
        
        return response


class DeleteVectorUC:
    """Use case for deleting a vector."""
    
    def __init__(
        self,
        vector_storage: VectorStoragePort,
        project_storage: ProjectStoragePort,
    ):
        self.vector_storage = vector_storage
        self.project_storage = project_storage
    
    def execute(
        self,
        project_id: str,
        collection: str,
        vector_id: str,
    ) -> Dict[str, Any]:
        """Delete a vector (soft delete).
        
        Args:
            project_id: Project identifier
            collection: Collection name
            vector_id: Vector identifier
            
        Returns:
            Dictionary with deletion status
            
        Raises:
            ValueError: If project/collection doesn't exist
        """
        pid = ProjectId(project_id)
        cname = CollectionName(collection)
        
        if not self.project_storage.project_exists(pid):
            raise ValueError(f"Project '{project_id}' does not exist")
        
        if not self.vector_storage.collection_exists(pid, cname):
            raise ValueError(f"Collection '{collection}' does not exist")
        
        deleted = self.vector_storage.delete_vector(pid, cname, vector_id)
        
        if not deleted:
            raise ValueError(f"Vector '{vector_id}' not found")
        
        return {
            "status": "ok",
            "id": vector_id,
            "deleted": True,
        }
