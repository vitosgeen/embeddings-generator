"""Ports (interfaces) for Vector Database components."""

from typing import List, Protocol, Dict, Any, Optional
from datetime import datetime

from ..domain.vdb import (
    ProjectId,
    CollectionName,
    CollectionConfig,
    VectorRecord,
    SearchResult,
    ShardInfo,
)


class ShardingPort(Protocol):
    """Protocol for sharding strategies."""
    
    def compute_shard(self, record_id: str, total_shards: int) -> int:
        """Compute which shard a record belongs to.
        
        Args:
            record_id: The unique identifier of the record
            total_shards: Total number of shards
            
        Returns:
            Shard ID (0-indexed)
        """
        ...


class VectorStoragePort(Protocol):
    """Protocol for vector storage backend."""
    
    def create_collection(
        self,
        project_id: ProjectId,
        config: CollectionConfig,
    ) -> None:
        """Create a new collection with sharding.
        
        Args:
            project_id: Project identifier
            config: Collection configuration
        """
        ...
    
    def add_vector(
        self,
        project_id: ProjectId,
        collection: CollectionName,
        record: VectorRecord,
    ) -> int:
        """Add a vector to the appropriate shard.
        
        Args:
            project_id: Project identifier
            collection: Collection name
            record: Vector record to add
            
        Returns:
            Shard ID where the vector was stored
        """
        ...
    
    def search_vectors(
        self,
        project_id: ProjectId,
        collection: CollectionName,
        query_vector: List[float],
        limit: int = 10,
    ) -> tuple[List[SearchResult], List[ShardInfo]]:
        """Search for similar vectors across all shards.
        
        Args:
            project_id: Project identifier
            collection: Collection name
            query_vector: Query vector for similarity search
            limit: Maximum number of results to return
            
        Returns:
            Tuple of (search results, shard info for debug)
        """
        ...
    
    def delete_vector(
        self,
        project_id: ProjectId,
        collection: CollectionName,
        vector_id: str,
    ) -> bool:
        """Delete a vector (soft delete).
        
        Args:
            project_id: Project identifier
            collection: Collection name
            vector_id: ID of vector to delete
            
        Returns:
            True if deleted, False if not found
        """
        ...
    
    def get_collection_info(
        self,
        project_id: ProjectId,
        collection: CollectionName,
    ) -> Dict[str, Any]:
        """Get collection metadata and statistics.
        
        Args:
            project_id: Project identifier
            collection: Collection name
            
        Returns:
            Dictionary with collection info
        """
        ...
    
    def list_collections(self, project_id: ProjectId) -> List[str]:
        """List all collections in a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            List of collection names
        """
        ...
    
    def collection_exists(
        self,
        project_id: ProjectId,
        collection: CollectionName,
    ) -> bool:
        """Check if a collection exists.
        
        Args:
            project_id: Project identifier
            collection: Collection name
            
        Returns:
            True if collection exists
        """
        ...


class ProjectStoragePort(Protocol):
    """Protocol for project-level storage operations."""
    
    def create_project(self, project_id: ProjectId, metadata: Dict[str, Any]) -> None:
        """Create a new project.
        
        Args:
            project_id: Project identifier
            metadata: Project metadata
        """
        ...
    
    def project_exists(self, project_id: ProjectId) -> bool:
        """Check if a project exists.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if project exists
        """
        ...
    
    def get_project_metadata(self, project_id: ProjectId) -> Dict[str, Any]:
        """Get project metadata.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Project metadata dictionary
        """
        ...
    
    def list_projects(self) -> List[str]:
        """List all project IDs.
        
        Returns:
            List of project ID strings
        """
        ...
