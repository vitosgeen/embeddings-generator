# Phase 2 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Browser / HTTP Client                        │
│                                                                      │
│  Authorization: Bearer sk-admin-XXXXXXXXXXXXXXXXXXXX                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                │ HTTP Request
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │            AuthenticationMiddleware                            │ │
│  │  - Extract Bearer token from header                           │ │
│  │  - Verify with APIKeyStorage                                  │ │
│  │  - Build AuthContext (user, role, permissions)                │ │
│  │  - Inject into request context                                │ │
│  └─────────────────────────────┬──────────────────────────────────┘ │
│                                │                                     │
│                                ▼                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    Admin Routes                                │ │
│  │  /admin/                 → Dashboard                          │ │
│  │  /admin/users            → User Management                    │ │
│  │  /admin/keys             → API Key Management                 │ │
│  │  /admin/logs             → Audit Log Viewer                   │ │
│  │                                                                │ │
│  │  Each route:                                                   │ │
│  │  1. Checks permissions (auth.require_permission)              │ │
│  │  2. Queries storage layer                                     │ │
│  │  3. Renders Jinja2 template                                   │ │
│  │  4. Logs operation to audit trail                             │ │
│  └─────────────────────────────┬──────────────────────────────────┘ │
└─────────────────────────────────┼──────────────────────────────────┘
                                  │
                                  │ Storage Operations
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Storage Layer                                │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  UserStorage     │  │  APIKeyStorage   │  │ AuditLogStorage  │  │
│  │                  │  │                  │  │                  │  │
│  │  - create_user   │  │  - create_key    │  │  - create_log    │  │
│  │  - list_users    │  │  - list_keys     │  │  - list_logs     │  │
│  │  - get_by_id     │  │  - get_by_id     │  │  - filter_logs   │  │
│  │  - deactivate    │  │  - revoke_key    │  │                  │  │
│  │  - delete        │  │  - delete_key    │  │                  │  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                      │            │
│           └─────────────────────┼──────────────────────┘            │
│                                 │                                   │
│                                 ▼                                   │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    SQLAlchemy ORM                              │ │
│  │                                                                │ │
│  │  Models: User, APIKey, AuditLog                               │ │
│  │  Relationships: User → APIKeys, User → Logs                   │ │
│  │  Session management: Context manager                          │ │
│  └─────────────────────────────┬──────────────────────────────────┘ │
└─────────────────────────────────┼──────────────────────────────────┘
                                  │
                                  │ SQL Queries
                                  ▼
                         ┌─────────────────┐
                         │  SQLite DB      │
                         │  (auth.db)      │
                         │                 │
                         │  Tables:        │
                         │  - users        │
                         │  - api_keys     │
                         │  - audit_logs   │
                         └─────────────────┘
```

## Request Flow Example: Create User

```
1. Browser: POST /admin/users
   Headers: Authorization: Bearer sk-admin-...
   Body: username=demo&role=monitor

2. AuthenticationMiddleware:
   - Extract token: sk-admin-...
   - Lookup in APIKeyStorage
   - Build AuthContext(username='admin', role='admin', permissions=['all'])
   - Attach to request

3. Admin Route Handler:
   - Check permission: auth.require_permission('admin:users')  ✓
   - Validate form data
   - Call UserStorage.create_user(username='demo', role='monitor')
   
4. UserStorage:
   - Create SQLAlchemy User model
   - Insert into database via session
   - Return User instance

5. Audit Logger:
   - AuditLogStorage.create_log(
       action='user_created',
       user_id=auth.user_id,
       details={'username': 'demo'}
     )

6. Template Rendering:
   - Load user_row.html
   - Render with new user data
   - Return HTML fragment

7. HTMX Response:
   - Browser receives HTML
   - Inserts row at top of table
   - Shows toast notification
   - No page reload!
```

## Component Architecture

```
app/
├── domain/
│   └── auth.py                    # Role, AuthContext, APIKeyManager
│
├── adapters/
│   ├── infra/
│   │   └── auth_storage.py        # SQLAlchemy models + storage classes
│   │
│   └── rest/
│       ├── auth_middleware.py     # AuthenticationMiddleware
│       ├── admin_routes.py        # Admin UI routes (NEW)
│       └── fastapi_app.py         # Main app (includes admin router)
│
└── usecases/
    └── (no changes - auth is infrastructure)

templates/
└── admin/                         # HTMX templates (NEW)
    ├── base.html                  # Master template
    ├── dashboard.html             # Stats dashboard
    ├── users.html                 # User list + filters
    ├── user_row.html              # Table row fragment
    ├── user_form.html             # Create user modal
    ├── keys.html                  # Key list + filters
    ├── key_form.html              # Create key modal
    ├── key_created.html           # Success view with plaintext key
    └── logs.html                  # Audit log table
```

## HTMX Interactions

### Modal Form Submission
```html
<!-- Button opens modal -->
<button hx-get="/admin/users/new"
        hx-target="#modal-content"
        onclick="modal.show()">
  New User
</button>

<!-- Modal contains form -->
<form hx-post="/admin/users"
      hx-target="#users-tbody"
      hx-swap="afterbegin">
  <!-- Form fields -->
</form>

<!-- Server returns row HTML -->
<tr id="user-123">
  <td>demo-user</td>
  <td>monitor</td>
  <!-- ... -->
</tr>

<!-- HTMX inserts at top of table, closes modal -->
```

### Inline Delete
```html
<button hx-delete="/admin/users/123"
        hx-confirm="Delete user?"
        hx-target="#user-123"
        hx-swap="outerHTML swap:1s">
  Delete
</button>

<!-- Server returns 200 OK -->
<!-- HTMX removes row with fade animation -->
```

### Filter Dropdown
```html
<select hx-get="/admin/users"
        hx-trigger="change"
        hx-target="#users-table">
  <option value="">All Roles</option>
  <option value="admin">Admin</option>
  <!-- ... -->
</select>

<!-- Server returns filtered table HTML -->
<!-- HTMX replaces entire table -->
```

## Security Model

```
┌─────────────┐
│   Request   │
│  (API Key)  │
└──────┬──────┘
       │
       ▼
┌──────────────────────────┐
│  Authentication          │
│  - Verify key exists     │
│  - Check not expired     │
│  - Check not revoked     │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│  Authorization           │
│  - Load user role        │
│  - Map to permissions    │
│  - Check route requires  │
└──────┬───────────────────┘
       │
       ▼
┌──────────────────────────┐
│  Audit Logging           │
│  - Record action         │
│  - Capture user_id       │
│  - Store result          │
└──────────────────────────┘
```

## Database Schema

```sql
-- Users table
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL,  -- admin, monitor, service-app, project-owner
  email TEXT,
  active BOOLEAN DEFAULT TRUE,
  created_at DATETIME,
  updated_at DATETIME
);

-- API Keys table
CREATE TABLE api_keys (
  id INTEGER PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  key_id TEXT UNIQUE NOT NULL,  -- Public part: sk-admin-abc...
  key_hash TEXT NOT NULL,       -- Argon2 hash
  label TEXT,
  active BOOLEAN DEFAULT TRUE,
  created_at DATETIME,
  last_used_at DATETIME,
  expires_at DATETIME,
  revoked_at DATETIME
);

-- Audit Logs table
CREATE TABLE audit_logs (
  id INTEGER PRIMARY KEY,
  action TEXT NOT NULL,         -- user_created, key_revoked, etc.
  user_id INTEGER,              -- Who did it
  resource_type TEXT,           -- What was affected
  resource_id TEXT,
  status TEXT,                  -- success, failure, denied
  timestamp DATETIME,
  details TEXT                  -- JSON
);
```

## Permission Matrix

| Role         | Permissions                                              | Admin UI Access          |
|--------------|----------------------------------------------------------|--------------------------|
| admin        | all (wildcard)                                           | Full access              |
| monitor      | read:health, read:metrics, read:projects, read:audit-logs | Logs only               |
| service-app  | write:embeddings, read:embeddings, write:collections     | None (API-only role)     |
| project-owner| (scoped to assigned projects - Phase 3)                  | Project-specific (Phase 3)|

## Performance Considerations

- **Database**: SQLite adequate for <10K users/keys, migrate to PostgreSQL for production
- **Caching**: None yet, add Redis for session management in Phase 3
- **Pagination**: Not implemented, add for lists >100 items
- **Indexes**: Created on username, key_id, active, last_used_at, timestamp
- **Connection pooling**: StaticPool for SQLite (single connection), use QueuePool for PostgreSQL

## Future Enhancements

### Phase 3: Project Access Control
- User-to-project associations (UserProject table)
- Scoped permissions (project-owner role)
- Project management UI in admin panel

### Phase 4: Advanced Features
- Session-based authentication (login page)
- Pagination + advanced filtering
- Export functionality (CSV, JSON)
- Rate limiting dashboard
- Dark mode toggle
- WebSocket real-time updates
