"""Unit tests for authentication domain logic."""

import pytest
from datetime import datetime, timedelta

from app.domain.auth import (
    Role,
    APIKeyManager,
    AuthContext,
    infer_role_from_account_name,
    mask_api_key,
    api_key_manager,
)


class TestRole:
    """Tests for Role enum and permissions."""
    
    def test_role_values(self):
        """Test that roles have correct string values."""
        assert Role.ADMIN.value == "admin"
        assert Role.MONITOR.value == "monitor"
        assert Role.SERVICE_APP.value == "service-app"
        assert Role.PROJECT_OWNER.value == "project-owner"
    
    def test_role_permissions_admin(self):
        """Test admin role has all permissions."""
        permissions = Role.ADMIN.get_permissions()
        assert "all" in permissions
        # Admin has wildcard 'all' permission
    
    def test_role_permissions_monitor(self):
        """Test monitor role has read-only permissions."""
        permissions = Role.MONITOR.get_permissions()
        assert "read:projects" in permissions
        assert "read:health" in permissions
        assert "read:metrics" in permissions
        assert "read:audit-logs" in permissions
        # Should not have write permissions
        assert "write:projects" not in permissions
        assert "write:collections" not in permissions
        assert "write:vectors" not in permissions
    
    def test_role_permissions_service_app(self):
        """Test service-app role has full operational permissions."""
        permissions = Role.SERVICE_APP.get_permissions()
        assert "read:projects" in permissions
        assert "write:projects" in permissions  # Can create projects
        assert "read:collections" in permissions
        assert "write:collections" in permissions
        assert "write:vectors" in permissions
        assert "delete:vectors" in permissions
        assert "search:vectors" in permissions
        # Should not have admin permissions
        assert "admin:users" not in permissions
    
    def test_role_permissions_project_owner(self):
        """Test project-owner role has project-scoped permissions."""
        permissions = Role.PROJECT_OWNER.get_permissions()
        assert "write:projects" in permissions  # Can create their own projects
        assert "read:project" in permissions  # Note: singular 'project'
        assert "read:collections" in permissions
        assert "write:collections" in permissions
        assert "write:vectors" in permissions
        assert "delete:vectors" in permissions
        assert "search:vectors" in permissions
        # Should not have admin permissions
        assert "admin:users" not in permissions


class TestAPIKeyManager:
    """Tests for API key generation and validation."""
    
    def test_generate_key_format(self):
        """Test that generated keys have correct format."""
        key = api_key_manager.generate_key("admin")
        
        # Should start with sk-admin-
        assert key.startswith("sk-admin-")
        
        # Should be 33 characters total: sk- (3) + admin- (6) + random (24)
        assert len(key) == 33
        
        # Should be alphanumeric after prefix
        parts = key.split("-", 2)
        assert parts[0] == "sk"
        assert parts[1] == "admin"
        assert len(parts[2]) == 24
        assert parts[2].isalnum()
    
    def test_generate_key_different_roles(self):
        """Test key generation for different roles."""
        admin_key = api_key_manager.generate_key("admin")
        monitor_key = api_key_manager.generate_key("monitor")
        service_key = api_key_manager.generate_key("service-app")
        
        assert admin_key.startswith("sk-admin-")
        assert monitor_key.startswith("sk-monitor-")
        # Note: service-app becomes serviceapp (no hyphen) in key format
        assert service_key.startswith("sk-serviceapp-")
    
    def test_generate_key_uniqueness(self):
        """Test that generated keys are unique."""
        keys = [api_key_manager.generate_key("admin") for _ in range(100)]
        assert len(keys) == len(set(keys))  # All unique
    
    def test_hash_key(self):
        """Test key hashing produces consistent results."""
        key = "sk-admin-abc123def456ghi789jkl"
        hash1 = api_key_manager.hash_key(key)
        hash2 = api_key_manager.hash_key(key)
        
        # Hashes should be different (due to salt)
        assert hash1 != hash2
        
        # But both should verify
        assert api_key_manager.verify_key(key, hash1)
        assert api_key_manager.verify_key(key, hash2)
    
    def test_hash_key_format(self):
        """Test that hashed keys have Argon2 format."""
        key = "sk-admin-test123"
        hashed = api_key_manager.hash_key(key)
        
        # Argon2 hashes start with $argon2id$
        assert hashed.startswith("$argon2id$")
    
    def test_verify_key_correct(self):
        """Test verifying correct key."""
        key = api_key_manager.generate_key("admin")
        hashed = api_key_manager.hash_key(key)
        
        assert api_key_manager.verify_key(key, hashed) is True
    
    def test_verify_key_incorrect(self):
        """Test verifying incorrect key."""
        key = api_key_manager.generate_key("admin")
        wrong_key = api_key_manager.generate_key("admin")
        hashed = api_key_manager.hash_key(key)
        
        assert api_key_manager.verify_key(wrong_key, hashed) is False
    
    def test_verify_key_invalid_hash(self):
        """Test verifying key with invalid hash format."""
        key = "sk-admin-test123"
        invalid_hash = "not-a-valid-hash"
        
        assert api_key_manager.verify_key(key, invalid_hash) is False
    
    def test_key_format_matches_pattern(self):
        """Test that generated keys match expected pattern."""
        key = api_key_manager.generate_key("admin")
        
        # Should match pattern: sk-{role}-{24 alphanumeric}
        assert key.startswith("sk-")
        parts = key.split("-", 2)
        assert len(parts) == 3
        assert parts[0] == "sk"
        assert len(parts[2]) == 24
        assert parts[2].isalnum()


class TestAuthContext:
    """Tests for AuthContext functionality."""
    
    @pytest.fixture
    def admin_context(self):
        """Create admin auth context."""
        return AuthContext(
            user_id=1,
            username="admin",
            role="admin",
            permissions=Role.get_permissions(Role.ADMIN),
            accessible_projects=["*"],
            api_key_id="sk-admin-test123",
        )
    
    @pytest.fixture
    def monitor_context(self):
        """Create monitor auth context."""
        return AuthContext(
            user_id=2,
            username="monitor",
            role="monitor",
            permissions=Role.get_permissions(Role.MONITOR),
            accessible_projects=["*"],
            api_key_id="sk-monitor-test456",
        )
    
    @pytest.fixture
    def project_owner_context(self):
        """Create project owner auth context."""
        return AuthContext(
            user_id=3,
            username="user1",
            role="project-owner",
            permissions=Role.get_permissions(Role.PROJECT_OWNER),
            accessible_projects=["project1", "project2"],
            api_key_id="sk-project-owner-test789",
        )
    
    def test_has_permission_admin_wildcard(self, admin_context):
        """Test admin has all permissions via wildcard."""
        assert admin_context.has_permission("read:projects")
        assert admin_context.has_permission("write:projects")
        assert admin_context.has_permission("admin:users")
        assert admin_context.has_permission("any:permission")
    
    def test_has_permission_specific(self, monitor_context):
        """Test specific permission check."""
        assert monitor_context.has_permission("read:projects")
        assert monitor_context.has_permission("read:health")
        # Monitor doesn't have read:collections in actual permissions
        assert not monitor_context.has_permission("read:collections")
        assert not monitor_context.has_permission("write:projects")
        assert not monitor_context.has_permission("admin:users")
    
    def test_can_access_project_admin(self, admin_context):
        """Test admin can access all projects."""
        assert admin_context.can_access_project("project1")
        assert admin_context.can_access_project("project2")
        assert admin_context.can_access_project("any-project")
    
    def test_can_access_project_owner(self, project_owner_context):
        """Test project owner can only access assigned projects."""
        assert project_owner_context.can_access_project("project1")
        assert project_owner_context.can_access_project("project2")
        assert not project_owner_context.can_access_project("project3")
    
    def test_require_permission_success(self, admin_context):
        """Test require_permission passes for valid permission."""
        # Should not raise
        admin_context.require_permission("read:projects")
    
    def test_require_permission_failure(self, monitor_context):
        """Test require_permission raises for missing permission."""
        with pytest.raises(PermissionError, match="Permission 'write:projects' required"):
            monitor_context.require_permission("write:projects")
    
    def test_require_project_access_success(self, project_owner_context):
        """Test require_project_access passes for valid project."""
        # Should not raise
        project_owner_context.require_project_access("project1")
    
    def test_require_project_access_failure(self, project_owner_context):
        """Test require_project_access raises for inaccessible project."""
        with pytest.raises(PermissionError, match="Access to project 'project3' denied"):
            project_owner_context.require_project_access("project3")


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_infer_role_from_account_name_admin(self):
        """Test inferring admin role from account names."""
        assert infer_role_from_account_name("admin") == "admin"
        assert infer_role_from_account_name("administrator") == "admin"
        assert infer_role_from_account_name("sys-admin") == "admin"
    
    def test_infer_role_from_account_name_monitor(self):
        """Test inferring monitor role from account names."""
        assert infer_role_from_account_name("monitor") == "monitor"
        assert infer_role_from_account_name("monitoring") == "monitor"
        assert infer_role_from_account_name("monitor-service") == "monitor"
    
    def test_infer_role_from_account_name_service(self):
        """Test inferring service-app role from account names."""
        assert infer_role_from_account_name("service") == "service-app"
        assert infer_role_from_account_name("api-service") == "service-app"
        assert infer_role_from_account_name("myapp") == "service-app"
        assert infer_role_from_account_name("app-backend") == "service-app"
    
    def test_infer_role_from_account_name_default(self):
        """Test default role for unknown account names."""
        assert infer_role_from_account_name("user1") == "project-owner"
        assert infer_role_from_account_name("alice") == "project-owner"
        assert infer_role_from_account_name("bob-project") == "project-owner"
    
    def test_mask_api_key_standard(self):
        """Test masking standard length API keys."""
        key = "sk-admin-abc123def456ghi789jkl"
        masked = mask_api_key(key)
        
        # Should show first 4 and last 4 chars with ... in between
        assert masked.startswith("sk-a")
        assert masked.endswith("jkl")
        assert "..." in masked
        assert len(masked) < len(key)
    
    def test_mask_api_key_short(self):
        """Test masking short API keys."""
        key = "sk-admin-abc"
        masked = mask_api_key(key)
        
        # Even short keys get masked with first 4 and last 4
        assert "..." in masked
    
    def test_mask_api_key_preserves_format(self):
        """Test that masking preserves readable format."""
        key = "sk-serviceapp-xyz789uvw456rst123pqr"
        masked = mask_api_key(key)
        
        # Shows first 4 and last 4 chars
        assert masked.startswith("sk-s")
        assert masked.endswith("3pqr")
        assert "..." in masked
