"""Unit tests for authentication storage layer."""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from app.adapters.infra.auth_storage import (
    AuthDatabase,
    UserStorage,
    APIKeyStorage,
    AuditLogStorage,
    User,
    APIKey,
    AuditLog,
)
from app.domain.auth import api_key_manager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    
    db = AuthDatabase(path)
    db.create_tables()  # Create schema
    
    yield db
    
    # Cleanup
    db.close()
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def user_storage(temp_db):
    """Create UserStorage instance with temp database."""
    return UserStorage(temp_db)


@pytest.fixture
def key_storage(temp_db):
    """Create APIKeyStorage instance with temp database."""
    return APIKeyStorage(temp_db)


@pytest.fixture
def audit_storage(temp_db):
    """Create AuditLogStorage instance with temp database."""
    return AuditLogStorage(temp_db)


class TestAuthDatabase:
    """Tests for AuthDatabase."""
    
    def test_create_database(self):
        """Test database creation."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        
        try:
            db = AuthDatabase(path)
            db.create_tables()
            assert os.path.exists(path)
            # File should have content after creating tables
            assert os.path.getsize(path) > 0
        finally:
            db.close()
            os.unlink(path)
    
    def test_get_session(self, temp_db):
        """Test getting database session."""
        with temp_db.get_session() as session:
            assert session is not None
            # Session should be usable - use a simple query
            from sqlalchemy import select
            from app.adapters.infra.auth_storage import User
            result = session.execute(select(User)).fetchall()
            assert isinstance(result, list)


class TestUserStorage:
    """Tests for UserStorage."""
    
    def test_create_user(self, user_storage):
        """Test creating a user."""
        user = user_storage.create_user(
            username="testuser",
            email="test@example.com",
            role="admin",
        )
        
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "admin"
        assert user.is_active is True
        assert user.created_at is not None
    
    def test_create_user_with_metadata(self, user_storage):
        """Test creating a user with metadata."""
        metadata = {"department": "engineering", "location": "remote"}
        user = user_storage.create_user(
            username="testuser",
            role="admin",
            metadata=metadata,
        )
        
        assert user.meta == metadata
    
    def test_get_user_by_id(self, user_storage):
        """Test retrieving user by ID."""
        created = user_storage.create_user(username="testuser", role="admin")
        
        retrieved = user_storage.get_user_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.username == "testuser"
    
    def test_get_user_by_id_not_found(self, user_storage):
        """Test retrieving non-existent user returns None."""
        user = user_storage.get_user_by_id(99999)
        assert user is None
    
    def test_get_user_by_username(self, user_storage):
        """Test retrieving user by username."""
        user_storage.create_user(username="testuser", role="admin")
        
        retrieved = user_storage.get_user_by_username("testuser")
        
        assert retrieved is not None
        assert retrieved.username == "testuser"
    
    def test_get_user_by_username_not_found(self, user_storage):
        """Test retrieving non-existent username returns None."""
        user = user_storage.get_user_by_username("nonexistent")
        assert user is None
    
    def test_get_user_by_email(self, user_storage):
        """Test retrieving user by email."""
        user_storage.create_user(
            username="testuser",
            email="test@example.com",
            role="admin",
        )
        
        retrieved = user_storage.get_user_by_email("test@example.com")
        
        assert retrieved is not None
        assert retrieved.email == "test@example.com"
    
    def test_list_users(self, user_storage):
        """Test listing all users."""
        user_storage.create_user(username="user1", role="admin")
        user_storage.create_user(username="user2", role="monitor")
        user_storage.create_user(username="user3", role="project-owner")
        
        users = user_storage.list_users()
        
        assert len(users) == 3
        usernames = [u.username for u in users]
        assert "user1" in usernames
        assert "user2" in usernames
        assert "user3" in usernames
    
    def test_list_users_by_role(self, user_storage):
        """Test listing users filtered by role."""
        user_storage.create_user(username="admin1", role="admin")
        user_storage.create_user(username="admin2", role="admin")
        user_storage.create_user(username="monitor1", role="monitor")
        
        admins = user_storage.list_users(role="admin")
        
        assert len(admins) == 2
        assert all(u.role == "admin" for u in admins)
    
    def test_update_user(self, user_storage):
        """Test updating user fields."""
        user = user_storage.create_user(username="testuser", role="project-owner")
        
        updated = user_storage.update_user(
            user.id,
            email="updated@example.com",
            role="admin",
        )
        
        assert updated.email == "updated@example.com"
        assert updated.role == "admin"
        assert updated.username == "testuser"  # Unchanged
    
    def test_deactivate_user(self, user_storage):
        """Test deactivating a user."""
        user = user_storage.create_user(username="testuser", role="admin")
        assert user.is_active is True
        
        user_storage.deactivate_user(user.id)
        
        retrieved = user_storage.get_user_by_id(user.id)
        assert retrieved.is_active is False
    
    def test_delete_user(self, user_storage):
        """Test deleting a user."""
        user = user_storage.create_user(username="testuser", role="admin")
        
        user_storage.delete_user(user.id)
        
        retrieved = user_storage.get_user_by_id(user.id)
        assert retrieved is None


class TestAPIKeyStorage:
    """Tests for APIKeyStorage."""
    
    def test_create_api_key(self, user_storage, key_storage):
        """Test creating an API key."""
        user = user_storage.create_user(username="testuser", role="admin")
        
        plaintext = api_key_manager.generate_key("admin")
        key_hash = api_key_manager.hash_key(plaintext)
        
        api_key = key_storage.create_api_key(
            user_id=user.id,
            key_id=plaintext,
            key_hash=key_hash,
            label="Test Key",
        )
        
        assert api_key.id is not None
        assert api_key.user_id == user.id
        assert api_key.key_id == plaintext
        assert api_key.key_hash == key_hash
        assert api_key.label == "Test Key"
        assert api_key.is_active is True
        assert api_key.created_at is not None
    
    def test_create_api_key_with_expiration(self, user_storage, key_storage):
        """Test creating an API key with expiration."""
        user = user_storage.create_user(username="testuser", role="admin")
        
        plaintext = api_key_manager.generate_key("admin")
        key_hash = api_key_manager.hash_key(plaintext)
        expires_at = datetime.utcnow() + timedelta(days=30)
        
        api_key = key_storage.create_api_key(
            user_id=user.id,
            key_id=plaintext,
            key_hash=key_hash,
            expires_at=expires_at,
        )
        
        assert api_key.expires_at is not None
        assert api_key.is_expired is False
    
    def test_get_api_key_by_id(self, user_storage, key_storage):
        """Test retrieving API key by ID."""
        user = user_storage.create_user(username="testuser", role="admin")
        plaintext = api_key_manager.generate_key("admin")
        key_hash = api_key_manager.hash_key(plaintext)
        
        created = key_storage.create_api_key(
            user_id=user.id,
            key_id=plaintext,
            key_hash=key_hash,
        )
        
        retrieved = key_storage.get_api_key_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.key_id == plaintext
    
    def test_get_api_key_by_key_id(self, user_storage, key_storage):
        """Test retrieving API key by key_id."""
        user = user_storage.create_user(username="testuser", role="admin")
        plaintext = api_key_manager.generate_key("admin")
        key_hash = api_key_manager.hash_key(plaintext)
        
        key_storage.create_api_key(
            user_id=user.id,
            key_id=plaintext,
            key_hash=key_hash,
        )
        
        retrieved = key_storage.get_api_key_by_key_id(plaintext)
        
        assert retrieved is not None
        assert retrieved.key_id == plaintext
    
    def test_list_user_api_keys(self, user_storage, key_storage):
        """Test listing API keys for a user."""
        user = user_storage.create_user(username="testuser", role="admin")
        
        for i in range(3):
            plaintext = api_key_manager.generate_key("admin")
            key_hash = api_key_manager.hash_key(plaintext)
            key_storage.create_api_key(
                user_id=user.id,
                key_id=plaintext,
                key_hash=key_hash,
                label=f"Key {i}",
            )
        
        keys = key_storage.list_user_api_keys(user.id)
        
        assert len(keys) == 3
    
    def test_list_user_api_keys_active_only(self, user_storage, key_storage):
        """Test listing only active API keys."""
        user = user_storage.create_user(username="testuser", role="admin")
        
        # Create 2 active and 1 inactive key
        for i in range(3):
            plaintext = api_key_manager.generate_key("admin")
            key_hash = api_key_manager.hash_key(plaintext)
            key = key_storage.create_api_key(
                user_id=user.id,
                key_id=plaintext,
                key_hash=key_hash,
            )
            
            if i == 2:  # Deactivate last one
                key_storage.revoke_api_key(key.id)
        
        active_keys = key_storage.list_user_api_keys(user.id, active_only=True)
        
        assert len(active_keys) == 2
        assert all(k.is_active for k in active_keys)
    
    def test_revoke_api_key(self, user_storage, key_storage):
        """Test revoking an API key."""
        user = user_storage.create_user(username="testuser", role="admin")
        plaintext = api_key_manager.generate_key("admin")
        key_hash = api_key_manager.hash_key(plaintext)
        
        api_key = key_storage.create_api_key(
            user_id=user.id,
            key_id=plaintext,
            key_hash=key_hash,
        )
        
        assert api_key.is_active is True
        
        key_storage.revoke_api_key(api_key.id)
        
        retrieved = key_storage.get_api_key_by_id(api_key.id)
        assert retrieved.is_active is False
        assert retrieved.revoked_at is not None
    
    def test_delete_api_key(self, user_storage, key_storage):
        """Test deleting an API key."""
        user = user_storage.create_user(username="testuser", role="admin")
        plaintext = api_key_manager.generate_key("admin")
        key_hash = api_key_manager.hash_key(plaintext)
        
        api_key = key_storage.create_api_key(
            user_id=user.id,
            key_id=plaintext,
            key_hash=key_hash,
        )
        
        key_storage.delete_api_key(api_key.id)
        
        retrieved = key_storage.get_api_key_by_id(api_key.id)
        assert retrieved is None
    
    def test_update_last_used(self, user_storage, key_storage):
        """Test updating last_used_at timestamp."""
        user = user_storage.create_user(username="testuser", role="admin")
        plaintext = api_key_manager.generate_key("admin")
        key_hash = api_key_manager.hash_key(plaintext)
        
        api_key = key_storage.create_api_key(
            user_id=user.id,
            key_id=plaintext,
            key_hash=key_hash,
        )
        
        assert api_key.last_used_at is None
        
        key_storage.update_last_used(api_key.id)
        
        retrieved = key_storage.get_api_key_by_id(api_key.id)
        assert retrieved.last_used_at is not None




class TestAuditLogStorage:
    """Tests for AuditLogStorage."""
    
    def test_create_log(self, audit_storage):
        """Test creating an audit log entry."""
        log = audit_storage.create_log(
            action="user_login",
            status="success",
            ip_address="192.168.1.1",
            user_agent="Test Client",
        )
        
        assert log.id is not None
        assert log.action == "user_login"
        assert log.status == "success"
        assert log.ip_address == "192.168.1.1"
        assert log.user_agent == "Test Client"
        assert log.created_at is not None
    
    def test_create_log_with_user(self, user_storage, audit_storage):
        """Test creating audit log with user ID."""
        user = user_storage.create_user(username="testuser", role="admin")
        
        log = audit_storage.create_log(
            action="api_call",
            user_id=user.id,
            status="success",
        )
        
        assert log.user_id == user.id
    
    def test_create_log_with_details(self, audit_storage):
        """Test creating audit log with details."""
        details = {
            "endpoint": "/api/projects",
            "method": "POST",
            "response_code": 201,
        }
        
        log = audit_storage.create_log(
            action="api_call",
            status="success",
            details=details,
        )
        
        assert log.details == details
    
    def test_list_logs(self, audit_storage):
        """Test listing audit logs."""
        for i in range(5):
            audit_storage.create_log(action=f"action{i}", status="success")
        
        logs = audit_storage.list_logs(limit=10)
        
        assert len(logs) == 5
    
    def test_list_logs_with_limit(self, audit_storage):
        """Test listing audit logs with limit."""
        for i in range(10):
            audit_storage.create_log(action=f"action{i}", status="success")
        
        logs = audit_storage.list_logs(limit=5)
        
        assert len(logs) == 5
    
    def test_list_user_logs(self, user_storage, audit_storage):
        """Test listing logs for specific user."""
        user1 = user_storage.create_user(username="user1", role="admin")
        user2 = user_storage.create_user(username="user2", role="admin")
        
        audit_storage.create_log(action="action1", user_id=user1.id, status="success")
        audit_storage.create_log(action="action2", user_id=user1.id, status="success")
        audit_storage.create_log(action="action3", user_id=user2.id, status="success")
        
        user1_logs = audit_storage.list_user_logs(user1.id)
        
        assert len(user1_logs) == 2
        assert all(log.user_id == user1.id for log in user1_logs)
    
    def test_list_logs_by_action(self, audit_storage):
        """Test listing logs filtered by action."""
        audit_storage.create_log(action="login", status="success")
        audit_storage.create_log(action="login", status="failure")
        audit_storage.create_log(action="api_call", status="success")
        
        login_logs = audit_storage.list_logs_by_action("login")
        
        assert len(login_logs) == 2
        assert all(log.action == "login" for log in login_logs)
