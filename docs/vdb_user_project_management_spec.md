# User & Project Management for VDB Service — Technical Specification

**Version:** 1.1  
**Status:** Draft  
**Last Updated:** December 4, 2025

## 1. Scope

This specification extends the existing Vector Database Service (VDB Service) with:

1. **User & project management** — Multi-tenant isolation with user-to-project mappings
2. **Encrypted SQLite storage** — Protected storage for users, API keys, and projects
3. **API key lifecycle** — Create, revoke, rotate, and audit key usage
4. **Role-based access control (RBAC)** — Fine-grained permissions per role
5. **HTMX-based admin UI** — Modern, zero-JS admin interface (no CLI required)
6. **Bootstrap identities** — Seed built-in users from environment variables (`admin`, `monitor`, `service-app`)
7. **Audit logging** — Track all authentication attempts and administrative actions

## 2. Roles & Access Model

### 2.1 Roles

The system supports four roles with hierarchical permissions:

| Role | Source | Scope | Use Case |
|------|--------|-------|----------|
| **admin** | Environment | Global | Full system access, user/project management |
| **monitor** | Environment | Global | Read-only health checks, metrics, auditing |
| **service-app** | Environment | Global | Application-level access, no admin operations |
| **project-owner** | Admin UI | Project-scoped | Access only to assigned projects |

**Notes:**
- Environment-sourced roles (`admin`, `monitor`, `service-app`) are bootstrapped on first startup
- `project-owner` roles are created dynamically through admin UI
- Multiple users can share the same role
- A user can own multiple projects

### 2.2 Permissions

Permissions are granted per role and validated on each request:

```yaml
admin:
  - all  # Wildcard permission for everything

monitor:
  - read:health         # GET /health
  - read:metrics        # GET /metrics (new endpoint)
  - read:audit-logs     # GET /admin/audit-logs
  - read:projects       # List all projects
  - read:users          # List all users

service-app:
  - read:projects       # List own projects
  - read:collections    # List collections in accessible projects
  - write:collections   # Create collections
  - write:vectors       # Add/update vectors
  - delete:vectors      # Delete vectors
  - search:vectors      # Search within collections

project-owner:
  - read:project        # Read project details (own projects only)
  - read:collections    # List collections (own projects only)
  - write:collections   # Create collections (own projects only)
  - write:vectors       # Add/update vectors (own projects only)
  - delete:vectors      # Delete vectors (own projects only)
  - search:vectors      # Search within collections (own projects only)
```

**Permission Validation:**
- Middleware checks permission + project ownership before processing request
- `admin` role bypasses all project-level checks
- Failed checks return `403 Forbidden` with clear error messages

## 3. Storage — SQLite with Protection

### 3.1 Backend

- **Database file:** `./data/auth.db` (configurable via `AUTH_DB_PATH` env var)
- **Engine:** SQLite 3.35+ (supports JSON, window functions)
- **Connection pooling:** Not required (single-process FastAPI with async SQLite)
- **Migrations:** Alembic-based schema versioning

### 3.2 Security

#### 3.2.1 API Key Hashing
- **Algorithm:** Argon2id (recommended) or Bcrypt (fallback)
- **Argon2 params:** `time_cost=2, memory_cost=65536, parallelism=4`
- **Key format:** `sk-{role}-{random_24_chars}` (e.g., `sk-admin-a1b2c3d4e5f6g7h8i9j0k1l2`)
- **Storage:** Only hash stored in DB, plaintext shown once at creation

#### 3.2.2 Database Encryption (Optional)
- **Library:** SQLCipher (via `pysqlcipher3`)
- **Activation:** Set `AUTH_DB_ENCRYPTION_KEY` environment variable
- **Key derivation:** PBKDF2 with 256,000 iterations
- **Cipher:** AES-256-CBC

#### 3.2.3 Secrets Management
- API keys never logged or included in error messages
- Database encryption key stored in secure vault (production) or env (dev)
- Automatic key rotation reminders (90-day default)

### 3.3 Database Schema

#### Table: `users`
Stores user identities and their base roles.

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'monitor', 'service-app', 'project-owner')),
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT 1,
    metadata JSON  -- Additional user properties
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(active);
```

#### Table: `api_keys`
Stores hashed API keys with lifecycle tracking.

```sql
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    key_id TEXT UNIQUE NOT NULL,  -- Public identifier (e.g., 'sk-admin-abc123...')
    key_hash TEXT NOT NULL,        -- Argon2/Bcrypt hash
    label TEXT,                    -- Human-readable label (e.g., 'Production API', 'Dev Testing')
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    revoked_at TIMESTAMP,
    expires_at TIMESTAMP,          -- Optional expiration
    active BOOLEAN DEFAULT 1,
    metadata JSON,                 -- IP restrictions, rate limits, etc.
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_active ON api_keys(active);
```

#### Table: `projects`
Stores project metadata and ownership.

```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT UNIQUE NOT NULL,  -- User-facing ID (e.g., 'my-rag-app')
    owner_user_id INTEGER NOT NULL,
    name TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT 1,
    metadata JSON,  -- Custom project settings
    FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE RESTRICT
);

CREATE INDEX idx_projects_project_id ON projects(project_id);
CREATE INDEX idx_projects_owner ON projects(owner_user_id);
CREATE INDEX idx_projects_active ON projects(active);
```

#### Table: `user_projects`
Many-to-many mapping for project access.

```sql
CREATE TABLE user_projects (
    user_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    role TEXT DEFAULT 'project-owner' CHECK(role IN ('project-owner', 'project-viewer')),
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER,  -- Admin user who granted access
    PRIMARY KEY (user_id, project_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_user_projects_user ON user_projects(user_id);
CREATE INDEX idx_user_projects_project ON user_projects(project_id);
```

#### Table: `audit_logs`
Tracks authentication events and admin actions.

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    action TEXT NOT NULL,  -- 'login', 'api_call', 'key_created', 'key_revoked', etc.
    resource_type TEXT,    -- 'user', 'project', 'api_key', 'vector', etc.
    resource_id TEXT,
    status TEXT,           -- 'success', 'failure', 'denied'
    ip_address TEXT,
    user_agent TEXT,
    details JSON,          -- Additional context
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_status ON audit_logs(status);
```

## 4. API Key Lifecycle

### 4.1 Key Generation

**Format:** `sk-{role}-{random_24_chars}`

**Process:**
1. Admin creates key via UI with label (e.g., "Production API - Service A")
2. System generates cryptographically secure random key
3. Key hash computed (Argon2id/Bcrypt)
4. **Plaintext key shown ONCE** in UI with copy button
5. Only hash stored in database
6. Audit log entry created

**Example:**
```
Plaintext: sk-admin-x7k2p9m4n8q1r5t3w6y0
Stored:    $argon2id$v=19$m=65536,t=2,p=4$...
```

### 4.2 Key Validation

On each authenticated request:
1. Extract `Bearer {key}` from `Authorization` header
2. Lookup `api_keys` table by `key_id` prefix (first 16 chars for performance)
3. Verify hash matches (Argon2/Bcrypt verification)
4. Check `active=1` and `revoked_at IS NULL`
5. Check `expires_at` if set
6. Update `last_used_at` timestamp (async, non-blocking)
7. Load user, role, and project access
8. Inject `AuthContext` into request state

### 4.3 Key Revocation

**Manual Revocation:**
- Admin clicks "Revoke" in UI
- Sets `active=0`, `revoked_at=NOW()`
- Key immediately stops working
- Audit log records revocation with reason

**Automatic Revocation:**
- User deletion → cascade revokes all keys
- Expiration date reached → automatic revocation
- Suspicious activity detected → emergency revocation

### 4.4 Key Rotation

**Process:**
1. Admin initiates rotation for existing key
2. New key generated with same permissions
3. Old key marked for revocation (grace period: 24h default)
4. Both keys work during grace period
5. After grace period, old key auto-revoked
6. Email notification sent to user (if email configured)

**Rotation Policies:**
- Recommended: 90 days for production keys
- Monitor role: 180 days
- Admin role: 30-60 days (stricter)

### 4.5 Key Metadata & Restrictions

Optional metadata stored in `api_keys.metadata` JSON field:

```json
{
  "ip_whitelist": ["192.168.1.0/24", "10.0.0.5"],
  "rate_limit": {
    "requests_per_minute": 100,
    "requests_per_day": 10000
  },
  "allowed_endpoints": ["/vdb/*", "/embed"],
  "created_by": "admin-user",
  "purpose": "Production RAG system",
  "environment": "prod"
}
```

## 5. Authentication Middleware

### 5.1 Request Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Request arrives with Authorization: Bearer sk-xxx-yyy    │
└─────────────────────────────────────┬───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Middleware extracts key from header                      │
└─────────────────────────────────────┬───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Query api_keys table by key_id prefix                    │
│    → Check active=1, revoked_at IS NULL, expires_at         │
└─────────────────────────────────────┬───────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Verify hash (Argon2/Bcrypt) - constant time              │
└─────────────────────────────────────┬───────────────────────┘
                                      │
                  ┌───────────────────┴───────────────────┐
                  │                                       │
         ❌ Invalid                                    ✅ Valid
                  │                                       │
                  ▼                                       ▼
    ┌──────────────────────────┐      ┌──────────────────────────────┐
    │ Return 401 Unauthorized  │      │ 5. Load user & permissions   │
    │ Log failed attempt       │      │    → JOIN users, user_projects│
    └──────────────────────────┘      └──────────────┬───────────────┘
                                                      │
                                                      ▼
                                      ┌──────────────────────────────┐
                                      │ 6. Build AuthContext object  │
                                      │    - user_id, username, role │
                                      │    - permissions[]           │
                                      │    - accessible_projects[]   │
                                      └──────────────┬───────────────┘
                                                      │
                                                      ▼
                                      ┌──────────────────────────────┐
                                      │ 7. Inject context into       │
                                      │    request.state.auth        │
                                      └──────────────┬───────────────┘
                                                      │
                                                      ▼
                                      ┌──────────────────────────────┐
                                      │ 8. Update last_used_at       │
                                      │    (async background task)   │
                                      └──────────────┬───────────────┘
                                                      │
                                                      ▼
                                      ┌──────────────────────────────┐
                                      │ 9. Proceed to endpoint       │
                                      └──────────────────────────────┘
```

### 5.2 AuthContext Object

```python
@dataclass
class AuthContext:
    user_id: int
    username: str
    role: str
    permissions: List[str]
    accessible_projects: List[str]  # project_ids user can access
    api_key_id: str  # For audit logging
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return "all" in self.permissions or permission in self.permissions
    
    def can_access_project(self, project_id: str) -> bool:
        """Check if user can access specific project."""
        return self.role == "admin" or project_id in self.accessible_projects
```

### 5.3 Endpoint Protection

**Public endpoints** (no auth required):
- `GET /` - Homepage
- `GET /health` - Health check
- `GET /docs` - API documentation
- `GET /admin/login` - Admin login page

**Authenticated endpoints** (Bearer token required):
- `POST /embed` - Generate embeddings
- All `/vdb/*` endpoints - Vector database operations

**Admin-only endpoints** (requires `admin` role):
- `GET /admin/users` - User management
- `POST /admin/users` - Create user
- `POST /admin/api-keys` - Generate API key
- `GET /admin/audit-logs` - View audit logs

### 5.4 Error Responses

```json
// 401 Unauthorized - Invalid/missing token
{
  "detail": "Invalid or expired API key",
  "error_code": "AUTH_INVALID_KEY"
}

// 403 Forbidden - Valid token, insufficient permissions
{
  "detail": "Insufficient permissions to access this resource",
  "error_code": "AUTH_FORBIDDEN",
  "required_permission": "write:collections"
}

// 403 Forbidden - Valid token, wrong project
{
  "detail": "Access denied to project 'customer-123'",
  "error_code": "AUTH_PROJECT_ACCESS_DENIED",
  "project_id": "customer-123"
}
```

## 6. Admin HTMX UI

### 6.1 Technology Stack

- **Backend:** FastAPI with Jinja2 templates
- **Frontend:** HTMX 1.9+ for dynamic interactions (zero JavaScript)
- **CSS:** TailwindCSS or simple custom styles
- **Forms:** CSRF protection via `python-multipart`
- **Session:** Secure cookies with `itsdangerous`

### 6.2 Pages & Features

#### 6.2.1 Login Page (`/admin/login`)
- Simple form: username + API key (for admin role)
- Or admin password (optional, for human admins)
- Session cookie set on success
- Redirect to dashboard

#### 6.2.2 Dashboard (`/admin`)
- Summary cards:
  - Total users
  - Total projects
  - Active API keys
  - Recent activity (last 10 audit logs)
- Quick actions: Create user, Create project

#### 6.2.3 Users Management (`/admin/users`)

**List View:**
- Table with columns: Username, Role, Email, Created, Active, Actions
- Filters: Role, Active status
- Search by username
- Pagination (50 per page)
- Actions: Edit, Deactivate, View Keys

**Create/Edit Form:**
- Fields: Username, Role, Email, Active checkbox
- Validation: Unique username, valid email
- HTMX inline validation (check username availability)

**User Details Page:**
- User info display
- List of API keys (with create button)
- List of accessible projects
- Audit log for this user (last 50 actions)

#### 6.2.4 Projects Management (`/admin/projects`)

**List View:**
- Table: Project ID, Name, Owner, Collections Count, Created, Actions
- Search by project ID or name
- Filter by owner
- Actions: Edit, View Collections, Manage Access

**Create/Edit Form:**
- Fields: Project ID (slug), Name, Description, Owner (dropdown)
- Validation: Unique project ID, alphanumeric + hyphens only

**Project Access Management:**
- Grant access to additional users (multi-select + role)
- Revoke access from users
- HTMX live search for users

#### 6.2.5 API Keys Management (`/admin/api-keys`)

**List View:**
- Table: Key ID (masked), User, Label, Created, Last Used, Status, Actions
- Filter: Active/Revoked, User, Expiration status
- Sort: Last used, Created date
- Actions: View Details, Revoke, Rotate

**Create Form:**
- Select user (dropdown)
- Label (required)
- Expiration (optional date picker)
- Advanced: IP whitelist, rate limits
- **Key Display:** After creation, show plaintext key ONCE with copy button
  - ⚠️ Warning: "Save this key now. It won't be shown again."
  - Copy to clipboard button
  - Download as `.txt` file option

**Key Details Page:**
- Metadata display
- Usage statistics (requests per day chart)
- Revocation button with reason input
- Rotation button (generates new key)

#### 6.2.6 Audit Logs (`/admin/audit-logs`)

**List View:**
- Table: Timestamp, User, Action, Resource, Status, IP, Details
- Filters:
  - Date range picker
  - User dropdown
  - Action type (multi-select)
  - Status (success/failure/denied)
- Export: Download as CSV
- Pagination (100 per page)
- Real-time updates via HTMX polling (optional)

### 6.3 HTMX Patterns

**Inline Form Validation:**
```html
<input name="username" 
       hx-post="/admin/validate/username" 
       hx-trigger="blur" 
       hx-target="#username-error">
<span id="username-error"></span>
```

**Dynamic List Updates:**
```html
<button hx-post="/admin/api-keys/revoke/123" 
        hx-target="#key-row-123" 
        hx-swap="outerHTML"
        hx-confirm="Are you sure you want to revoke this key?">
  Revoke
</button>
```

**Search with Auto-complete:**
```html
<input name="search" 
       hx-get="/admin/users/search" 
       hx-trigger="keyup changed delay:300ms" 
       hx-target="#user-list">
```

**Modal Dialogs:**
```html
<div hx-get="/admin/users/123/edit" 
     hx-target="#modal-content" 
     hx-swap="innerHTML">
  Edit User
</div>
```

### 6.4 UI/UX Considerations

- **Mobile-responsive:** Works on tablets and phones
- **Keyboard navigation:** Tab order, Enter to submit
- **Accessibility:** ARIA labels, semantic HTML
- **Loading states:** HTMX indicators for async operations
- **Success/error toasts:** Temporary notifications (HTMX OOB swaps)
- **Confirmation dialogs:** For destructive actions (revoke, delete)
- **Copy-to-clipboard:** One-click copy for API keys, project IDs

## 7. Security

### 7.1 API Key Security

- ✅ **Hashing:** Argon2id with proper parameters (time=2, memory=64MB, parallelism=4)
- ✅ **No plaintext storage:** Keys shown once at creation, never retrievable
- ✅ **Constant-time comparison:** Prevents timing attacks during verification
- ✅ **Rate limiting:** Per-key request limits (configurable in metadata)
- ✅ **Key rotation:** Automated reminders, grace period for zero-downtime rotation
- ✅ **Expiration:** Optional time-based expiration for temporary keys

### 7.2 Database Security

- ✅ **Encryption at rest:** Optional SQLCipher with AES-256
- ✅ **Connection security:** Local file access only (no network exposure)
- ✅ **Prepared statements:** All queries use parameterized statements (SQL injection prevention)
- ✅ **Backups:** Regular automated backups with encryption
- ✅ **File permissions:** `chmod 600` on auth.db file (owner read/write only)

### 7.3 Admin UI Security

- ✅ **CSRF protection:** Token validation on all POST/PUT/DELETE requests
- ✅ **Session management:** Secure HttpOnly cookies with SameSite=Strict
- ✅ **Session timeout:** 30 minutes inactivity (configurable)
- ✅ **Password hashing:** Admin passwords use Argon2id (if password auth enabled)
- ✅ **Brute force protection:** Rate limiting on login attempts (5 attempts → 15 min lockout)
- ✅ **Content Security Policy:** Strict CSP headers to prevent XSS
- ✅ **HTTPS only:** Production deployment requires TLS

### 7.4 Logging Security

- ❌ **Never log:** API keys (plaintext), password hashes, encryption keys
- ✅ **Always log:** Failed authentication attempts, authorization failures
- ✅ **Sanitize:** Remove sensitive data from error messages
- ✅ **Audit trail:** All admin actions logged with timestamp, IP, user agent
- ✅ **Log rotation:** Prevent disk space exhaustion
- ✅ **Retention policy:** 90 days for audit logs (configurable)

### 7.5 Network Security

- ✅ **IP whitelisting:** Optional per-key IP restrictions
- ✅ **Rate limiting:** Global (1000 req/min) and per-key limits
- ✅ **Request size limits:** Max 10MB payload (prevents DoS)
- ✅ **Timeout enforcement:** 30s request timeout
- ✅ **CORS policy:** Restricted origins in production

### 7.6 Threat Mitigation

| Threat | Mitigation |
|--------|------------|
| **Key leakage** | Expiration, rotation, revocation, no plaintext storage |
| **SQL injection** | Parameterized queries, ORM usage |
| **XSS attacks** | CSP headers, HTMX auto-escaping, Jinja2 auto-escaping |
| **CSRF attacks** | Token validation on state-changing operations |
| **Brute force** | Rate limiting, account lockout, Argon2 slow hashing |
| **Timing attacks** | Constant-time hash comparison |
| **Privilege escalation** | Role validation on every request, immutable admin role |
| **Data exfiltration** | Project-level isolation, permission checks |
| **DoS attacks** | Rate limiting, request size limits, connection pooling |

## 8. First Startup (Bootstrap)

### 8.1 Environment Configuration

Bootstrap users are configured via environment variables:

```bash
# Format: account_name:api_key,account_name2:api_key2
API_KEYS=admin:sk-admin-abc123xyz789,monitor:sk-monitor-def456uvw012,service-app:sk-service-ghi789rst345

# Optional: Custom database paths
AUTH_DB_PATH=./data/auth.db
VDB_STORAGE_PATH=./data/vdb-storage

# Optional: Database encryption
AUTH_DB_ENCRYPTION_KEY=your-secret-encryption-key-here

# Optional: Session configuration
SESSION_SECRET_KEY=your-session-secret-key
SESSION_TIMEOUT_MINUTES=30
```

### 8.2 Bootstrap Process

On first startup (when `auth.db` doesn't exist):

1. **Create database file** with proper permissions (600)
2. **Apply schema migrations** (all tables, indexes)
3. **Parse `API_KEYS` environment variable**
4. **For each key in API_KEYS:**
   - Determine role from account name (`admin`, `monitor`, or `service-app`)
   - Create user record in `users` table
   - Hash the API key (Argon2id)
   - Insert into `api_keys` table with label "Bootstrap Key"
   - Log creation in `audit_logs`

5. **Create default admin project** (optional):
   - Project ID: `system-default`
   - Owner: First admin user
   - Used for system operations

6. **Log bootstrap completion**

### 8.3 Bootstrap Example

```python
# Pseudocode for bootstrap logic
def bootstrap_auth_db():
    if auth_db_exists():
        logger.info("Auth database already exists, skipping bootstrap")
        return
    
    logger.info("Starting bootstrap process...")
    
    # Create database and schema
    create_database()
    apply_migrations()
    
    # Parse environment
    api_keys_env = os.getenv("API_KEYS", "")
    if not api_keys_env:
        logger.warning("No API_KEYS found in environment, creating empty database")
        return
    
    # Seed users and keys
    for account, key in parse_api_keys(api_keys_env):
        role = infer_role(account)  # admin, monitor, or service-app
        
        user_id = create_user(
            username=account,
            role=role,
            email=None,
            active=True
        )
        
        key_hash = hash_api_key(key)
        
        create_api_key(
            user_id=user_id,
            key_id=key,  # Public identifier
            key_hash=key_hash,
            label=f"Bootstrap Key - {account}",
            active=True
        )
        
        audit_log(
            action="bootstrap_user_created",
            user_id=user_id,
            details={"role": role, "source": "environment"}
        )
    
    logger.info(f"Bootstrap complete: {len(users)} users created")
```

### 8.4 Idempotency

- Bootstrap only runs if `auth.db` doesn't exist
- Re-running the application with existing DB is safe (no-op)
- To re-bootstrap: Delete `auth.db` and restart application
- **Production warning:** Deleting DB loses all users, keys, and projects

### 8.5 Migration from Existing System

If migrating from the current simple API key system:

1. Export existing `API_KEYS` environment variable
2. Stop application
3. Run bootstrap process
4. Bootstrap will create users with same API keys
5. Keys continue to work without changes
6. **Backward compatible:** No breaking changes for API consumers

### 8.6 Health Check Enhancement

Add database connectivity check to `/health` endpoint:

```json
{
  "status": "ok",
  "model_id": "BAAI/bge-base-en-v1.5",
  "device": "cuda",
  "dim": 768,
  "batch_size": 32,
  "auth_db": {
    "status": "connected",
    "users_count": 12,
    "active_keys_count": 18,
    "projects_count": 5
  },
  "vdb": {
    "status": "connected",
    "storage_path": "./data/vdb-storage"
  }
}
```

## 9. Non-Functional Requirements

### 9.1 Performance

- **Authentication latency:** < 10ms per request (cached user context)
- **Database queries:** Single query for auth + permissions (JOIN optimization)
- **API key hashing:** Argon2 verification ~50ms (acceptable for auth)
- **Concurrent users:** Support 100+ simultaneous authenticated requests
- **Session storage:** In-memory or Redis (for multi-instance deployments)

### 9.2 Reliability

- **Database backups:** 
  - Automated hourly backups (last 24h retained)
  - Daily backups (last 30 days retained)
  - Weekly backups (last 12 weeks retained)
  - Backup storage: Local + S3 (production)

- **Disaster recovery:**
  - Backup restoration tested monthly
  - RTO (Recovery Time Objective): < 1 hour
  - RPO (Recovery Point Objective): < 1 hour

- **Data integrity:**
  - Foreign key constraints enforced
  - Transactions for multi-table operations
  - Regular PRAGMA integrity_check

### 9.3 Scalability

- **Database size:** SQLite efficient up to 100GB (millions of users)
- **Query optimization:** Indexes on all foreign keys and search columns
- **Connection pooling:** Not required (single-process async)
- **Horizontal scaling:** Shared SQLite via NFS or migrate to PostgreSQL

### 9.4 Monitoring & Observability

- **Metrics (Prometheus format):**
  - `auth_requests_total{status="success|failure|denied"}`
  - `auth_latency_seconds{quantile="0.5|0.9|0.99"}`
  - `active_sessions_count`
  - `api_keys_total{status="active|revoked|expired"}`
  - `database_size_bytes`
  - `backup_last_success_timestamp`

- **Logging:**
  - Structured JSON logs (compatible with ELK, Datadog)
  - Log levels: DEBUG (dev), INFO (prod), WARN, ERROR
  - Correlation IDs for request tracing

- **Alerts:**
  - Failed auth attempts > 100/min → Potential brute force
  - Database size > 80% capacity → Cleanup needed
  - Backup failure → Immediate notification
  - API key expiration < 7 days → Rotation reminder

### 9.5 Usability

- **Admin UI:**
  - Zero JavaScript required (works with JS disabled)
  - Mobile-responsive design (works on phones/tablets)
  - Keyboard navigation support
  - Screen reader compatible (WCAG 2.1 AA)
  - Dark mode support (optional)

- **Error messages:**
  - User-friendly, actionable error descriptions
  - No stack traces or internal details exposed
  - Link to documentation for common errors

- **Documentation:**
  - API reference (OpenAPI/Swagger)
  - Admin UI user guide
  - Security best practices
  - Troubleshooting guide

### 9.6 Deployment

- **Docker support:**
  - Official Dockerfile provided
  - Multi-stage build (small image size)
  - Health check configured
  - Volume mounts for data persistence

- **Environment variables:**
  - All configuration via env vars (12-factor app)
  - `.env.example` file provided
  - Validation on startup (fail fast if misconfigured)

- **Dependencies:**
  - Python 3.10+
  - SQLite 3.35+ (bundled with Python)
  - Optional: SQLCipher (for encryption)
  - Total dependencies: < 20 packages

### 9.7 Testing

- **Unit tests:** 90%+ code coverage
- **Integration tests:** All API endpoints, auth flows
- **Security tests:** Penetration testing, OWASP Top 10 checks
- **Performance tests:** Load testing with 1000+ concurrent users
- **UI tests:** Playwright/Selenium for admin interface

### 9.8 Compliance & Standards

- **GDPR compliance:**
  - User data deletion (right to be forgotten)
  - Data export functionality
  - Consent management (for optional features)
  - Data retention policies

- **SOC 2 considerations:**
  - Audit logging (all access tracked)
  - Encryption at rest and in transit
  - Access control (RBAC)
  - Change management (version control)

- **Security standards:**
  - OWASP API Security Top 10
  - CWE Top 25 (Common Weakness Enumeration)
  - NIST Cybersecurity Framework

### 9.9 Maintenance

- **Schema migrations:** Alembic-based versioning (zero-downtime upgrades)
- **Database vacuuming:** Scheduled VACUUM operations (monthly)
- **Log rotation:** Automatic cleanup of old logs (90 days retention)
- **Key expiration cleanup:** Automated purge of expired keys (> 1 year old)

---

## 10. Implementation Roadmap

### Phase 1: Core Auth System (Week 1-2)
- [ ] SQLite schema creation
- [ ] User management (CRUD)
- [ ] API key hashing & verification
- [ ] Authentication middleware
- [ ] Bootstrap process
- [ ] Unit tests

### Phase 2: Project Management (Week 3)
- [ ] Project CRUD operations
- [ ] User-project mapping
- [ ] Permission validation
- [ ] Integration with VDB endpoints
- [ ] Integration tests

### Phase 3: Admin UI Foundation (Week 4)
- [ ] HTMX setup & templates
- [ ] Login page & session management
- [ ] Dashboard page
- [ ] Users list & create/edit forms
- [ ] Projects list & create/edit forms

### Phase 4: Admin UI Advanced (Week 5)
- [ ] API key management interface
- [ ] Key creation with one-time display
- [ ] Key revocation & rotation
- [ ] Audit logs viewer
- [ ] Search & filtering

### Phase 5: Security Hardening (Week 6)
- [ ] CSRF protection
- [ ] Rate limiting
- [ ] IP whitelisting
- [ ] SQLCipher integration
- [ ] Security testing

### Phase 6: Polish & Production (Week 7-8)
- [ ] Monitoring & metrics
- [ ] Documentation
- [ ] Performance optimization
- [ ] Backup automation
- [ ] Deployment guides

---

## 11. Open Questions & Future Enhancements

### Open Questions
1. **OAuth2 support?** Should we add OAuth2/OIDC for SSO integration?
2. **Multi-factor authentication?** TOTP (Google Authenticator) for admin users?
3. **Database choice?** PostgreSQL option for high-scale deployments?
4. **Key sharing?** Allow multiple users to share the same API key?

### Future Enhancements
- **Webhooks:** Notify external systems of auth events
- **API rate limiting dashboard:** Real-time usage monitoring
- **Usage analytics:** Per-project/per-user statistics
- **Billing integration:** Usage-based billing for SaaS model
- **Team management:** Organize users into teams with inherited permissions
- **Custom roles:** Allow admins to define custom roles with specific permissions
- **API versioning:** Support multiple API versions simultaneously

---

## Appendix A: API Key Format Specification

**Format:** `sk-{role}-{random_chars}`

**Components:**
- `sk`: Static prefix (Secret Key)
- `role`: 3-15 chars, identifies role (admin, monitor, service, project)
- `random_chars`: 24 chars, cryptographically random (A-Za-z0-9)

**Examples:**
```
sk-admin-x7k2p9m4n8q1r5t3w6y0
sk-monitor-a1b2c3d4e5f6g7h8i9j0
sk-service-k1l2m3n4o5p6q7r8s9t0
sk-project-u1v2w3x4y5z6a7b8c9d0
```

**Validation Regex:**
```regex
^sk-[a-z]{3,15}-[A-Za-z0-9]{24}$
```

---

## Appendix B: Database Indexes

Critical indexes for performance:

```sql
-- Users
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_active ON users(active);

-- API Keys
CREATE INDEX idx_api_keys_key_id ON api_keys(key_id);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_active ON api_keys(active);
CREATE INDEX idx_api_keys_last_used ON api_keys(last_used_at);

-- Projects
CREATE INDEX idx_projects_project_id ON projects(project_id);
CREATE INDEX idx_projects_owner ON projects(owner_user_id);
CREATE INDEX idx_projects_active ON projects(active);

-- User Projects
CREATE INDEX idx_user_projects_user ON user_projects(user_id);
CREATE INDEX idx_user_projects_project ON user_projects(project_id);

-- Audit Logs
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_status ON audit_logs(status);
```
