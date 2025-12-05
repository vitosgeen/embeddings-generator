"""Admin UI routes for user and API key management."""

import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, HTTPException, Form, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.domain.auth import AuthContext, Role, api_key_manager, mask_api_key
from app.adapters.infra.auth_storage import (
    AuthDatabase,
    UserStorage,
    APIKeyStorage,
    AuditLogStorage,
    ProjectStorage,
)
from app.config import AUTH_DB_PATH, ADMIN_PASSWORD
from .auth_middleware import get_current_user

logger = logging.getLogger(__name__)


# Initialize templates
templates = Jinja2Templates(directory="templates")

# Add custom filters
def format_number(value):
    """Format number with thousands separator."""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

templates.env.filters["format_number"] = format_number

# Initialize storage
_auth_db = AuthDatabase(AUTH_DB_PATH)
_user_storage = UserStorage(_auth_db)
_key_storage = APIKeyStorage(_auth_db)
_audit_storage = AuditLogStorage(_auth_db)
_project_storage = ProjectStorage(_auth_db)


# Admin session helper
async def get_admin_user(request: Request) -> AuthContext:
    """Get admin user from session cookie or API key.
    
    Checks for admin_session cookie first, then falls back to API key auth.
    """
    # Check for admin session cookie
    admin_session = request.cookies.get("admin_session")
    if admin_session:
        try:
            # Parse session cookie: "username:user_id"
            parts = admin_session.split(":")
            if len(parts) == 2:
                username, user_id_str = parts
                user = _user_storage.get_user_by_username(username)
                if user and user.active and user.role == "admin" and str(user.id) == user_id_str:
                    # Create auth context for admin user
                    role = Role.from_string(user.role)
                    return AuthContext(
                        user_id=user.id,
                        username=user.username,
                        role=user.role,
                        permissions=role.get_permissions(),
                        accessible_projects=[],  # Admin has access to all
                        api_key_id="session",
                    )
        except Exception as e:
            logger.error(f"Failed to parse admin session: {e}")
    
    # Fall back to regular API key authentication
    try:
        return await get_current_user(request)
    except HTTPException:
        # Redirect to login if no valid authentication
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Please login",
            headers={"Location": "/admin/login"}
        )


def build_admin_router() -> APIRouter:
    """Build the admin UI router."""
    
    router = APIRouter(prefix="/admin", tags=["Admin UI"])
    
    # ========================================================================
    # Authentication
    # ========================================================================
    
    @router.get("/login", response_class=HTMLResponse)
    async def login_page(request: Request, error: Optional[str] = None):
        """Display login page."""
        return templates.TemplateResponse("admin/login.html", {
            "request": request,
            "error": error
        })
    
    @router.post("/login")
    async def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...)
    ):
        """Handle login submission.
        
        Note: This is a simplified authentication for demo purposes.
        Password is validated against a simple check (admin123 for admin user).
        In production, use proper password hashing and validation.
        """
        # Get user by username
        user = _user_storage.get_user_by_username(username)
        if not user or not user.active:
            return templates.TemplateResponse("admin/login.html", {
                "request": request,
                "error": "Invalid username or password",
                "username": username
            })
        
        # Check if user has admin role
        if user.role != "admin":
            return templates.TemplateResponse("admin/login.html", {
                "request": request,
                "error": "Access denied: Admin role required",
                "username": username
            })
        
        # Validate password against environment variable
        # Password can be set via ADMIN_PASSWORD in .env file
        if password != ADMIN_PASSWORD:
            return templates.TemplateResponse("admin/login.html", {
                "request": request,
                "error": "Invalid username or password",
                "username": username
            })
        
        # Create session cookie
        response = RedirectResponse(url="/admin/", status_code=status.HTTP_302_FOUND)
        
        # Set session cookie (simple implementation - use proper session management in production)
        response.set_cookie(
            key="admin_session",
            value=f"{user.username}:{user.id}",
            httponly=True,
            max_age=3600 * 24,  # 24 hours
            samesite="lax"
        )
        
        return response
    
    @router.get("/logout")
    async def logout():
        """Handle logout."""
        response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
        response.delete_cookie("admin_session")
        return response
    
    # ========================================================================
    # Dashboard
    # ========================================================================
    
    @router.get("/", response_class=HTMLResponse)
    async def admin_dashboard(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Admin dashboard homepage."""
        auth.require_permission("admin:users")
        
        # Get statistics
        users = _user_storage.list_users()
        active_users = [u for u in users if u.active]
        
        total_keys = 0
        active_keys = 0
        for user in users:
            user_keys = _key_storage.list_user_api_keys(user.id)
            total_keys += len(user_keys)
            active_keys += len([k for k in user_keys if k.is_active and not k.is_expired])
        
        recent_logs = _audit_storage.list_logs(limit=10)
        
        return templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "auth": auth,
            "stats": {
                "total_users": len(users),
                "active_users": len(active_users),
                "total_keys": total_keys,
                "active_keys": active_keys,
            },
            "recent_logs": recent_logs,
        })
    
    @router.get("/tasks", response_class=HTMLResponse)
    async def tasks_page(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Task queue management page."""
        auth.require_permission("admin:users")
        
        return templates.TemplateResponse("admin/tasks.html", {
            "request": request,
            "auth": auth,
        })
    
    # ========================================================================
    # User Management
    # ========================================================================
    
    @router.get("/users", response_class=HTMLResponse)
    async def list_users(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
        role: Optional[str] = None,
    ):
        """List all users."""
        auth.require_permission("admin:users")
        
        users = _user_storage.list_users(role=role)
        
        return templates.TemplateResponse("admin/users.html", {
            "request": request,
            "auth": auth,
            "users": users,
            "filter_role": role,
            "roles": [r.value for r in Role],
        })
    
    @router.get("/users/new", response_class=HTMLResponse)
    async def new_user_form(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Show form to create new user."""
        auth.require_permission("admin:users")
        
        return templates.TemplateResponse("admin/user_form.html", {
            "request": request,
            "auth": auth,
            "user": None,
            "roles": [r.value for r in Role],
        })
    
    @router.post("/users", response_class=HTMLResponse)
    async def create_user(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
        username: str = Form(...),
        email: Optional[str] = Form(None),
        role: str = Form(...),
    ):
        """Create a new user."""
        auth.require_permission("admin:users")
        
        try:
            # Check if username already exists
            existing = _user_storage.get_user_by_username(username)
            if existing:
                return templates.TemplateResponse("admin/user_form.html", {
                    "request": request,
                    "auth": auth,
                    "user": None,
                    "roles": [r.value for r in Role],
                    "error": f"Username '{username}' already exists",
                })
            
            # Create user
            user = _user_storage.create_user(
                username=username,
                email=email if email else None,
                role=role,
            )
            
            # Log the action
            _audit_storage.create_log(
                action="user_created",
                user_id=auth.user_id,
                status="success",
                details={"created_user_id": user.id, "username": username},
            )
            
            # Return user row for HTMX to insert
            return templates.TemplateResponse("admin/user_row.html", {
                "request": request,
                "user": user,
            })
            
        except Exception as e:
            return templates.TemplateResponse("admin/user_form.html", {
                "request": request,
                "auth": auth,
                "user": None,
                "roles": [r.value for r in Role],
                "error": str(e),
            })
    
    @router.get("/users/{user_id}", response_class=HTMLResponse)
    async def get_user(
        request: Request,
        user_id: int,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Get user details."""
        auth.require_permission("admin:users")
        
        user = _user_storage.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get user's API keys
        api_keys = _key_storage.list_user_api_keys(user_id)
        
        return templates.TemplateResponse("admin/user_detail.html", {
            "request": request,
            "auth": auth,
            "user": user,
            "api_keys": api_keys,
        })
    
    @router.post("/users/{user_id}/deactivate")
    async def deactivate_user(
        user_id: int,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Deactivate a user."""
        auth.require_permission("admin:users")
        
        user = _user_storage.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        _user_storage.deactivate_user(user_id)
        
        _audit_storage.create_log(
            action="user_deactivated",
            user_id=auth.user_id,
            status="success",
            details={"deactivated_user_id": user_id, "username": user.username},
        )
        
        return {"status": "success", "message": f"User {user.username} deactivated"}
    
    @router.delete("/users/{user_id}")
    async def delete_user(
        user_id: int,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Delete a user."""
        auth.require_permission("admin:users")
        
        user = _user_storage.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        _user_storage.delete_user(user_id)
        
        _audit_storage.create_log(
            action="user_deleted",
            user_id=auth.user_id,
            status="success",
            details={"deleted_user_id": user_id, "username": user.username},
        )
        
        return {"status": "success", "message": f"User {user.username} deleted"}
    
    # ========================================================================
    # API Key Management
    # ========================================================================
    
    @router.get("/keys", response_class=HTMLResponse)
    async def list_keys(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
        user_id: Optional[int] = None,
    ):
        """List API keys."""
        auth.require_permission("admin:api_keys")
        
        if user_id:
            user = _user_storage.get_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            keys = _key_storage.list_user_api_keys(user_id)
            filter_user = user
        else:
            # Get all keys for all users
            users = _user_storage.list_users()
            keys = []
            for user in users:
                user_keys = _key_storage.list_user_api_keys(user.id)
                keys.extend(user_keys)
            filter_user = None
        
        return templates.TemplateResponse("admin/keys.html", {
            "request": request,
            "auth": auth,
            "keys": keys,
            "filter_user": filter_user,
        })
    
    @router.get("/keys/new", response_class=HTMLResponse)
    async def new_key_form(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
        user_id: Optional[int] = None,
    ):
        """Show form to create new API key."""
        auth.require_permission("admin:api_keys")
        
        users = _user_storage.list_users()
        selected_user = None
        if user_id:
            selected_user = _user_storage.get_user_by_id(user_id)
        
        return templates.TemplateResponse("admin/key_form.html", {
            "request": request,
            "auth": auth,
            "users": users,
            "selected_user": selected_user,
        })
    
    @router.post("/keys", response_class=HTMLResponse)
    async def create_key(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
        user_id: int = Form(...),
        label: str = Form(...),
        expires_days: str = Form(""),
    ):
        """Create a new API key."""
        auth.require_permission("admin:api_keys")
        
        user = _user_storage.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Generate key
        plaintext_key = api_key_manager.generate_key(user.role)
        key_hash = api_key_manager.hash_key(plaintext_key)
        
        # Calculate expiration
        expires_at = None
        # Convert empty string to None, then parse as int if present
        expires_days_int = None
        if expires_days and expires_days.strip():
            try:
                expires_days_int = int(expires_days)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid expiration days")
        
        if expires_days_int:
            expires_at = datetime.utcnow() + timedelta(days=expires_days_int)
        
        # Store key
        api_key = _key_storage.create_api_key(
            user_id=user.id,
            key_id=plaintext_key,
            key_hash=key_hash,
            label=label,
            expires_at=expires_at,
        )
        
        _audit_storage.create_log(
            action="api_key_created",
            user_id=auth.user_id,
            status="success",
            details={
                "key_id": api_key.id,
                "for_user": user.username,
                "label": label,
            },
        )
        
        # Return key details with plaintext key (only shown once!)
        return templates.TemplateResponse("admin/key_created.html", {
            "request": request,
            "auth": auth,
            "api_key": api_key,
            "plaintext_key": plaintext_key,
            "user": user,
        })
    
    @router.post("/keys/{key_id}/revoke")
    async def revoke_key(
        key_id: int,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Revoke an API key."""
        auth.require_permission("admin:api_keys")
        
        api_key = _key_storage.get_api_key_by_id(key_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")
        
        _key_storage.revoke_api_key(key_id)
        
        _audit_storage.create_log(
            action="api_key_revoked",
            user_id=auth.user_id,
            status="success",
            details={"key_id": key_id, "label": api_key.label},
        )
        
        return {"status": "success", "message": "API key revoked"}
    
    @router.delete("/keys/{key_id}")
    async def delete_key(
        key_id: int,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Delete an API key."""
        auth.require_permission("admin:api_keys")
        
        api_key = _key_storage.get_api_key_by_id(key_id)
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")
        
        _key_storage.delete_api_key(key_id)
        
        _audit_storage.create_log(
            action="api_key_deleted",
            user_id=auth.user_id,
            status="success",
            details={"key_id": key_id, "label": api_key.label},
        )
        
        return {"status": "success", "message": "API key deleted"}
    
    # ========================================================================
    # Audit Logs
    # ========================================================================
    
    @router.get("/logs", response_class=HTMLResponse)
    async def view_logs(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
        action: Optional[str] = None,
        limit: int = 50,
    ):
        """View audit logs."""
        auth.require_permission("read:audit-logs")
        
        if action:
            logs = _audit_storage.list_logs_by_action(action, limit=limit)
        else:
            logs = _audit_storage.list_logs(limit=limit)
        
        return templates.TemplateResponse("admin/logs.html", {
            "request": request,
            "auth": auth,
            "logs": logs,
            "filter_action": action,
        })
    
    # ========================================================================
    # Project Management
    # ========================================================================
    
    @router.get("/projects", response_class=HTMLResponse)
    async def list_projects(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
        owner_id: Optional[int] = None,
    ):
        """List all projects."""
        auth.require_permission("admin:users")
        
        if owner_id:
            owner = _user_storage.get_user_by_id(owner_id)
            if not owner:
                raise HTTPException(status_code=404, detail="User not found")
            projects = _project_storage.list_projects(owner_user_id=owner_id)
            filter_owner = owner
        else:
            projects = _project_storage.list_projects()
            filter_owner = None
        
        users = _user_storage.list_users()
        
        # Create user map for templates
        user_map = {user.id: user for user in users}
        
        return templates.TemplateResponse("admin/projects.html", {
            "request": request,
            "auth": auth,
            "projects": projects,
            "filter_owner": filter_owner,
            "users": users,
            "user_map": user_map,
        })
    
    @router.get("/projects/new", response_class=HTMLResponse)
    async def new_project_form(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Show form to create new project."""
        auth.require_permission("admin:users")
        
        users = _user_storage.list_users()
        
        return templates.TemplateResponse("admin/project_form.html", {
            "request": request,
            "auth": auth,
            "project": None,
            "users": users,
        })
    
    @router.post("/projects", response_class=HTMLResponse)
    async def create_project(
        request: Request,
        auth: AuthContext = Depends(get_admin_user),
        project_id: str = Form(...),
        owner_user_id: int = Form(...),
        name: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
    ):
        """Create a new project."""
        auth.require_permission("admin:users")
        
        try:
            # Check if project_id already exists
            existing = _project_storage.get_project_by_id(project_id)
            if existing:
                users = _user_storage.list_users()
                return templates.TemplateResponse("admin/project_form.html", {
                    "request": request,
                    "auth": auth,
                    "project": None,
                    "users": users,
                    "error": f"Project ID '{project_id}' already exists",
                })
            
            # Verify owner exists
            owner = _user_storage.get_user_by_id(owner_user_id)
            if not owner:
                raise HTTPException(status_code=404, detail="Owner user not found")
            
            # Create project
            project = _project_storage.create_project(
                project_id=project_id,
                owner_user_id=owner_user_id,
                name=name if name else None,
                description=description if description else None,
            )
            
            # Log the action
            _audit_storage.create_log(
                action="project_created",
                user_id=auth.user_id,
                status="success",
                details={
                    "project_id": project_id,
                    "owner_user_id": owner_user_id,
                    "name": name,
                },
            )
            
            # Return project row for HTMX to insert
            return templates.TemplateResponse("admin/project_row.html", {
                "request": request,
                "project": project,
                "owner": owner,
            })
            
        except Exception as e:
            users = _user_storage.list_users()
            return templates.TemplateResponse("admin/project_form.html", {
                "request": request,
                "auth": auth,
                "project": None,
                "users": users,
                "error": str(e),
            })
    
    @router.get("/projects/{project_id}", response_class=HTMLResponse)
    async def get_project(
        request: Request,
        project_id: str,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Get project details and user access."""
        auth.require_permission("admin:users")
        
        project = _project_storage.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get owner
        owner = _user_storage.get_user_by_id(project.owner_user_id)
        
        # Get users with access
        project_users = _project_storage.list_project_users(project_id)
        
        # Get all users for granting access
        all_users = _user_storage.list_users()
        
        return templates.TemplateResponse("admin/project_detail.html", {
            "request": request,
            "auth": auth,
            "project": project,
            "owner": owner,
            "project_users": project_users,
            "all_users": all_users,
        })
    
    @router.post("/projects/{project_id}/grant-access", response_class=HTMLResponse)
    async def grant_project_access(
        request: Request,
        project_id: str,
        auth: AuthContext = Depends(get_admin_user),
        user_id: int = Form(...),
        role: str = Form("project-owner"),
    ):
        """Grant a user access to a project."""
        auth.require_permission("admin:users")
        
        project = _project_storage.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user = _user_storage.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Grant access
        _project_storage.grant_project_access(
            user_id=user_id,
            project_id=project_id,
            role=role,
            granted_by=auth.user_id,
        )
        
        _audit_storage.create_log(
            action="project_access_granted",
            user_id=auth.user_id,
            status="success",
            details={
                "project_id": project_id,
                "granted_to_user_id": user_id,
                "role": role,
            },
        )
        
        # Return updated user row
        project_users = _project_storage.list_project_users(project_id)
        return templates.TemplateResponse("admin/project_users_list.html", {
            "request": request,
            "project": project,
            "project_users": project_users,
        })
    
    @router.post("/projects/{project_id}/revoke-access/{user_id}")
    async def revoke_project_access(
        project_id: str,
        user_id: int,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Revoke a user's access to a project."""
        auth.require_permission("admin:users")
        
        project = _project_storage.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        user = _user_storage.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Don't allow revoking owner's access
        if project.owner_user_id == user_id:
            raise HTTPException(status_code=400, detail="Cannot revoke owner's access")
        
        _project_storage.revoke_project_access(user_id, project_id)
        
        _audit_storage.create_log(
            action="project_access_revoked",
            user_id=auth.user_id,
            status="success",
            details={
                "project_id": project_id,
                "revoked_from_user_id": user_id,
                "username": user.username,
            },
        )
        
        return {"status": "success", "message": f"Access revoked for {user.username}"}
    
    @router.post("/projects/{project_id}/deactivate")
    async def deactivate_project(
        project_id: str,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Deactivate a project."""
        auth.require_permission("admin:users")
        
        project = _project_storage.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        _project_storage.deactivate_project(project_id)
        
        _audit_storage.create_log(
            action="project_deactivated",
            user_id=auth.user_id,
            status="success",
            details={"project_id": project_id, "name": project.name},
        )
        
        return {"status": "success", "message": f"Project {project_id} deactivated"}
    
    @router.delete("/projects/{project_id}")
    async def delete_project(
        project_id: str,
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Delete a project."""
        auth.require_permission("admin:users")
        
        project = _project_storage.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        _project_storage.delete_project(project_id)
        
        _audit_storage.create_log(
            action="project_deleted",
            user_id=auth.user_id,
            status="success",
            details={"project_id": project_id, "name": project.name},
        )
        
        return {"status": "success", "message": f"Project {project_id} deleted"}
    
    # ========================================================================
    # Usage Dashboard
    # ========================================================================
    
    @router.get("/usage", response_class=HTMLResponse)
    async def usage_dashboard(
        request: Request,
        time_range: str = "24h",
        auth: AuthContext = Depends(get_admin_user),
    ):
        """Usage statistics and monitoring dashboard."""
        auth.require_permission("admin:users")
        
        from app.adapters.infra.auth_storage import UsageTrackingStorage, QuotaStorage
        from datetime import timedelta
        from collections import defaultdict
        
        usage_storage = UsageTrackingStorage(_auth_db)
        quota_storage = QuotaStorage(_auth_db)
        
        # Calculate time range
        now = datetime.utcnow()
        if time_range == "24h":
            start_time = now - timedelta(hours=24)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:  # all
            start_time = None
        
        # Get usage summary
        usage_summary = usage_storage.get_usage_stats(start_time=start_time)
        
        # Calculate success rate
        with _auth_db.get_session() as session:
            from app.adapters.infra.auth_storage import UsageRecord
            query = session.query(UsageRecord)
            if start_time:
                query = query.filter(UsageRecord.timestamp >= start_time)
            
            all_ops = query.all()
            if all_ops:
                successful = len([op for op in all_ops if op.status == "success"])
                usage_summary["success_rate"] = (successful / len(all_ops)) * 100
            else:
                usage_summary["success_rate"] = 0
        
        # Get top users
        user_stats = defaultdict(lambda: {"operations": 0, "vectors": 0})
        for record in all_ops:
            user_stats[record.user_id]["operations"] += 1
            user_stats[record.user_id]["vectors"] += record.vector_count
        
        users = _user_storage.list_users()
        user_map = {u.id: u.username for u in users}
        
        top_users = []
        for user_id, stats in sorted(user_stats.items(), key=lambda x: x[1]["operations"], reverse=True):
            top_users.append({
                "username": user_map.get(user_id, f"User #{user_id}"),
                "operations": stats["operations"],
                "vectors": stats["vectors"]
            })
        
        # Get top projects
        project_stats = defaultdict(lambda: {"operations": 0, "vectors": 0})
        for record in all_ops:
            project_stats[record.project_id]["operations"] += 1
            project_stats[record.project_id]["vectors"] += record.vector_count
        
        top_projects = []
        for proj_id, stats in sorted(project_stats.items(), key=lambda x: x[1]["operations"], reverse=True):
            top_projects.append({
                "project_id": proj_id,
                "operations": stats["operations"],
                "vectors": stats["vectors"]
            })
        
        # Get quota status
        quota_status = []
        quotas = quota_storage.list_quotas()
        for quota in quotas[:10]:  # Show top 10
            # Get current usage
            current_vectors = 0
            searches_today = 0
            
            with _auth_db.get_session() as session:
                from app.adapters.infra.auth_storage import UsageRecord
                
                if quota.project_id:
                    # Project-specific
                    vector_query = session.query(UsageRecord).filter(
                        UsageRecord.project_id == quota.project_id,
                        UsageRecord.operation_type.in_(["add_vector", "batch_add_vector"]),
                        UsageRecord.status == "success"
                    )
                    search_query = session.query(UsageRecord).filter(
                        UsageRecord.project_id == quota.project_id,
                        UsageRecord.operation_type == "search",
                        UsageRecord.timestamp >= now - timedelta(days=1)
                    )
                elif quota.user_id:
                    # User-specific
                    vector_query = session.query(UsageRecord).filter(
                        UsageRecord.user_id == quota.user_id,
                        UsageRecord.operation_type.in_(["add_vector", "batch_add_vector"]),
                        UsageRecord.status == "success"
                    )
                    search_query = session.query(UsageRecord).filter(
                        UsageRecord.user_id == quota.user_id,
                        UsageRecord.operation_type == "search",
                        UsageRecord.timestamp >= now - timedelta(days=1)
                    )
                else:
                    continue
                
                current_vectors = sum(r.vector_count for r in vector_query.all())
                searches_today = search_query.count()
            
            usage_percent = 0
            if quota.max_vectors_per_project:
                usage_percent = (current_vectors / quota.max_vectors_per_project) * 100
            
            quota_status.append({
                "username": user_map.get(quota.user_id) if quota.user_id else None,
                "project_id": quota.project_id,
                "max_vectors_per_project": quota.max_vectors_per_project,
                "current_vectors": current_vectors,
                "max_searches_per_day": quota.max_searches_per_day,
                "searches_today": searches_today,
                "usage_percent": usage_percent
            })
        
        # Prepare chart data
        by_operation = usage_summary.get("by_operation", {})
        operations_chart_data = {
            "labels": list(by_operation.keys()),
            "operations": [stats["count"] for stats in by_operation.values()],
            "vectors": [stats["vectors"] for stats in by_operation.values()]
        }
        
        # Get recent operations with usernames
        recent_ops = usage_storage.get_recent_operations(limit=50)
        recent_operations = []
        for op in recent_ops:
            recent_operations.append({
                "timestamp": op.timestamp,
                "username": user_map.get(op.user_id, "Unknown"),
                "project_id": op.project_id,
                "operation_type": op.operation_type,
                "vector_count": op.vector_count,
                "duration_ms": op.duration_ms,
                "status": op.status
            })
        
        return templates.TemplateResponse("admin/usage.html", {
            "request": request,
            "auth": auth,
            "usage_summary": usage_summary,
            "top_users": top_users,
            "top_projects": top_projects,
            "quota_status": quota_status,
            "operations_chart_data": operations_chart_data,
            "recent_operations": recent_operations,
            "time_range": time_range
        })
    
    return router
