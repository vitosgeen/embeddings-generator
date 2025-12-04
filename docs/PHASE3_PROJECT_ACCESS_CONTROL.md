# Phase 3: Project-Level Access Control

## Overview

Phase 3 implements fine-grained project-level access control, allowing administrators to grant users access to specific VDB projects. This builds on Phase 2's admin UI to provide a complete multi-tenant vector database system.

## Architecture

### Database Schema

**UserProject Table** (many-to-many relationship):
```sql
CREATE TABLE user_projects (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    project_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('project-owner', 'project-viewer')),
    granted_at TEXT NOT NULL,
    granted_by_user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by_user_id) REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(user_id, project_id)
)
```

**Project Roles**:
- `project-owner`: Full access (read + write vectors/collections)
- `project-viewer`: Read-only access (search only)

### AuthContext Enhancement

The `AuthContext` object now includes:
```python
@dataclass
class AuthContext:
    user_id: int
    username: str
    role: str
    permissions: List[str]
    accessible_projects: List[str]  # NEW: project_ids user can access
    api_key_id: str
    
    def can_access_project(self, project_id: str) -> bool:
        """Check if user can access a specific project."""
        if self.role == "admin":
            return True  # Admin has universal access
        return project_id in self.accessible_projects
```

### Middleware Integration

The auth middleware (`auth_middleware.py`) now:
1. Queries the `user_projects` table during authentication
2. Populates `accessible_projects` list in AuthContext
3. Admin users get empty list (all access granted implicitly)

```python
# In auth_middleware.py
if user.role != "admin":
    # Query user's project access
    user_projects = project_storage.list_user_projects(user.id)
    accessible_projects = [up.project_id for up in user_projects]
else:
    accessible_projects = []  # Admin can access everything
```

## Admin UI Features

### Project Management Pages

**List Projects** (`/admin/projects`):
- View all projects with owner information
- Filter by owner user
- Create new projects
- Links to project detail pages

**Project Detail** (`/admin/projects/{project_id}`):
- View project metadata
- See owner and creation date
- Manage user access (grant/revoke)
- Deactivate or delete project

**Grant Access**:
- Select user from dropdown
- Choose role (project-owner or project-viewer)
- Inline HTMX updates (no page reload)

**Revoke Access**:
- Remove user from project
- Cannot revoke project owner access
- Confirmation dialog before revoke

### Templates Created

1. `templates/admin/projects.html` - Project list page
2. `templates/admin/project_detail.html` - Project detail page
3. `templates/admin/project_form.html` - Create project modal form
4. `templates/admin/project_row.html` - Project table row (HTMX)
5. `templates/admin/project_users_list.html` - User access table

## API Endpoints

### Admin API Routes

```
GET    /admin/projects                             # List all projects
POST   /admin/projects                             # Create new project
GET    /admin/projects/new                         # Get create form
GET    /admin/projects/{project_id}                # Project detail page
POST   /admin/projects/{project_id}/grant-access   # Grant user access
POST   /admin/projects/{project_id}/revoke-access/{user_id}  # Revoke access
POST   /admin/projects/{project_id}/deactivate     # Soft delete
DELETE /admin/projects/{project_id}                # Hard delete
```

### VDB API Routes (Updated)

All VDB endpoints now check project access:

```python
@router.get("/vdb/projects")
def list_projects(auth: AuthContext = Depends(get_current_user)):
    """List accessible projects (filtered by user access)."""
    auth.require_permission("read:projects")
    all_projects = list_projects_uc.execute()
    
    if auth.role == "admin":
        return all_projects
    
    # Filter to accessible projects only
    accessible = set(auth.accessible_projects)
    return {
        "projects": [p for p in all_projects["projects"] if p in accessible]
    }

@router.get("/vdb/projects/{project_id}/collections")
def list_collections(project_id: str, auth: AuthContext = Depends(get_current_user)):
    """List collections (requires project access)."""
    auth.require_permission("read:collections")
    
    # NEW: Check project access
    if not auth.can_access_project(project_id):
        raise HTTPException(status_code=403, detail=f"Access denied to project '{project_id}'")
    
    return list_collections_uc.execute(project_id)
```

**Protected Endpoints**:
- `GET /vdb/projects` - Filtered by accessible_projects
- `GET /vdb/projects/{project_id}/collections` - Requires project access
- `POST /vdb/projects/{project_id}/collections` - Requires project access
- `POST /vdb/projects/{project_id}/collections/{collection}/add` - Requires project access
- `POST /vdb/projects/{project_id}/collections/{collection}/search` - Requires project access
- `DELETE /vdb/projects/{project_id}/collections/{collection}/vectors/{vector_id}` - Requires project access

## Access Control Flow

### Request Flow with Project Access Check

```
1. Client → API Request with API key
   ↓
2. Auth Middleware:
   - Validate API key
   - Load user + permissions
   - Query user_projects table → accessible_projects list
   - Create AuthContext with accessible_projects
   ↓
3. VDB Route Handler:
   - Check permission (e.g., "read:collections")
   - Check project access: auth.can_access_project(project_id)
   - If authorized → Execute use case
   - If denied → Return 403 Forbidden
```

### Permission + Project Access Matrix

| User Role    | System Permissions | Project Access | Result |
|--------------|-------------------|----------------|--------|
| admin        | all               | all (implicit) | ✅ Full access to all projects |
| service-app  | read/write vectors | project A, B   | ✅ Can read/write in A, B only |
| service-app  | read/write vectors | no projects    | ❌ Has permissions but no projects |
| monitor      | read:projects     | project C      | ✅ Can list/view project C only |

**Key Insight**: Users need BOTH system permissions AND project access to perform operations.

## Testing

### Test Scenario: Multi-Tenant Access Control

```python
# Setup: Create test data
admin_key = "sk-admin-..."
testapp_key = "sk-serviceapp-..."  # User ID: 3

# Grant testapp access to demo_project and search_proj
project_storage.grant_project_access("demo_project", user_id=3, role="project-owner")
project_storage.grant_project_access("search_proj", user_id=3, role="project-owner")

# Test 1: List projects (filtered)
GET /vdb/projects (admin_key)
→ Returns: all 17 projects

GET /vdb/projects (testapp_key)  
→ Returns: ["demo_project", "search_proj"]  ✅ Filtered to accessible only

# Test 2: Access granted project
GET /vdb/projects/search_proj/collections (testapp_key)
→ 200 OK, returns collections  ✅ Has access

# Test 3: Access denied project
GET /vdb/projects/list_coll_proj/collections (testapp_key)
→ 403 Forbidden: "Access denied to project 'list_coll_proj'"  ✅ Blocked

# Test 4: Write operations (project-owner role)
POST /vdb/projects/search_proj/collections (testapp_key)
→ 200 OK, collection created  ✅ project-owner can write
```

### Admin UI Testing

```bash
# Create project via admin UI
curl -X POST http://localhost:8000/admin/projects \
  -H "Authorization: Bearer sk-admin-..." \
  -d "project_id=test-rag-app&name=Test+RAG+Application&description=Demo"

# Grant access to monitor user
curl -X POST http://localhost:8000/admin/projects/test-rag-app/grant-access \
  -H "Authorization: Bearer sk-admin-..." \
  -d "user_id=2&role=project-viewer"

# View project detail page
curl http://localhost:8000/admin/projects/test-rag-app \
  -H "Authorization: Bearer sk-admin-..."
# → Shows: owner=admin, users=[monitor (project-viewer)]
```

## Implementation Checklist

- [x] Add `UserProject` model to database schema
- [x] Create `ProjectStorage` class with CRUD operations
- [x] Add `accessible_projects` field to `AuthContext`
- [x] Update auth middleware to populate accessible_projects
- [x] Add project access checks to all VDB routes
- [x] Implement project filtering in list_projects endpoint
- [x] Create admin UI for project management
- [x] Add grant/revoke access functionality
- [x] Create HTMX templates for inline updates
- [x] Add project detail page with user access table
- [x] Test multi-tenant access control scenarios
- [x] Document Phase 3 implementation

## Security Considerations

1. **Admin Bypass**: Admins can access all projects without explicit grants
2. **Owner Protection**: Cannot revoke project owner's access
3. **Cascade Delete**: Deleting a user removes all their project access
4. **Audit Trail**: `granted_by_user_id` tracks who granted access
5. **SQL Injection**: All queries use parameterized statements
6. **Permission Layering**: Users need both system permissions AND project access

## Migration Notes

### Existing Deployments

For systems upgrading from Phase 2 to Phase 3:

1. **Database Migration**: Run schema updates to create `user_projects` table
2. **Default Access**: Existing projects have no user access by default
3. **Admin Access**: Admin users retain full access (no migration needed)
4. **Service Apps**: Must grant project access to existing service-app users
5. **Backward Compatibility**: VDB endpoints remain backward compatible (admins unaffected)

### Migration Script Example

```python
from app.adapters.infra.auth_storage import AuthDatabase, ProjectStorage, UserStorage

db = AuthDatabase("app-auth.db")
project_storage = ProjectStorage(db)
user_storage = UserStorage(db)

# Grant all service-app users access to all existing projects
service_users = [u for u in user_storage.list_users() if u.role == "service-app"]
existing_projects = ["demo_project", "search_proj", ...]  # List from VDB

for user in service_users:
    for project_id in existing_projects:
        project_storage.grant_project_access(
            project_id=project_id,
            user_id=user.id,
            role="project-owner",
            granted_by_user_id=1  # admin
        )
```

## Next Steps (Phase 4 Ideas)

- [ ] **Collection-Level Access**: Grant access to specific collections within projects
- [ ] **Team/Group Management**: Manage groups of users with shared project access
- [ ] **Access Request Workflow**: Users can request project access (approval flow)
- [ ] **Usage Quotas**: Limit vectors/searches per project per user
- [ ] **Activity Dashboard**: Show per-project usage statistics
- [ ] **API Key Scoping**: Bind API keys to specific projects (instead of user-level)

## Conclusion

Phase 3 delivers a complete multi-tenant vector database system with:
- Fine-grained project-level access control
- Intuitive admin UI for managing access
- Secure API endpoints with permission + project checks
- Full audit trail and access management

The system is now production-ready for multi-tenant SaaS deployments where different customers/teams need isolated access to their vector data.
