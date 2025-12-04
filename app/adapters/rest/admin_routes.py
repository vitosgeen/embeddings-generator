"""Admin UI routes for user and API key management."""

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
from app.config import AUTH_DB_PATH
from .auth_middleware import get_current_user


# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize storage
_auth_db = AuthDatabase(AUTH_DB_PATH)
_user_storage = UserStorage(_auth_db)
_key_storage = APIKeyStorage(_auth_db)
_audit_storage = AuditLogStorage(_auth_db)
_project_storage = ProjectStorage(_auth_db)


def build_admin_router() -> APIRouter:
    """Build the admin UI router."""
    
    router = APIRouter(prefix="/admin", tags=["Admin UI"])
    
    # ========================================================================
    # Dashboard
    # ========================================================================
    
    @router.get("/", response_class=HTMLResponse)
    async def admin_dashboard(
        request: Request,
        auth: AuthContext = Depends(get_current_user),
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
    
    # ========================================================================
    # User Management
    # ========================================================================
    
    @router.get("/users", response_class=HTMLResponse)
    async def list_users(
        request: Request,
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
        user_id: int = Form(...),
        label: str = Form(...),
        expires_days: Optional[int] = Form(None),
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
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
        auth: AuthContext = Depends(get_current_user),
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
    
    return router
