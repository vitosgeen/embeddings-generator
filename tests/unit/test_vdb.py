"""Basic VDB service tests."""

import pytest
from datetime import datetime

from app.domain.vdb import (
    ProjectId,
    CollectionName,
    CollectionConfig,
    VectorRecord,
    DistanceMetric,
)
from app.adapters.infra.vdb_storage import HashSharding


class TestVDBDomain:
    """Test VDB domain models."""
    
    def test_project_id_creation(self):
        """Test ProjectId value object creation."""
        project_id = ProjectId("test_project_123")
        assert project_id.value == "test_project_123"
    
    def test_project_id_validation(self):
        """Test ProjectId validation."""
        with pytest.raises(ValueError):
            ProjectId("")
        
        with pytest.raises(ValueError):
            ProjectId("invalid project!")
    
    def test_collection_name_creation(self):
        """Test CollectionName value object creation."""
        name = CollectionName("my_collection")
        assert name.value == "my_collection"
    
    def test_collection_config_creation(self):
        """Test CollectionConfig creation."""
        config = CollectionConfig(
            name=CollectionName("test_collection"),
            dimension=384,
            metric=DistanceMetric.COSINE,
            shards=4,
            description="Test collection",
        )
        
        assert config.name.value == "test_collection"
        assert config.dimension == 384
        assert config.metric == DistanceMetric.COSINE
        assert config.shards == 4
        assert config.description == "Test collection"
    
    def test_collection_config_validation(self):
        """Test CollectionConfig validation."""
        with pytest.raises(ValueError):
            CollectionConfig(
                name=CollectionName("test"),
                dimension=0,  # Invalid
                metric=DistanceMetric.COSINE,
                shards=4,
            )
        
        with pytest.raises(ValueError):
            CollectionConfig(
                name=CollectionName("test"),
                dimension=384,
                metric=DistanceMetric.COSINE,
                shards=0,  # Invalid
            )
    
    def test_vector_record_creation(self):
        """Test VectorRecord creation."""
        record = VectorRecord(
            id="vec_001",
            vector=[0.1, 0.2, 0.3],
            metadata={"type": "test"},
            document="Test document",
        )
        
        assert record.id == "vec_001"
        assert record.dimension == 3
        assert record.metadata == {"type": "test"}
        assert record.document == "Test document"
        assert not record.deleted
    
    def test_vector_record_validation(self):
        """Test VectorRecord validation."""
        with pytest.raises(ValueError):
            VectorRecord(id="", vector=[0.1, 0.2])
        
        with pytest.raises(ValueError):
            VectorRecord(id="vec_001", vector=[])


class TestHashSharding:
    """Test hash-based sharding."""
    
    def test_compute_shard(self):
        """Test shard computation."""
        sharding = HashSharding()
        
        # Test consistent hashing
        shard1 = sharding.compute_shard("test_id_1", 4)
        shard2 = sharding.compute_shard("test_id_1", 4)
        assert shard1 == shard2
        
        # Test shard is in valid range
        for i in range(100):
            shard = sharding.compute_shard(f"id_{i}", 4)
            assert 0 <= shard < 4
    
    def test_shard_distribution(self):
        """Test that sharding distributes records reasonably."""
        sharding = HashSharding()
        shards_count = 4
        
        # Create many IDs and count distribution
        shard_counts = {i: 0 for i in range(shards_count)}
        
        for i in range(1000):
            shard = sharding.compute_shard(f"id_{i}", shards_count)
            shard_counts[shard] += 1
        
        # Each shard should have roughly 25% (allow 15-35% range)
        for count in shard_counts.values():
            assert 150 <= count <= 350, "Sharding distribution is too uneven"
