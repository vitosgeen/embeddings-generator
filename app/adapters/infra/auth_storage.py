"""SQLite-based authentication and authorization storage using SQLAlchemy."""

from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import StaticPool

Base = declarative_base()


# ============================================================================
# SQLAlchemy Models
# ============================================================================


class User(Base):
    """User identity and role."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(
        String(50),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False, index=True)
    meta_json = Column(Text, nullable=True)  # JSON stored as text

    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    owned_projects = relationship("Project", back_populates="owner", foreign_keys="Project.owner_user_id")
    project_access = relationship("UserProject", back_populates="user", cascade="all, delete-orphan", foreign_keys="UserProject.user_id")
    audit_logs = relationship("AuditLog", back_populates="user", foreign_keys="AuditLog.user_id")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'monitor', 'service-app', 'project-owner')",
            name="check_user_role",
        ),
    )

    @property
    def is_active(self) -> bool:
        """Check if user is active (alias for active field)."""
        return self.active

    @property
    def meta(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if self.meta_json:
            return json.loads(self.meta_json)
        return {}

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Set metadata from dictionary."""
        self.meta_json = json.dumps(value) if value else None


class APIKey(Base):
    """API key with hashed storage and lifecycle tracking."""

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key_id = Column(String(255), unique=True, nullable=False, index=True)  # Public identifier (e.g., 'sk-admin-abc...')
    key_hash = Column(Text, nullable=False)  # Argon2/Bcrypt hash
    label = Column(String(255), nullable=True)  # Human-readable label
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True, index=True)
    revoked_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True, nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)  # JSON: IP whitelist, rate limits, etc.

    # Relationships
    user = relationship("User", back_populates="api_keys")

    @property
    def meta(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if self.meta_json:
            return json.loads(self.meta_json)
        return {}

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Set metadata from dictionary."""
        self.meta_json = json.dumps(value) if value else None

    @property
    def is_active(self) -> bool:
        """Check if key is active (not explicitly deactivated)."""
        return self.active

    @property
    def is_expired(self) -> bool:
        """Check if key has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    @property
    def is_revoked(self) -> bool:
        """Check if key has been revoked."""
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if key is valid (active, not expired, not revoked)."""
        return self.active and not self.is_expired and not self.is_revoked


class Project(Base):
    """VDB project with ownership tracking."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(255), unique=True, nullable=False, index=True)  # User-facing ID (e.g., 'my-rag-app')
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False, index=True)
    metadata_json = Column(Text, nullable=True)  # Custom project settings

    # Relationships
    owner = relationship("User", back_populates="owned_projects", foreign_keys=[owner_user_id])
    user_access = relationship("UserProject", back_populates="project", cascade="all, delete-orphan")

    @property
    def meta(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if self.meta_json:
            return json.loads(self.meta_json)
        return {}

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Set metadata from dictionary."""
        self.meta_json = json.dumps(value) if value else None


class UserProject(Base):
    """Many-to-many mapping for project access control."""

    __tablename__ = "user_projects"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True, index=True)
    role = Column(String(50), default="project-owner", nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="project_access", foreign_keys=[user_id])
    project = relationship("Project", back_populates="user_access")
    granter = relationship("User", foreign_keys=[granted_by])

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('project-owner', 'project-viewer')",
            name="check_user_project_role",
        ),
        Index("idx_user_projects_user", "user_id"),
        Index("idx_user_projects_project", "project_id"),
    )


class AuditLog(Base):
    """Audit trail for authentication events and admin actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # 'login', 'api_call', 'key_created', etc.
    resource_type = Column(String(50), nullable=True)  # 'user', 'project', 'api_key', 'vector', etc.
    resource_id = Column(String(255), nullable=True)
    status = Column(String(20), nullable=True, index=True)  # 'success', 'failure', 'denied'
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(Text, nullable=True)
    details_json = Column(Text, nullable=True)  # Additional context as JSON

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    @property
    def created_at(self):
        """Alias for timestamp field."""
        return self.timestamp
    
    @property
    def details(self) -> Dict[str, Any]:
        """Alias for detail_data property."""
        return self.detail_data
    
    @property
    def detail_data(self) -> Dict[str, Any]:
        """Get details as dictionary."""
        if self.details_json:
            return json.loads(self.details_json)
        return {}

    @detail_data.setter
    def detail_data(self, value: Dict[str, Any]):
        """Set details from dictionary."""
        self.details_json = json.dumps(value) if value else None


class UsageRecord(Base):
    """Track resource usage per user/project."""

    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    operation_type = Column(String(50), nullable=False, index=True)  # 'add_vector', 'search', 'delete_vector'
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Metrics
    vector_count = Column(Integer, default=1, nullable=False)  # Number of vectors in operation
    payload_size = Column(Integer, nullable=True)  # Size in bytes
    duration_ms = Column(Integer, nullable=True)  # Operation duration in milliseconds
    
    # Context
    collection_name = Column(String(255), nullable=True, index=True)
    status = Column(String(20), default="success", nullable=False)  # 'success', 'failure', 'quota_exceeded'
    meta_json = Column(Text, nullable=True)  # Additional context

    # Relationships
    user = relationship("User")

    # Indexes
    __table_args__ = (
        Index("idx_usage_user_project_time", "user_id", "project_id", "timestamp"),
        Index("idx_usage_operation_time", "operation_type", "timestamp"),
    )

    @property
    def meta(self) -> Dict[str, Any]:
        """Get metadata as dictionary."""
        if self.meta_json:
            return json.loads(self.meta_json)
        return {}

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Set metadata from dictionary."""
        self.meta_json = json.dumps(value) if value else None


class Quota(Base):
    """Define usage quotas for users/projects."""

    __tablename__ = "quotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    project_id = Column(String(255), nullable=True, index=True)
    
    # Quota limits (null = unlimited)
    max_vectors_per_project = Column(Integer, nullable=True)
    max_searches_per_day = Column(Integer, nullable=True)
    max_collections_per_project = Column(Integer, nullable=True)
    max_storage_bytes = Column(Integer, nullable=True)
    
    # Time-based limits
    max_operations_per_minute = Column(Integer, nullable=True)
    max_operations_per_hour = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    user = relationship("User")

    # Constraints - either user_id or project_id must be set (or both)
    __table_args__ = (
        Index("idx_quota_user_project", "user_id", "project_id"),
    )


# ============================================================================
# Database Manager
# ============================================================================


class AuthDatabase:
    """Manager for authentication database operations."""

    def __init__(self, db_path: str = "./data/auth.db"):
        """Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        
        # Create engine with connection pooling for single-threaded async
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a database session.
        
        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()

    def close(self):
        """Close database connection."""
        self.engine.dispose()


# ============================================================================
# Storage Implementations
# ============================================================================


class UserStorage:
    """Storage operations for users."""

    def __init__(self, db: AuthDatabase):
        self.db = db

    def create_user(
        self,
        username: str,
        role: str,
        email: Optional[str] = None,
        active: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> User:
        """Create a new user.
        
        Args:
            username: Unique username
            role: User role (admin, monitor, service-app, project-owner)
            email: Optional email address
            active: Whether user is active
            metadata: Optional metadata dictionary
            
        Returns:
            Created User instance
        """
        with self.db.get_session() as session:
            user = User(
                username=username,
                role=role,
                email=email,
                active=active,
            )
            if metadata:
                user.meta = metadata
            
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with self.db.get_session() as session:
            return session.query(User).filter(User.id == user_id).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        with self.db.get_session() as session:
            return session.query(User).filter(User.username == username).first()

    def list_users(
        self,
        role: Optional[str] = None,
        active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[User]:
        """List users with optional filters.
        
        Args:
            role: Filter by role
            active: Filter by active status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of User instances
        """
        with self.db.get_session() as session:
            query = session.query(User)
            
            if role:
                query = query.filter(User.role == role)
            if active is not None:
                query = query.filter(User.active == active)
            
            return query.limit(limit).offset(offset).all()

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email.
        
        Args:
            email: User email
            
        Returns:
            User instance or None if not found
        """
        with self.db.get_session() as session:
            return session.query(User).filter(User.email == email).first()

    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        role: Optional[str] = None,
        active: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[User]:
        """Update user fields.
        
        Args:
            user_id: User ID to update
            email: New email (if provided)
            role: New role (if provided)
            active: New active status (if provided)
            metadata: New metadata (if provided)
            
        Returns:
            Updated User instance or None if not found
        """
        with self.db.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            if email is not None:
                user.email = email
            if role is not None:
                user.role = role
            if active is not None:
                user.active = active
            if metadata is not None:
                user.meta = metadata
            
            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)
            return user

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user (soft delete).
        
        Args:
            user_id: User ID to deactivate
            
        Returns:
            True if deactivated, False if not found
        """
        with self.db.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.active = False
            user.updated_at = datetime.utcnow()
            session.commit()
            return True

    def delete_user(self, user_id: int) -> bool:
        """Delete user (hard delete from database).
        
        Args:
            user_id: User ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self.db.get_session() as session:
            user = session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            session.delete(user)
            session.commit()
            return True


class APIKeyStorage:
    """Storage operations for API keys."""

    def __init__(self, db: AuthDatabase):
        self.db = db

    def create_api_key(
        self,
        user_id: int,
        key_id: str,
        key_hash: str,
        label: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> APIKey:
        """Create a new API key.
        
        Args:
            user_id: User ID who owns this key
            key_id: Public key identifier (e.g., 'sk-admin-abc...')
            key_hash: Hashed key value
            label: Human-readable label
            expires_at: Optional expiration datetime
            metadata: Optional metadata (IP whitelist, rate limits, etc.)
            
        Returns:
            Created APIKey instance
        """
        with self.db.get_session() as session:
            api_key = APIKey(
                user_id=user_id,
                key_id=key_id,
                key_hash=key_hash,
                label=label,
                expires_at=expires_at,
            )
            if metadata:
                api_key.meta = metadata
            
            session.add(api_key)
            session.commit()
            session.refresh(api_key)
            return api_key

    def get_api_key_by_key_id(self, key_id: str) -> Optional[APIKey]:
        """Get API key by key_id."""
        with self.db.get_session() as session:
            return session.query(APIKey).filter(APIKey.key_id == key_id).first()

    def get_api_key_by_id(self, id: int) -> Optional[APIKey]:
        """Get API key by primary key ID."""
        with self.db.get_session() as session:
            return session.query(APIKey).filter(APIKey.id == id).first()

    def list_user_keys(self, user_id: int, active_only: bool = False) -> List[APIKey]:
        """List all API keys for a user.
        
        Args:
            user_id: User ID
            active_only: If True, only return active keys
            
        Returns:
            List of APIKey instances
        """
        with self.db.get_session() as session:
            query = session.query(APIKey).filter(APIKey.user_id == user_id)
            
            if active_only:
                query = query.filter(APIKey.active == True)
            
            return query.all()

    def list_user_api_keys(self, user_id: int, active_only: bool = False) -> List[APIKey]:
        """Alias for list_user_keys."""
        return self.list_user_keys(user_id, active_only)

    def update_last_used(self, key_id: str) -> bool:
        """Update last_used_at timestamp for a key.
        
        Args:
            key_id: Key ID to update
            
        Returns:
            True if updated, False if not found
        """
        with self.db.get_session() as session:
            api_key = session.query(APIKey).filter(APIKey.key_id == key_id).first()
            if not api_key:
                return False
            
            api_key.last_used_at = datetime.utcnow()
            session.commit()
            return True

    def revoke_key(self, key_id: str) -> bool:
        """Revoke an API key by key_id.
        
        Args:
            key_id: Key ID to revoke
            
        Returns:
            True if revoked, False if not found
        """
        with self.db.get_session() as session:
            api_key = session.query(APIKey).filter(APIKey.key_id == key_id).first()
            if not api_key:
                return False
            
            api_key.active = False
            api_key.revoked_at = datetime.utcnow()
            session.commit()
            return True

    def revoke_api_key(self, id: int) -> bool:
        """Revoke an API key by primary key ID.
        
        Args:
            id: Primary key ID of the API key
            
        Returns:
            True if revoked, False if not found
        """
        with self.db.get_session() as session:
            api_key = session.query(APIKey).filter(APIKey.id == id).first()
            if not api_key:
                return False
            
            api_key.active = False
            api_key.revoked_at = datetime.utcnow()
            session.commit()
            return True

    def delete_api_key(self, id: int) -> bool:
        """Delete an API key (hard delete from database).
        
        Args:
            id: Primary key ID of the API key
            
        Returns:
            True if deleted, False if not found
        """
        with self.db.get_session() as session:
            api_key = session.query(APIKey).filter(APIKey.id == id).first()
            if not api_key:
                return False
            
            session.delete(api_key)
            session.commit()
            return True


class AuditLogStorage:
    """Storage operations for audit logs."""

    def __init__(self, db: AuthDatabase):
        self.db = db

    def create_log(
        self,
        action: str,
        user_id: Optional[int] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """Create an audit log entry.
        
        Args:
            action: Action performed (e.g., 'login', 'api_call', 'key_created')
            user_id: User who performed the action
            resource_type: Type of resource (e.g., 'user', 'project', 'api_key')
            resource_id: ID of the resource
            status: Status of the action ('success', 'failure', 'denied')
            ip_address: Client IP address
            user_agent: Client user agent string
            details: Additional details as dictionary
            
        Returns:
            Created AuditLog instance
        """
        with self.db.get_session() as session:
            log = AuditLog(
                action=action,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                status=status,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            if details:
                log.detail_data = details
            
            session.add(log)
            session.commit()
            session.refresh(log)
            return log

    def list_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """List audit logs with optional filters.
        
        Args:
            user_id: Filter by user ID
            action: Filter by action
            status: Filter by status
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of AuditLog instances
        """
        with self.db.get_session() as session:
            query = session.query(AuditLog)
            
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if action:
                query = query.filter(AuditLog.action == action)
            if status:
                query = query.filter(AuditLog.status == status)
            
            return query.order_by(AuditLog.timestamp.desc()).limit(limit).offset(offset).all()

    def list_logs_by_action(self, action: str, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        """List audit logs filtered by action.
        
        Args:
            action: Action to filter by
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of AuditLog instances
        """
        return self.list_logs(action=action, limit=limit, offset=offset)

    def list_user_logs(self, user_id: int, limit: int = 100, offset: int = 0) -> List[AuditLog]:
        """List audit logs for a specific user.
        
        Args:
            user_id: User ID to filter by
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of AuditLog instances for the user
        """
        return self.list_logs(user_id=user_id, limit=limit, offset=offset)


class ProjectStorage:
    """Storage operations for projects and user-project access control."""

    def __init__(self, db: AuthDatabase):
        self.db = db

    def create_project(
        self,
        project_id: str,
        owner_user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Project:
        """Create a new project.
        
        Args:
            project_id: Unique project identifier (e.g., 'my-rag-app')
            owner_user_id: User ID of the project owner
            name: Human-readable project name
            description: Project description
            metadata: Additional project metadata
            
        Returns:
            Created Project instance
        """
        with self.db.get_session() as session:
            project = Project(
                project_id=project_id,
                owner_user_id=owner_user_id,
                name=name,
                description=description,
            )
            if metadata:
                project.meta = metadata
            
            session.add(project)
            session.commit()
            session.refresh(project)
            return project

    def get_project_by_id(self, project_id: str) -> Optional[Project]:
        """Get project by project_id."""
        with self.db.get_session() as session:
            return session.query(Project).filter(Project.project_id == project_id).first()

    def get_project_by_pk(self, pk: int) -> Optional[Project]:
        """Get project by primary key."""
        with self.db.get_session() as session:
            return session.query(Project).filter(Project.id == pk).first()

    def list_projects(
        self,
        owner_user_id: Optional[int] = None,
        active_only: bool = True,
    ) -> List[Project]:
        """List projects with optional filters.
        
        Args:
            owner_user_id: Filter by owner user ID
            active_only: If True, only return active projects
            
        Returns:
            List of Project instances
        """
        with self.db.get_session() as session:
            query = session.query(Project)
            
            if owner_user_id:
                query = query.filter(Project.owner_user_id == owner_user_id)
            if active_only:
                query = query.filter(Project.active == True)
            
            return query.order_by(Project.created_at.desc()).all()

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Project]:
        """Update project fields.
        
        Args:
            project_id: Project ID to update
            name: New name (if provided)
            description: New description (if provided)
            metadata: New metadata (if provided)
            
        Returns:
            Updated Project instance or None if not found
        """
        with self.db.get_session() as session:
            project = session.query(Project).filter(Project.project_id == project_id).first()
            if not project:
                return None
            
            if name is not None:
                project.name = name
            if description is not None:
                project.description = description
            if metadata is not None:
                project.meta = metadata
            
            project.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(project)
            return project

    def deactivate_project(self, project_id: str) -> bool:
        """Deactivate a project (soft delete).
        
        Args:
            project_id: Project ID to deactivate
            
        Returns:
            True if deactivated, False if not found
        """
        with self.db.get_session() as session:
            project = session.query(Project).filter(Project.project_id == project_id).first()
            if not project:
                return False
            
            project.active = False
            project.updated_at = datetime.utcnow()
            session.commit()
            return True

    def delete_project(self, project_id: str) -> bool:
        """Delete a project (hard delete).
        
        Args:
            project_id: Project ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self.db.get_session() as session:
            project = session.query(Project).filter(Project.project_id == project_id).first()
            if not project:
                return False
            
            session.delete(project)
            session.commit()
            return True

    # User-Project Access Control Methods

    def grant_project_access(
        self,
        user_id: int,
        project_id: str,
        role: str = "project-owner",
        granted_by: Optional[int] = None,
    ) -> UserProject:
        """Grant a user access to a project.
        
        Args:
            user_id: User ID to grant access to
            project_id: Project ID to grant access for
            role: Role for the user ('project-owner', 'project-viewer')
            granted_by: User ID who granted the access
            
        Returns:
            Created UserProject instance
        """
        with self.db.get_session() as session:
            # Get project primary key
            project = session.query(Project).filter(Project.project_id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Check if access already exists
            existing = session.query(UserProject).filter(
                UserProject.user_id == user_id,
                UserProject.project_id == project.id
            ).first()
            
            if existing:
                # Update existing access
                existing.role = role
                existing.granted_at = datetime.utcnow()
                existing.granted_by = granted_by
                session.commit()
                session.refresh(existing)
                return existing
            
            # Create new access
            user_project = UserProject(
                user_id=user_id,
                project_id=project.id,
                role=role,
                granted_by=granted_by,
            )
            
            session.add(user_project)
            session.commit()
            session.refresh(user_project)
            return user_project

    def revoke_project_access(self, user_id: int, project_id: str) -> bool:
        """Revoke a user's access to a project.
        
        Args:
            user_id: User ID to revoke access from
            project_id: Project ID to revoke access for
            
        Returns:
            True if revoked, False if access didn't exist
        """
        with self.db.get_session() as session:
            # Get project primary key
            project = session.query(Project).filter(Project.project_id == project_id).first()
            if not project:
                return False
            
            user_project = session.query(UserProject).filter(
                UserProject.user_id == user_id,
                UserProject.project_id == project.id
            ).first()
            
            if not user_project:
                return False
            
            session.delete(user_project)
            session.commit()
            return True

    def list_project_users(self, project_id: str) -> List[tuple]:
        """List all users with access to a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of tuples: (User, UserProject)
        """
        with self.db.get_session() as session:
            project = session.query(Project).filter(Project.project_id == project_id).first()
            if not project:
                return []
            
            results = session.query(User, UserProject).join(
                UserProject, User.id == UserProject.user_id
            ).filter(
                UserProject.project_id == project.id
            ).all()
            
            return results

    def list_user_projects(self, user_id: int, active_only: bool = True) -> List[tuple]:
        """List all projects a user has access to.
        
        Args:
            user_id: User ID
            active_only: If True, only return active projects
            
        Returns:
            List of tuples: (Project, UserProject)
        """
        with self.db.get_session() as session:
            query = session.query(Project, UserProject).join(
                UserProject, Project.id == UserProject.project_id
            ).filter(
                UserProject.user_id == user_id
            )
            
            if active_only:
                query = query.filter(Project.active == True)
            
            return query.order_by(Project.created_at.desc()).all()

    def check_user_project_access(self, user_id: int, project_id: str) -> Optional[str]:
        """Check if a user has access to a project and return their role.
        
        Args:
            user_id: User ID
            project_id: Project ID
            
        Returns:
            User's role in the project or None if no access
        """
        with self.db.get_session() as session:
            project = session.query(Project).filter(Project.project_id == project_id).first()
            if not project:
                return None
            
            # Check if user is owner
            if project.owner_user_id == user_id:
                return "project-owner"
            
            # Check UserProject table
            user_project = session.query(UserProject).filter(
                UserProject.user_id == user_id,
                UserProject.project_id == project.id
            ).first()
            
            return user_project.role if user_project else None


# ============================================================================
# Usage Tracking Storage
# ============================================================================


class UsageTrackingStorage:
    """Storage operations for usage tracking."""

    def __init__(self, db: AuthDatabase):
        self.db = db

    def record_operation(
        self,
        user_id: int,
        project_id: str,
        operation_type: str,
        vector_count: int = 1,
        collection_name: Optional[str] = None,
        payload_size: Optional[int] = None,
        duration_ms: Optional[int] = None,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageRecord:
        """Record a usage operation.
        
        Args:
            user_id: User performing the operation
            project_id: Project ID
            operation_type: Type of operation ('add_vector', 'search', 'delete_vector')
            vector_count: Number of vectors in operation
            collection_name: Collection name
            payload_size: Size of payload in bytes
            duration_ms: Operation duration in milliseconds
            status: Operation status ('success', 'failure', 'quota_exceeded')
            metadata: Additional context
            
        Returns:
            Created UsageRecord
        """
        with self.db.get_session() as session:
            record = UsageRecord(
                user_id=user_id,
                project_id=project_id,
                operation_type=operation_type,
                vector_count=vector_count,
                collection_name=collection_name,
                payload_size=payload_size,
                duration_ms=duration_ms,
                status=status,
            )
            if metadata:
                record.meta = metadata
            
            session.add(record)
            session.commit()
            session.refresh(record)
            return record

    def get_usage_stats(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[str] = None,
        operation_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated usage statistics.
        
        Args:
            user_id: Filter by user ID
            project_id: Filter by project ID
            operation_type: Filter by operation type
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dictionary with aggregated stats
        """
        with self.db.get_session() as session:
            query = session.query(UsageRecord)
            
            if user_id:
                query = query.filter(UsageRecord.user_id == user_id)
            if project_id:
                query = query.filter(UsageRecord.project_id == project_id)
            if operation_type:
                query = query.filter(UsageRecord.operation_type == operation_type)
            if start_time:
                query = query.filter(UsageRecord.timestamp >= start_time)
            if end_time:
                query = query.filter(UsageRecord.timestamp <= end_time)
            
            records = query.all()
            
            # Aggregate stats
            total_operations = len(records)
            total_vectors = sum(r.vector_count for r in records)
            total_payload_size = sum(r.payload_size for r in records if r.payload_size)
            
            # Group by operation type
            by_operation = {}
            for record in records:
                op_type = record.operation_type
                if op_type not in by_operation:
                    by_operation[op_type] = {
                        "count": 0,
                        "vectors": 0,
                        "total_duration_ms": 0,
                        "operations": []
                    }
                by_operation[op_type]["count"] += 1
                by_operation[op_type]["vectors"] += record.vector_count
                if record.duration_ms:
                    by_operation[op_type]["total_duration_ms"] += record.duration_ms
                    by_operation[op_type]["operations"].append(record.duration_ms)
            
            # Calculate averages
            for op_type, stats in by_operation.items():
                if stats["operations"]:
                    stats["avg_duration_ms"] = stats["total_duration_ms"] / len(stats["operations"])
                else:
                    stats["avg_duration_ms"] = 0
                # Remove temporary data
                del stats["operations"]
                del stats["total_duration_ms"]
            
            return {
                "total_operations": total_operations,
                "total_vectors": total_vectors,
                "total_payload_size": total_payload_size,
                "by_operation": by_operation,
                "time_range": {
                    "start": start_time.isoformat() if start_time else None,
                    "end": end_time.isoformat() if end_time else None,
                }
            }

    def get_recent_operations(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[UsageRecord]:
        """Get recent usage records.
        
        Args:
            user_id: Filter by user ID
            project_id: Filter by project ID
            limit: Maximum number of records
            
        Returns:
            List of UsageRecord objects
        """
        with self.db.get_session() as session:
            query = session.query(UsageRecord)
            
            if user_id:
                query = query.filter(UsageRecord.user_id == user_id)
            if project_id:
                query = query.filter(UsageRecord.project_id == project_id)
            
            return query.order_by(UsageRecord.timestamp.desc()).limit(limit).all()


# ============================================================================
# Quota Management Storage
# ============================================================================


class QuotaStorage:
    """Storage operations for quota management."""

    def __init__(self, db: AuthDatabase):
        self.db = db

    def create_quota(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[str] = None,
        max_vectors_per_project: Optional[int] = None,
        max_searches_per_day: Optional[int] = None,
        max_collections_per_project: Optional[int] = None,
        max_storage_bytes: Optional[int] = None,
        max_operations_per_minute: Optional[int] = None,
        max_operations_per_hour: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Quota:
        """Create a quota definition.
        
        Args:
            user_id: User ID (optional)
            project_id: Project ID (optional)
            max_vectors_per_project: Max vectors per project
            max_searches_per_day: Max searches per day
            max_collections_per_project: Max collections per project
            max_storage_bytes: Max storage in bytes
            max_operations_per_minute: Rate limit per minute
            max_operations_per_hour: Rate limit per hour
            notes: Additional notes
            
        Returns:
            Created Quota
        """
        with self.db.get_session() as session:
            quota = Quota(
                user_id=user_id,
                project_id=project_id,
                max_vectors_per_project=max_vectors_per_project,
                max_searches_per_day=max_searches_per_day,
                max_collections_per_project=max_collections_per_project,
                max_storage_bytes=max_storage_bytes,
                max_operations_per_minute=max_operations_per_minute,
                max_operations_per_hour=max_operations_per_hour,
                notes=notes,
            )
            
            session.add(quota)
            session.commit()
            session.refresh(quota)
            return quota

    def get_quota(
        self,
        user_id: Optional[int] = None,
        project_id: Optional[str] = None,
    ) -> Optional[Quota]:
        """Get quota for user/project.
        
        Priority: project-specific > user-specific > default
        
        Args:
            user_id: User ID
            project_id: Project ID
            
        Returns:
            Quota object or None
        """
        with self.db.get_session() as session:
            # Check project-specific quota first
            if user_id and project_id:
                quota = session.query(Quota).filter(
                    Quota.user_id == user_id,
                    Quota.project_id == project_id,
                    Quota.active == True
                ).first()
                if quota:
                    return quota
            
            # Check user-specific quota
            if user_id:
                quota = session.query(Quota).filter(
                    Quota.user_id == user_id,
                    Quota.project_id == None,
                    Quota.active == True
                ).first()
                if quota:
                    return quota
            
            # Check project-level quota
            if project_id:
                quota = session.query(Quota).filter(
                    Quota.user_id == None,
                    Quota.project_id == project_id,
                    Quota.active == True
                ).first()
                if quota:
                    return quota
            
            return None

    def check_quota(
        self,
        user_id: int,
        project_id: str,
        operation_type: str,
        vector_count: int = 1,
    ) -> tuple[bool, Optional[str]]:
        """Check if operation is allowed under quota.
        
        Args:
            user_id: User ID
            project_id: Project ID
            operation_type: Operation type
            vector_count: Number of vectors
            
        Returns:
            (allowed, reason) - True if allowed, False with reason if not
        """
        quota = self.get_quota(user_id, project_id)
        
        # No quota = unlimited
        if not quota:
            return (True, None)
        
        # Check rate limits
        if operation_type == "search" and quota.max_searches_per_day:
            # Count searches in last 24 hours
            from datetime import timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            with self.db.get_session() as session:
                count = session.query(UsageRecord).filter(
                    UsageRecord.user_id == user_id,
                    UsageRecord.project_id == project_id,
                    UsageRecord.operation_type == "search",
                    UsageRecord.timestamp >= yesterday,
                    UsageRecord.status == "success"
                ).count()
                
                if count >= quota.max_searches_per_day:
                    return (False, f"Daily search limit exceeded ({quota.max_searches_per_day})")
        
        # Check vectors per project limit
        if operation_type == "add_vector" and quota.max_vectors_per_project:
            # Would need to query VDB storage to get current vector count
            # For now, just check usage records (approximation)
            with self.db.get_session() as session:
                added = session.query(UsageRecord).filter(
                    UsageRecord.project_id == project_id,
                    UsageRecord.operation_type == "add_vector",
                    UsageRecord.status == "success"
                ).count()
                
                deleted = session.query(UsageRecord).filter(
                    UsageRecord.project_id == project_id,
                    UsageRecord.operation_type == "delete_vector",
                    UsageRecord.status == "success"
                ).count()
                
                current_estimate = added - deleted
                if current_estimate + vector_count > quota.max_vectors_per_project:
                    return (False, f"Vector limit exceeded ({quota.max_vectors_per_project})")
        
        return (True, None)

    def list_quotas(self) -> List[Quota]:
        """List all active quotas."""
        with self.db.get_session() as session:
            return session.query(Quota).filter(Quota.active == True).all()
