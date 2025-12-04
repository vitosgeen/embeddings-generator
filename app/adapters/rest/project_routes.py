"""Admin UI routes for project management and access control."""

from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.domain.auth import AuthContext
from app.adapters.infra.auth_storage import (
    AuthDatabase,
    UserStorage,
    ProjectStorage,
    AuditLogStorage,
)
from app.config import AUTH_DB_PATH
from .auth_middleware import get_current_user


# Initialize templates
templates = Jinja2Templates(directory="templates")

# Initialize storage
_auth_db = AuthDatabase(AUTH_DB_PATH)
_user_storage = UserStorage(_auth_db)
_project_storage = ProjectStorage(_auth_db)
_audit_storage = AuditLogStorage(_auth_db)


def build_project_router() -> APIRouter:
    """Build the project management router."""
    
    router = APIRouter(prefix="/admin/projects", tags=["Project Management"])
    
    # ========================================================================
    # Project Management
    # ========================================================================
    
    @router.get("/", response_class=HTMLResponse)
    async def list_projects(
        request: Request,
        auth: AuthContext = Depends(get_current_user),
        owner_id: Optional[int] = None,
    ):
        """List all projects."""
        auth.require_permission("admin:projects")
        
        projects = _project_storage.list_projects(owner_user_id=owner_id)
        users = _user_storage.list_users()
        
        # Build owner lookup
        user_map = {u.id: u for u in users}
        
        return templates.TemplateResponse("admin/projects.html", {
            "request": request,
            "auth": auth,
            "projects": projects,
            "users": users,
            "user_map": user_map,
            "filter_owner_id": owner_id,
        })
    
    @router.get("/new", response_class=HTMLResponse)
    async def new_project_form(
        request: Request,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Show form to create new project."""
        auth.require_permission("admin:projects")
        
        users = _user_storage.list_users()
        
        return templates.TemplateResponse("admin/project_form.html", {
            "request": request,
            "auth": auth,
            "project": None,
            "users": users,
        })
    
    @router.post("/", response_class=HTMLResponse)
    async def create_project(
        request: Request,
        auth: AuthContext = Depends(get_current_user),
        project_id: str = Form(...),
        owner_user_id: int = Form(...),
        name: Optional[str] = Form(None),
        description: Optional[str] = Form(None),
    ):
        """Create a new project."""
        auth.require_permission("admin:projects")
        
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
            
            # Get owner user
            owner = _user_storage.get_user_by_id(owner_user_id)
            
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
    
    @router.get("/{project_id}", response_class=HTMLResponse)
    async def get_project(
        request: Request,
        project_id: str,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Get project details with user access list."""
        auth.require_permission("admin:projects")
        
        project = _project_storage.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get owner
        owner = _user_storage.get_user_by_id(project.owner_user_id)
        
        # Get users with access
        project_users = _project_storage.list_project_users(project_id)
        
        # Get all users for adding access
        all_users = _user_storage.list_users()
        
        return templates.TemplateResponse("admin/project_detail.html", {
            "request": request,
            "auth": auth,
            "project": project,
            "owner": owner,
            "project_users": project_users,
            "all_users": all_users,
        })
    
    @router.post("/{project_id}/deactivate")
    async def deactivate_project(
        project_id: str,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Deactivate a project."""
        auth.require_permission("admin:projects")
        
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
    
    @router.delete("/{project_id}")
    async def delete_project(
        project_id: str,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Delete a project."""
        auth.require_permission("admin:projects")
        
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
    # User-Project Access Control
    # ========================================================================
    
    @router.get("/{project_id}/access/new", response_class=HTMLResponse)
    async def new_access_form(
        request: Request,
        project_id: str,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Show form to grant user access to project."""
        auth.require_permission("admin:projects")
        
        project = _project_storage.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get users who don't already have access
        all_users = _user_storage.list_users()
        project_users = _project_storage.list_project_users(project_id)
        existing_user_ids = {up[1].user_id for up in project_users}
        available_users = [u for u in all_users if u.id not in existing_user_ids and u.id != project.owner_user_id]
        
        return templates.TemplateResponse("admin/project_access_form.html", {
            "request": request,
            "auth": auth,
            "project": project,
            "users": available_users,
        })
    
    @router.post("/{project_id}/access", response_class=HTMLResponse)
    async def grant_access(
        request: Request,
        project_id: str,
        auth: AuthContext = Depends(get_current_user),
        user_id: int = Form(...),
        role: str = Form(...),
    ):
        """Grant a user access to a project."""
        auth.require_permission("admin:projects")
        
        try:
            user_project = _project_storage.grant_project_access(
                user_id=user_id,
                project_id=project_id,
                role=role,
                granted_by=auth.user_id,
            )
            
            user = _user_storage.get_user_by_id(user_id)
            
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
            
            # Return access row for HTMX to insert
            return templates.TemplateResponse("admin/project_access_row.html", {
                "request": request,
                "user": user,
                "user_project": user_project,
                "project_id": project_id,
            })
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @router.delete("/{project_id}/access/{user_id}")
    async def revoke_access(
        project_id: str,
        user_id: int,
        auth: AuthContext = Depends(get_current_user),
    ):
        """Revoke a user's access to a project."""
        auth.require_permission("admin:projects")
        
        success = _project_storage.revoke_project_access(user_id, project_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Access not found")
        
        user = _user_storage.get_user_by_id(user_id)
        
        _audit_storage.create_log(
            action="project_access_revoked",
            user_id=auth.user_id,
            status="success",
            details={
                "project_id": project_id,
                "revoked_from_user_id": user_id,
                "username": user.username if user else None,
            },
        )
        
        return {"status": "success", "message": f"Access revoked for user {user_id}"}
    
    return router
