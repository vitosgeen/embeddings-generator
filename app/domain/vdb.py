"""Vector Database domain models."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class DistanceMetric(str, Enum):
    """Supported distance metrics for vector similarity."""
    COSINE = "cosine"
    DOT = "dot"
    L2 = "L2"


@dataclass(frozen=True)
class ProjectId:
    """Value object for project identifier."""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Project ID cannot be empty")
        # Validate alphanumeric + underscore/hyphen
        if not all(c.isalnum() or c in '_-' for c in self.value):
            raise ValueError("Project ID must be alphanumeric with underscores/hyphens")


@dataclass(frozen=True)
class CollectionName:
    """Value object for collection name."""
    value: str
    
    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValueError("Collection name cannot be empty")
        if not all(c.isalnum() or c in '_-' for c in self.value):
            raise ValueError("Collection name must be alphanumeric with underscores/hyphens")


@dataclass
class Project:
    """Represents a logical tenant in the vector database."""
    project_id: ProjectId
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id.value,
            "created_at": int(self.created_at.timestamp()),
            "metadata": self.metadata,
        }


@dataclass
class CollectionConfig:
    """Configuration for a vector collection."""
    name: CollectionName
    dimension: int
    metric: DistanceMetric
    shards: int
    description: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.dimension <= 0:
            raise ValueError("Dimension must be positive")
        if self.shards <= 0:
            raise ValueError("Shard count must be positive")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name.value,
            "dimension": self.dimension,
            "metric": self.metric.value,
            "shards": self.shards,
            "description": self.description,
            "created_at": int(self.created_at.timestamp()),
        }


@dataclass
class VectorRecord:
    """A single vector entry in the database."""
    id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    document: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    deleted: bool = False
    
    def __post_init__(self):
        if not self.id or not self.id.strip():
            raise ValueError("Vector ID cannot be empty")
        if not self.vector:
            raise ValueError("Vector cannot be empty")
    
    @property
    def dimension(self) -> int:
        return len(self.vector)
    
    def to_dict(self, include_debug: bool = False) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "metadata": self.metadata,
        }
        if self.document:
            result["document"] = self.document
        if include_debug:
            result["created_at"] = int(self.created_at.timestamp())
            result["updated_at"] = int(self.updated_at.timestamp())
            result["deleted"] = self.deleted
        return result


@dataclass
class SearchResult:
    """Result from a vector similarity search."""
    id: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    document: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "id": self.id,
            "score": self.score,
            "metadata": self.metadata,
        }
        if self.document:
            result["document"] = self.document
        return result


@dataclass
class ShardInfo:
    """Information about a specific shard."""
    shard_id: int
    record_count: int
    search_time_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "shard": self.shard_id,
            "count": self.record_count,
        }
        if self.search_time_ms is not None:
            result["search_time_ms"] = self.search_time_ms
        return result
