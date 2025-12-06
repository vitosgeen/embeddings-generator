"""Infrastructure adapters for Vector Database."""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

try:
    import lancedb
    import pyarrow as pa
except ImportError:
    lancedb = None
    pa = None

from ...domain.vdb import (
    ProjectId,
    CollectionName,
    CollectionConfig,
    VectorRecord,
    SearchResult,
    ShardInfo,
    DistanceMetric,
)
from ...ports.vdb_port import VectorStoragePort, ProjectStoragePort, ShardingPort


class HashSharding:
    """Hash-based sharding strategy."""
    
    def compute_shard(self, record_id: str, total_shards: int) -> int:
        """Compute shard using hash of record ID.
        
        Args:
            record_id: The unique identifier of the record
            total_shards: Total number of shards
            
        Returns:
            Shard ID (0-indexed)
        """
        hash_value = int(hashlib.md5(record_id.encode()).hexdigest(), 16)
        return hash_value % total_shards


class FileProjectStorage:
    """File-based project storage implementation."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _project_path(self, project_id: ProjectId) -> Path:
        return self.base_path / project_id.value
    
    def _project_meta_path(self, project_id: ProjectId) -> Path:
        return self._project_path(project_id) / "_project.json"
    
    def create_project(self, project_id: ProjectId, metadata: Dict[str, Any]) -> None:
        """Create a new project directory and metadata."""
        project_path = self._project_path(project_id)
        
        if project_path.exists():
            raise ValueError(f"Project '{project_id.value}' already exists")
        
        project_path.mkdir(parents=True, exist_ok=True)
        collections_path = project_path / "collections"
        collections_path.mkdir(exist_ok=True)
        
        meta = {
            "project_id": project_id.value,
            "created_at": int(datetime.now().timestamp()),
            "metadata": metadata,
        }
        
        with open(self._project_meta_path(project_id), 'w') as f:
            json.dump(meta, f, indent=2)
    
    def project_exists(self, project_id: ProjectId) -> bool:
        """Check if a project exists."""
        return self._project_meta_path(project_id).exists()
    
    def get_project_metadata(self, project_id: ProjectId) -> Dict[str, Any]:
        """Get project metadata."""
        if not self.project_exists(project_id):
            raise ValueError(f"Project '{project_id.value}' does not exist")
        
        with open(self._project_meta_path(project_id), 'r') as f:
            return json.load(f)
    
    def list_projects(self) -> List[str]:
        """List all project IDs."""
        projects = []
        for item in self.base_path.iterdir():
            if item.is_dir() and (item / "_project.json").exists():
                projects.append(item.name)
        return sorted(projects)


class LanceDBVectorStorage:
    """LanceDB-based vector storage with sharding."""
    
    def __init__(self, base_path: str, sharding: ShardingPort):
        if lancedb is None or pa is None:
            raise ImportError(
                "lancedb and pyarrow are required. "
                "Install with: pip install lancedb pyarrow"
            )
        
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.sharding = sharding
        self._dbs: Dict[str, Any] = {}  # Cache of LanceDB connections
    
    def _collection_path(self, project_id: ProjectId, collection: CollectionName) -> Path:
        return self.base_path / project_id.value / "collections" / collection.value
    
    def _config_path(self, project_id: ProjectId, collection: CollectionName) -> Path:
        return self._collection_path(project_id, collection) / "_config.json"
    
    def _shard_path(self, project_id: ProjectId, collection: CollectionName, shard_id: int) -> Path:
        return self._collection_path(project_id, collection) / f"shard_{shard_id}"
    
    def _get_db(self, shard_path: Path) -> Any:
        """Get or create LanceDB connection."""
        shard_key = str(shard_path)
        if shard_key not in self._dbs:
            shard_path.mkdir(parents=True, exist_ok=True)
            self._dbs[shard_key] = lancedb.connect(str(shard_path))
        return self._dbs[shard_key]
    
    def _load_config(self, project_id: ProjectId, collection: CollectionName) -> CollectionConfig:
        """Load collection configuration."""
        config_path = self._config_path(project_id, collection)
        
        if not config_path.exists():
            raise ValueError(f"Collection '{collection.value}' does not exist")
        
        with open(config_path, 'r') as f:
            data = json.load(f)
        
        return CollectionConfig(
            name=CollectionName(data["name"]),
            dimension=data["dimension"],
            metric=DistanceMetric(data["metric"]),
            shards=data["shards"],
            description=data.get("description"),
            created_at=datetime.fromtimestamp(data["created_at"]),
        )
    
    def _get_metric_type(self, metric: DistanceMetric) -> str:
        """Convert our metric to LanceDB metric."""
        mapping = {
            DistanceMetric.COSINE: "cosine",
            DistanceMetric.DOT: "dot",
            DistanceMetric.L2: "L2",
        }
        return mapping[metric]
    
    def create_collection(
        self,
        project_id: ProjectId,
        config: CollectionConfig,
    ) -> None:
        """Create a new collection with shards."""
        collection_path = self._collection_path(project_id, config.name)
        
        if collection_path.exists():
            raise ValueError(f"Collection '{config.name.value}' already exists")
        
        collection_path.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        with open(self._config_path(project_id, config.name), 'w') as f:
            json.dump(config.to_dict(), f, indent=2)
        
        # Initialize all shards
        for shard_id in range(config.shards):
            shard_path = self._shard_path(project_id, config.name, shard_id)
            shard_path.mkdir(parents=True, exist_ok=True)
    
    def add_vector(
        self,
        project_id: ProjectId,
        collection: CollectionName,
        record: VectorRecord,
    ) -> int:
        """Add a vector to the appropriate shard."""
        config = self._load_config(project_id, collection)
        
        # Validate dimension
        if record.dimension != config.dimension:
            raise ValueError(
                f"Vector dimension {record.dimension} does not match "
                f"collection dimension {config.dimension}"
            )
        
        # Compute shard
        shard_id = self.sharding.compute_shard(record.id, config.shards)
        shard_path = self._shard_path(project_id, collection, shard_id)
        
        # Get LanceDB connection
        db = self._get_db(shard_path)
        
        # Prepare data
        data = [{
            "id": record.id,
            "vector": record.vector,
            "metadata": json.dumps(record.metadata),
            "document": record.document or "",
            "created_at": int(record.created_at.timestamp()),
            "updated_at": int(record.updated_at.timestamp()),
            "deleted": record.deleted,
        }]
        
        # Create or append to table
        table_name = "vectors"
        try:
            table = db.open_table(table_name)
            table.add(data)
        except Exception:
            # Table doesn't exist, create it
            # Define schema
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), config.dimension)),
                pa.field("metadata", pa.string()),
                pa.field("document", pa.string()),
                pa.field("created_at", pa.int64()),
                pa.field("updated_at", pa.int64()),
                pa.field("deleted", pa.bool_()),
            ])
            db.create_table(table_name, data=data, schema=schema)
        
        return shard_id
    
    def search_vectors(
        self,
        project_id: ProjectId,
        collection: CollectionName,
        query_vector: List[float],
        limit: int = 10,
    ) -> tuple[List[SearchResult], List[ShardInfo]]:
        """Search for similar vectors across all shards."""
        config = self._load_config(project_id, collection)
        
        # Validate dimension
        if len(query_vector) != config.dimension:
            raise ValueError(
                f"Query vector dimension {len(query_vector)} does not match "
                f"collection dimension {config.dimension}"
            )
        
        all_results = []
        shard_info = []
        
        # Search each shard in parallel (sequential for now, can be parallelized)
        for shard_id in range(config.shards):
            shard_path = self._shard_path(project_id, collection, shard_id)
            
            if not shard_path.exists():
                continue
            
            start_time = time.time()
            
            try:
                db = self._get_db(shard_path)
                table = db.open_table("vectors")
                
                # Perform search
                results = table.search(query_vector).metric(self._get_metric_type(config.metric)).limit(limit).to_list()
                
                search_time = (time.time() - start_time) * 1000  # milliseconds
                
                # Convert results
                for row in results:
                    if not row.get("deleted", False):  # Filter out soft-deleted
                        all_results.append(SearchResult(
                            id=row["id"],
                            score=float(row.get("_distance", 0.0)),
                            metadata=json.loads(row.get("metadata", "{}")),
                            document=row.get("document") if row.get("document") else None,
                        ))
                
                shard_info.append(ShardInfo(
                    shard_id=shard_id,
                    record_count=len(results),
                    search_time_ms=search_time,
                ))
            
            except Exception:
                # Shard might be empty or not initialized
                shard_info.append(ShardInfo(
                    shard_id=shard_id,
                    record_count=0,
                    search_time_ms=0.0,
                ))
        
        # Sort all results by score and take top-k
        all_results.sort(key=lambda x: x.score, reverse=True)
        return all_results[:limit], shard_info
    
    def delete_vector(
        self,
        project_id: ProjectId,
        collection: CollectionName,
        vector_id: str,
    ) -> bool:
        """Delete a vector (soft delete)."""
        config = self._load_config(project_id, collection)
        
        # Compute which shard contains this vector
        shard_id = self.sharding.compute_shard(vector_id, config.shards)
        shard_path = self._shard_path(project_id, collection, shard_id)
        
        if not shard_path.exists():
            return False
        
        try:
            db = self._get_db(shard_path)
            table = db.open_table("vectors")
            
            # LanceDB doesn't support soft delete directly, so we'd need to:
            # 1. Read the record
            # 2. Update it with deleted=True
            # For simplicity, we'll use delete for now
            table.delete(f"id = '{vector_id}'")
            return True
        
        except Exception:
            return False
    
    def get_collection_info(
        self,
        project_id: ProjectId,
        collection: CollectionName,
    ) -> Dict[str, Any]:
        """Get collection metadata and statistics."""
        config = self._load_config(project_id, collection)
        
        shard_counts = {}
        total_records = 0
        
        for shard_id in range(config.shards):
            shard_path = self._shard_path(project_id, collection, shard_id)
            
            if not shard_path.exists():
                shard_counts[str(shard_id)] = 0
                continue
            
            try:
                db = self._get_db(shard_path)
                table = db.open_table("vectors")
                count = table.count_rows()
                shard_counts[str(shard_id)] = count
                total_records += count
            except Exception:
                shard_counts[str(shard_id)] = 0
        
        return {
            "name": config.name.value,
            "dimension": config.dimension,
            "metric": config.metric.value,
            "shards": config.shards,
            "description": config.description,
            "total_records": total_records,
            "shard_counts": shard_counts,
        }
    
    def list_collections(self, project_id: ProjectId) -> List[str]:
        """List all collections in a project."""
        collections_path = self.base_path / project_id.value / "collections"
        
        if not collections_path.exists():
            return []
        
        collections = []
        for item in collections_path.iterdir():
            if item.is_dir() and (item / "_config.json").exists():
                collections.append(item.name)
        
        return sorted(collections)
    
    def collection_exists(
        self,
        project_id: ProjectId,
        collection: CollectionName,
    ) -> bool:
        """Check if a collection exists."""
        return self._config_path(project_id, collection).exists()
