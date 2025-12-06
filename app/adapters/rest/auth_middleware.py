"""Authentication middleware for validating API keys and injecting AuthContext."""

import logging
from typing import Optional, Callable
from datetime import datetime

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app import config
from app.domain.auth import AuthContext, Role, api_key_manager
from app.adapters.infra.auth_storage import (
    AuthDatabase,
    UserStorage,
    APIKeyStorage,
    AuditLogStorage,
    ProjectStorage,
)

logger = logging.getLogger(__name__)

# Initialize global database connection
_auth_db: Optional[AuthDatabase] = None
_user_storage: Optional[UserStorage] = None
_key_storage: Optional[APIKeyStorage] = None
_audit_storage: Optional[AuditLogStorage] = None
_project_storage: Optional[ProjectStorage] = None


def initialize_auth_storage():
    """Initialize authentication storage connections."""
    global _auth_db, _user_storage, _key_storage, _audit_storage, _project_storage
    
    if _auth_db is None:
        logger.info(f"Initializing auth database: {config.AUTH_DB_PATH}")
        _auth_db = AuthDatabase(config.AUTH_DB_PATH)
        _auth_db.create_tables()  # Ensure all tables exist
        _user_storage = UserStorage(_auth_db)
        _key_storage = APIKeyStorage(_auth_db)
        _audit_storage = AuditLogStorage(_auth_db)
        _project_storage = ProjectStorage(_auth_db)


def set_test_auth_storage(db: AuthDatabase, user_storage: UserStorage, 
                          key_storage: APIKeyStorage, audit_storage: AuditLogStorage,
                          project_storage: ProjectStorage):
    """Set auth storage for testing (dependency injection)."""
    global _auth_db, _user_storage, _key_storage, _audit_storage, _project_storage
    _auth_db = db
    _user_storage = user_storage
    _key_storage = key_storage
    _audit_storage = audit_storage
    _project_storage = project_storage


def reset_auth_storage():
    """Reset auth storage (for test cleanup)."""
    global _auth_db, _user_storage, _key_storage, _audit_storage, _project_storage
    _auth_db = None
    _user_storage = None
    _key_storage = None
    _audit_storage = None
    _project_storage = None


def get_auth_storages():
    """Get initialized auth storage instances."""
    if _auth_db is None:
        initialize_auth_storage()
    return _user_storage, _key_storage, _audit_storage, _project_storage


# Security scheme for OpenAPI/Swagger docs
security = HTTPBearer()


# ============================================================================
# Public Endpoints (No Auth Required)
# ============================================================================

PUBLIC_ENDPOINTS = [
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/admin/login",
    "/favicon.ico",
]


def is_public_endpoint(path: str) -> bool:
    """Check if endpoint is public (doesn't require authentication).
    
    Args:
        path: Request path
        
    Returns:
        True if endpoint is public, False otherwise
    """
    # Exact matches
    if path in PUBLIC_ENDPOINTS:
        return True
    
    # Prefix matches for docs
    if path.startswith("/docs") or path.startswith("/redoc"):
        return True
    
    return False


# ============================================================================
# Authentication Logic
# ============================================================================

async def authenticate_request(
    api_key: str,
    request: Request,
) -> Optional[AuthContext]:
    """Authenticate a request using API key.
    
    Args:
        api_key: API key from Authorization header
        request: FastAPI request object
        
    Returns:
        AuthContext if authentication succeeds, None otherwise
    """
    user_storage, key_storage, audit_storage, project_storage = get_auth_storages()
    
    # Validate key format
    if not api_key_manager.validate_format(api_key):
        logger.warning(f"Invalid API key format from {request.client.host}")
        return None
    
    # Lookup key in database
    api_key_record = key_storage.get_api_key_by_key_id(api_key)
    if not api_key_record:
        logger.warning(f"API key not found: {api_key[:20]}...")
        return None
    
    # Verify key is valid (not expired, not revoked)
    if not api_key_record.is_valid:
        logger.warning(
            f"Invalid API key (expired={api_key_record.is_expired}, "
            f"revoked={api_key_record.is_revoked}): {api_key[:20]}..."
        )
        return None
    
    # Verify hash (constant-time comparison)
    if not api_key_manager.verify_key(api_key, api_key_record.key_hash):
        logger.warning(f"API key hash verification failed: {api_key[:20]}...")
        # Log failed authentication attempt
        audit_storage.create_log(
            action="auth_failed",
            status="failure",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={"reason": "hash_mismatch", "key_id": api_key[:20]},
        )
        return None
    
    # Load user information
    user = user_storage.get_user_by_id(api_key_record.user_id)
    if not user or not user.active:
        logger.warning(f"User not found or inactive for key: {api_key[:20]}...")
        return None
    
    # Get user's permissions based on role
    role = Role.from_string(user.role)
    permissions = role.get_permissions()
    
    # Get user's accessible projects
    accessible_projects = []
    if role != Role.ADMIN:  # Admin can access all projects
        try:
            # Query projects where user is owner or has explicit access
            user_storage, key_storage, audit_storage, project_storage = get_auth_storages()
            user_projects = project_storage.list_user_projects(user.id, active_only=True)
            accessible_projects = [proj.project_id for proj, _ in user_projects]
        except Exception as e:
            logger.error(f"Failed to load user projects: {e}")
    
    # Update last_used_at timestamp (async, non-blocking)
    try:
        key_storage.update_last_used(api_key)
    except Exception as e:
        logger.error(f"Failed to update last_used_at: {e}")
    
    # Create auth context
    auth_context = AuthContext(
        user_id=user.id,
        username=user.username,
        role=user.role,
        permissions=permissions,
        accessible_projects=accessible_projects,
        api_key_id=api_key[:20],  # Store masked key for audit
    )
    
    logger.debug(f"Authenticated user: {user.username} (role: {user.role})")
    
    return auth_context


# ============================================================================
# FastAPI Dependency for Endpoints
# ============================================================================

async def get_current_user(
    request: Request,
) -> AuthContext:
    """Dependency to get current authenticated user.
    
    Use this in endpoint parameters to require authentication:
    
    ```python
    @app.get("/protected")
    async def protected_endpoint(auth: AuthContext = Depends(get_current_user)):
        return {"user": auth.username}
    ```
    
    Args:
        request: FastAPI request object (injected automatically)
        
    Returns:
        AuthContext with user information from middleware
        
    Raises:
        HTTPException: 401 if authentication fails
    """
    # Get auth context from request state (injected by middleware)
    auth_context = getattr(request.state, "auth", None)
    
    if not auth_context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return auth_context


async def get_optional_user(
    request: Request,
) -> Optional[AuthContext]:
    """Dependency to get current user if authenticated, None otherwise.
    
    Use this for endpoints that optionally support authentication:
    
    ```python
    @app.get("/optional-auth")
    async def endpoint(auth: Optional[AuthContext] = Depends(get_optional_user)):
        if auth:
            return {"user": auth.username}
        return {"user": "anonymous"}
    ```
    
    Args:
        request: FastAPI request object
        
    Returns:
        AuthContext if authenticated, None otherwise
    """
    # Check if Authorization header exists
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    # Extract token
    api_key = auth_header.replace("Bearer ", "").strip()
    
    # Authenticate
    return await authenticate_request(api_key, request)


# ============================================================================
# Middleware for Request-Level Authentication
# ============================================================================

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to authenticate requests and inject AuthContext.
    
    This middleware:
    1. Checks if endpoint requires authentication
    2. Extracts Bearer token from Authorization header
    3. Validates token against database
    4. Injects AuthContext into request.state.auth
    5. Returns 401 if authentication fails for protected endpoints
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through authentication middleware.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response from handler or 401 error
        """
        # Check if endpoint is public
        if is_public_endpoint(request.url.path):
            request.state.auth = None
            return await call_next(request)
        
        # Extract Authorization header
        auth_header = request.headers.get("authorization")
        
        # If no auth header, check if endpoint requires it
        if not auth_header:
            # For now, we'll let the endpoint dependencies handle auth
            # This allows more flexible per-endpoint auth requirements
            request.state.auth = None
            return await call_next(request)
        
        # Parse Bearer token
        if not auth_header.startswith("Bearer "):
            return Response(
                content='{"detail":"Invalid Authorization header format. Expected: Bearer <token>"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        api_key = auth_header.replace("Bearer ", "").strip()
        
        # Authenticate
        auth_context = await authenticate_request(api_key, request)
        
        if not auth_context:
            # Log failed authentication
            user_storage, key_storage, audit_storage, project_storage = get_auth_storages()
            audit_storage.create_log(
                action="auth_failed",
                status="failure",
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                details={
                    "path": request.url.path,
                    "method": request.method,
                },
            )
            
            return Response(
                content='{"detail":"Invalid or expired API key","error_code":"AUTH_INVALID_KEY"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Inject auth context into request state
        request.state.auth = auth_context
        
        # Log successful authentication
        user_storage, key_storage, audit_storage, project_storage = get_auth_storages()
        audit_storage.create_log(
            action="auth_success",
            user_id=auth_context.user_id,
            status="success",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={
                "path": request.url.path,
                "method": request.method,
            },
        )
        
        # Continue to endpoint handler
        response = await call_next(request)
        
        return response


# ============================================================================
# Permission Checking Utilities
# ============================================================================

def require_permission(permission: str):
    """Decorator to require specific permission.
    
    Usage:
    ```python
    @app.post("/vectors")
    @require_permission("write:vectors")
    async def add_vector(auth: AuthContext = Depends(get_current_user)):
        ...
    ```
    """
    def decorator(func):
        async def wrapper(*args, auth: AuthContext = None, **kwargs):
            if not auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            if not auth.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required",
                    headers={"X-Required-Permission": permission},
                )
            
            return await func(*args, auth=auth, **kwargs)
        
        return wrapper
    
    return decorator


def require_role(role: str):
    """Decorator to require specific role.
    
    Usage:
    ```python
    @app.get("/admin/users")
    @require_role("admin")
    async def list_users(auth: AuthContext = Depends(get_current_user)):
        ...
    ```
    """
    def decorator(func):
        async def wrapper(*args, auth: AuthContext = None, **kwargs):
            if not auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )
            
            if auth.role != role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role '{role}' required. You have role '{auth.role}'",
                )
            
            return await func(*args, auth=auth, **kwargs)
        
        return wrapper
    
    return decorator
