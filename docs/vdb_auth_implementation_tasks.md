# VDB Auth System - Implementation Tasks

**Project:** User & Project Management for Vector Database Service  
**Created:** December 4, 2025  
**Status:** Planning  

---

## 📋 Task Categories

- 🔧 **Infrastructure** - Database, migrations, core setup
- 🔐 **Authentication** - Auth middleware, key management
- 👥 **User Management** - CRUD operations, roles
- 📁 **Project Management** - Multi-tenant isolation
- 🎨 **Admin UI** - HTMX interface
- ✅ **Testing** - Unit, integration, security tests
- 📚 **Documentation** - API docs, guides

---

## Phase 1: Core Auth System (Week 1-2)

### 🔧 Task 1.1: Database Setup & Schema
**Priority:** High | **Effort:** 4 hours | **Assignee:** Backend Dev

- [ ] Install dependencies: `sqlalchemy`, `alembic`, `argon2-cffi`
- [ ] Create `app/adapters/infra/auth_storage.py` module
- [ ] Define SQLAlchemy models:
  - [ ] `User` model with all fields from spec
  - [ ] `APIKey` model with hash storage
  - [ ] `Project` model (VDB projects)
  - [ ] `UserProject` many-to-many model
  - [ ] `AuditLog` model
- [ ] Create Alembic migration scripts
- [ ] Add database initialization function
- [ ] Set file permissions (chmod 600) on auth.db
- [ ] Add `AUTH_DB_PATH` to config.py

**Deliverables:**
- `app/adapters/infra/auth_storage.py`
- `alembic/versions/001_initial_schema.py`
- Updated `app/config.py`
- Updated `requirements.txt`

**Tests:**
- Database creation succeeds
- Schema matches specification
- Migrations apply cleanly

---

### 🔐 Task 1.2: API Key Hashing & Verification
**Priority:** High | **Effort:** 3 hours | **Assignee:** Backend Dev

- [ ] Create `app/domain/auth.py` with:
  - [ ] `generate_api_key()` - Format: `sk-{role}-{24_random_chars}`
  - [ ] `hash_api_key()` - Argon2id with proper parameters
  - [ ] `verify_api_key()` - Constant-time comparison
  - [ ] `APIKeyFormat` validator (regex pattern)
- [ ] Add key format constants to config
- [ ] Implement key generation with cryptographic randomness
- [ ] Add key expiration logic

**Deliverables:**
- `app/domain/auth.py`
- Key generation utilities
- Verification functions

**Tests:**
- Generated keys match format spec
- Hash/verify cycle works correctly
- Invalid keys are rejected
- Constant-time comparison verified

---

### 🔐 Task 1.3: Authentication Middleware
**Priority:** High | **Effort:** 5 hours | **Assignee:** Backend Dev

- [ ] Create `app/adapters/rest/auth_middleware.py`
- [ ] Implement `AuthContext` dataclass:
  - [ ] user_id, username, role
  - [ ] permissions list
  - [ ] accessible_projects list
  - [ ] has_permission() method
  - [ ] can_access_project() method
- [ ] Implement middleware:
  - [ ] Extract Bearer token from header
  - [ ] Query database for key
  - [ ] Verify hash
  - [ ] Check active status, expiration
  - [ ] Load user + permissions
  - [ ] Inject AuthContext into request.state
  - [ ] Update last_used_at (async background)
- [ ] Add error responses (401, 403)
- [ ] Create audit log helper function

**Deliverables:**
- `app/adapters/rest/auth_middleware.py`
- `AuthContext` class
- Middleware function integrated with FastAPI

**Tests:**
- Valid tokens authenticate successfully
- Invalid tokens return 401
- Expired keys are rejected
- last_used_at updates correctly
- Audit logs created for failed attempts

---

### 👥 Task 1.4: User Management (Domain Layer)
**Priority:** High | **Effort:** 4 hours | **Assignee:** Backend Dev

- [ ] Create `app/domain/user.py` with:
  - [ ] `User` value object
  - [ ] `Role` enum (admin, monitor, service-app, project-owner)
  - [ ] User validation logic
- [ ] Create `app/ports/auth_port.py` with:
  - [ ] `UserStoragePort` protocol
  - [ ] `APIKeyStoragePort` protocol
  - [ ] `AuditLogPort` protocol
- [ ] Create use cases in `app/usecases/auth_usecases.py`:
  - [ ] `CreateUserUC`
  - [ ] `GetUserUC`
  - [ ] `ListUsersUC`
  - [ ] `UpdateUserUC`
  - [ ] `DeactivateUserUC`

**Deliverables:**
- `app/domain/user.py`
- `app/ports/auth_port.py`
- `app/usecases/auth_usecases.py`

**Tests:**
- User creation with validation
- Role assignment works
- User lookup by ID and username
- User deactivation cascades properly

---

### 🔐 Task 1.5: Bootstrap Process
**Priority:** High | **Effort:** 3 hours | **Assignee:** Backend Dev

- [ ] Create `app/bootstrap_auth.py`
- [ ] Implement environment parser:
  - [ ] Parse `API_KEYS` from environment
  - [ ] Extract account names and keys
  - [ ] Infer roles from account names
- [ ] Implement bootstrap logic:
  - [ ] Check if auth.db exists
  - [ ] Create database if missing
  - [ ] Seed users from environment
  - [ ] Hash and store API keys
  - [ ] Create audit log entries
- [ ] Add bootstrap call to `main.py` startup
- [ ] Add idempotency checks (skip if DB exists)
- [ ] Create default admin project (optional)

**Deliverables:**
- `app/bootstrap_auth.py`
- Updated `main.py`
- Environment variable documentation

**Tests:**
- Bootstrap creates users correctly
- API keys work after bootstrap
- Re-running bootstrap is safe (no duplicates)
- Missing API_KEYS handled gracefully

---

### ✅ Task 1.6: Unit Tests for Phase 1
**Priority:** High | **Effort:** 6 hours | **Assignee:** QA/Backend Dev

- [ ] Create `tests/unit/test_auth_domain.py`:
  - [ ] Test key generation format
  - [ ] Test hash/verify functions
  - [ ] Test User validation
  - [ ] Test Role enum
- [ ] Create `tests/unit/test_auth_storage.py`:
  - [ ] Test database CRUD operations
  - [ ] Test foreign key constraints
  - [ ] Test cascade deletes
- [ ] Create `tests/unit/test_auth_usecases.py`:
  - [ ] Test all use cases with mocks
  - [ ] Test error handling
  - [ ] Test permission checks

**Deliverables:**
- Complete unit test suite for Phase 1
- 90%+ code coverage for auth modules

**Tests:**
- All unit tests pass
- Coverage report generated

---

## Phase 2: Project Management (Week 3)

### 📁 Task 2.1: Project Management (Domain Layer)
**Priority:** High | **Effort:** 4 hours | **Assignee:** Backend Dev

- [ ] Enhance `app/domain/vdb.py`:
  - [ ] Add `owner_user_id` to project metadata
  - [ ] Add project validation with ownership
- [ ] Create `app/ports/project_port.py`:
  - [ ] `ProjectStoragePort` protocol (already exists, enhance)
  - [ ] `ProjectAccessPort` protocol (new)
- [ ] Create use cases in `app/usecases/project_usecases.py`:
  - [ ] `CreateProjectUC` (with ownership)
  - [ ] `ListProjectsUC` (filtered by user access)
  - [ ] `GetProjectUC` (with access check)
  - [ ] `UpdateProjectUC`
  - [ ] `DeleteProjectUC`
  - [ ] `GrantProjectAccessUC`
  - [ ] `RevokeProjectAccessUC`

**Deliverables:**
- Enhanced VDB domain models
- New project access use cases
- Updated ports

**Tests:**
- Project creation assigns owner
- Access grants work correctly
- Non-owners cannot access projects
- Admin can access all projects

---

### 📁 Task 2.2: User-Project Mapping Storage
**Priority:** High | **Effort:** 3 hours | **Assignee:** Backend Dev

- [ ] Implement `UserProjectStorage` in auth_storage.py:
  - [ ] `grant_access(user_id, project_id, role)`
  - [ ] `revoke_access(user_id, project_id)`
  - [ ] `list_user_projects(user_id)`
  - [ ] `list_project_users(project_id)`
  - [ ] `check_access(user_id, project_id)`
- [ ] Add cascade logic for user/project deletion
- [ ] Add audit logging for access changes

**Deliverables:**
- User-project mapping implementation
- Storage methods in auth_storage.py

**Tests:**
- Access grants persist correctly
- Revocation removes access
- Cascade deletes work properly

---

### 🔐 Task 2.3: Permission Validation Decorator
**Priority:** Medium | **Effort:** 3 hours | **Assignee:** Backend Dev

- [ ] Create `app/adapters/rest/auth_decorators.py`
- [ ] Implement `@require_permission(permission: str)` decorator
- [ ] Implement `@require_project_access(project_id_param: str)` decorator
- [ ] Implement `@require_role(role: str)` decorator
- [ ] Add helper for extracting project_id from request

**Deliverables:**
- Reusable auth decorators
- Clear error responses for permission failures

**Tests:**
- Decorators correctly validate permissions
- 403 returned when access denied
- Admin bypasses project checks

---

### 🔐 Task 2.4: Integrate Auth with VDB Endpoints
**Priority:** High | **Effort:** 4 hours | **Assignee:** Backend Dev

- [ ] Update `app/adapters/rest/vdb_routes.py`:
  - [ ] Add `@require_permission` to all endpoints
  - [ ] Add `@require_project_access` to project-specific endpoints
  - [ ] Extract `request.state.auth` in endpoint handlers
  - [ ] Filter results by user's accessible projects
  - [ ] Add `requested_by` to responses
- [ ] Update VDB use cases to accept user context
- [ ] Add owner_user_id when creating projects
- [ ] Add audit logging for all VDB operations

**Deliverables:**
- Fully protected VDB endpoints
- Project isolation enforced
- Audit trail for all operations

**Tests:**
- Users can only access own projects
- Admin can access all projects
- Creating project assigns ownership
- Unauthorized access returns 403

---

### ✅ Task 2.5: Integration Tests for Phase 2
**Priority:** High | **Effort:** 5 hours | **Assignee:** QA/Backend Dev

- [ ] Create `tests/integration/test_auth_api.py`:
  - [ ] Test bootstrap process
  - [ ] Test authentication flow
  - [ ] Test permission validation
  - [ ] Test project access control
- [ ] Update `tests/integration/test_vdb_api.py`:
  - [ ] Add multi-user scenarios
  - [ ] Test project isolation
  - [ ] Test admin access to all projects
  - [ ] Test access grant/revoke

**Deliverables:**
- Integration tests for auth + VDB
- Multi-tenant test scenarios

**Tests:**
- All integration tests pass
- Project isolation verified
- Permission system works end-to-end

---

## Phase 3: Admin UI Foundation (Week 4)

### 🎨 Task 3.1: HTMX Setup & Base Templates
**Priority:** High | **Effort:** 4 hours | **Assignee:** Frontend Dev

- [ ] Install dependencies: `jinja2`, `python-multipart`, `itsdangerous`
- [ ] Create `templates/admin/` directory structure
- [ ] Create base template `base.html`:
  - [ ] HTML boilerplate
  - [ ] HTMX 1.9+ CDN
  - [ ] TailwindCSS or custom CSS
  - [ ] Navigation header
  - [ ] Flash message area
  - [ ] Footer
- [ ] Create `templates/admin/components/`:
  - [ ] `table.html` - Reusable table component
  - [ ] `form.html` - Form component with CSRF
  - [ ] `modal.html` - Modal dialog
  - [ ] `toast.html` - Success/error notifications
- [ ] Set up Jinja2 template engine in FastAPI

**Deliverables:**
- Base templates structure
- Reusable UI components
- HTMX integrated

**Tests:**
- Templates render correctly
- HTMX loads and works
- Base layout displays properly

---

### 🎨 Task 3.2: Login & Session Management
**Priority:** High | **Effort:** 4 hours | **Assignee:** Backend/Frontend Dev

- [ ] Create `app/adapters/rest/admin_routes.py`
- [ ] Implement session management:
  - [ ] `create_session()` - Generate secure session token
  - [ ] `verify_session()` - Validate session cookie
  - [ ] `destroy_session()` - Logout
  - [ ] Session timeout (30 min default)
- [ ] Create `templates/admin/login.html`:
  - [ ] Username + API key form
  - [ ] Optional: Password field (for admin users)
  - [ ] "Remember me" checkbox
  - [ ] Error message display
- [ ] Implement login endpoint (`POST /admin/login`)
- [ ] Implement logout endpoint (`POST /admin/logout`)
- [ ] Add session middleware for admin routes
- [ ] Implement CSRF token generation

**Deliverables:**
- Login page with form
- Session management system
- Admin route protection

**Tests:**
- Login succeeds with valid credentials
- Invalid credentials show error
- Session expires after timeout
- CSRF tokens validated on POST

---

### 🎨 Task 3.3: Dashboard Page
**Priority:** Medium | **Effort:** 3 hours | **Assignee:** Frontend Dev

- [ ] Create `templates/admin/dashboard.html`
- [ ] Implement summary cards:
  - [ ] Total users count
  - [ ] Total projects count
  - [ ] Active API keys count
  - [ ] Recent activity (last 10 audit logs)
- [ ] Add quick action buttons:
  - [ ] "Create User"
  - [ ] "Create Project"
  - [ ] "Generate API Key"
- [ ] Implement dashboard endpoint (`GET /admin`)
- [ ] Add auto-refresh for activity feed (HTMX polling)

**Deliverables:**
- Dashboard page with stats
- Quick actions
- Recent activity feed

**Tests:**
- Dashboard loads correctly
- Stats are accurate
- Quick actions navigate properly

---

### 🎨 Task 3.4: Users List & Search
**Priority:** High | **Effort:** 4 hours | **Assignee:** Frontend/Backend Dev

- [ ] Create `templates/admin/users/list.html`
- [ ] Implement users table:
  - [ ] Columns: Username, Role, Email, Created, Active, Actions
  - [ ] Pagination (50 per page)
  - [ ] Sort by column headers
- [ ] Add filters:
  - [ ] Role dropdown (all, admin, monitor, etc.)
  - [ ] Active status checkbox
- [ ] Add search:
  - [ ] Username search with HTMX debounce (300ms)
  - [ ] Auto-complete suggestions
- [ ] Implement backend endpoints:
  - [ ] `GET /admin/users` - List with filters
  - [ ] `GET /admin/users/search` - Search endpoint
- [ ] Add row actions: Edit, Deactivate, View Keys

**Deliverables:**
- Users list page
- Search and filter functionality
- Pagination

**Tests:**
- Users list displays correctly
- Search works with debounce
- Filters apply correctly
- Pagination works

---

### 🎨 Task 3.5: User Create/Edit Forms
**Priority:** High | **Effort:** 4 hours | **Assignee:** Frontend/Backend Dev

- [ ] Create `templates/admin/users/form.html`
- [ ] Implement form fields:
  - [ ] Username (with availability check via HTMX)
  - [ ] Role dropdown
  - [ ] Email (optional)
  - [ ] Active checkbox
- [ ] Add inline validation:
  - [ ] Username uniqueness check (HTMX blur event)
  - [ ] Email format validation
  - [ ] Role selection required
- [ ] Implement backend endpoints:
  - [ ] `GET /admin/users/new` - Show create form
  - [ ] `POST /admin/users` - Create user
  - [ ] `GET /admin/users/{id}/edit` - Show edit form
  - [ ] `PUT /admin/users/{id}` - Update user
- [ ] Add success/error messages (toast notifications)

**Deliverables:**
- User create/edit forms
- Inline validation
- CRUD endpoints

**Tests:**
- Create user form works
- Edit updates user correctly
- Validation catches errors
- Duplicate username prevented

---

### 🎨 Task 3.6: Projects List & Management
**Priority:** High | **Effort:** 4 hours | **Assignee:** Frontend/Backend Dev

- [ ] Create `templates/admin/projects/list.html`
- [ ] Implement projects table:
  - [ ] Columns: Project ID, Name, Owner, Collections, Created, Actions
  - [ ] Search by project ID or name
  - [ ] Filter by owner
- [ ] Create `templates/admin/projects/form.html`:
  - [ ] Project ID (slug validation)
  - [ ] Name
  - [ ] Description
  - [ ] Owner dropdown (search users)
- [ ] Implement backend endpoints:
  - [ ] `GET /admin/projects` - List projects
  - [ ] `POST /admin/projects` - Create project
  - [ ] `GET /admin/projects/{id}/edit` - Edit form
  - [ ] `PUT /admin/projects/{id}` - Update project
- [ ] Add project access management button

**Deliverables:**
- Projects list page
- Project create/edit forms
- Project management endpoints

**Tests:**
- Projects list works
- Create project succeeds
- Edit updates correctly
- Search filters properly

---

## Phase 4: Admin UI Advanced (Week 5)

### 🎨 Task 4.1: API Key Management List
**Priority:** High | **Effort:** 4 hours | **Assignee:** Frontend/Backend Dev

- [ ] Create `templates/admin/api-keys/list.html`
- [ ] Implement keys table:
  - [ ] Columns: Key ID (masked), User, Label, Created, Last Used, Status, Actions
  - [ ] Mask format: `sk-admin-x7k2...w6y0` (show first/last 4 chars)
  - [ ] Status badges: Active (green), Revoked (red), Expired (gray)
- [ ] Add filters:
  - [ ] Status (active/revoked/expired)
  - [ ] User dropdown
  - [ ] Date range for last used
- [ ] Add sorting:
  - [ ] Last used (default)
  - [ ] Created date
  - [ ] User
- [ ] Implement endpoint: `GET /admin/api-keys`
- [ ] Add row actions: View Details, Revoke, Rotate

**Deliverables:**
- API keys list page
- Filtering and sorting
- Key masking for security

**Tests:**
- Keys list displays correctly
- Masking works
- Filters apply properly
- Status badges accurate

---

### 🎨 Task 4.2: API Key Creation Workflow
**Priority:** High | **Effort:** 5 hours | **Assignee:** Frontend/Backend Dev

- [ ] Create `templates/admin/api-keys/create.html`
- [ ] Implement creation form:
  - [ ] User selection (dropdown with search)
  - [ ] Label (required, e.g., "Production API")
  - [ ] Expiration date (optional date picker)
  - [ ] Advanced options (collapsible):
    - [ ] IP whitelist (comma-separated)
    - [ ] Rate limits (requests/min, requests/day)
- [ ] Create `templates/admin/api-keys/display.html`:
  - [ ] **Large, prominent key display**
  - [ ] ⚠️ Warning: "Save this key now. It won't be shown again."
  - [ ] Copy to clipboard button
  - [ ] Download as .txt button
  - [ ] "I've saved this key" checkbox + Continue button
- [ ] Implement endpoints:
  - [ ] `GET /admin/api-keys/new` - Show form
  - [ ] `POST /admin/api-keys` - Generate key
  - [ ] Return one-time plaintext key
- [ ] Add audit log entry for key creation

**Deliverables:**
- Key creation form
- One-time key display page
- Copy/download functionality

**Tests:**
- Key generation works
- Plaintext key shown once
- Copy button works
- Expiration set correctly

---

### 🎨 Task 4.3: API Key Revocation & Rotation
**Priority:** High | **Effort:** 3 hours | **Assignee:** Backend/Frontend Dev

- [ ] Create `templates/admin/api-keys/revoke-modal.html`:
  - [ ] Confirmation message
  - [ ] Reason textarea (optional)
  - [ ] "Revoke Immediately" button
- [ ] Create `templates/admin/api-keys/rotate-modal.html`:
  - [ ] Explanation of rotation process
  - [ ] Grace period selector (0h, 24h, 48h, 7d)
  - [ ] "Generate New Key" button
- [ ] Implement endpoints:
  - [ ] `POST /admin/api-keys/{id}/revoke` - Revoke key
  - [ ] `POST /admin/api-keys/{id}/rotate` - Rotate key
- [ ] Add HTMX confirmation dialogs
- [ ] Update row in table after action (HTMX swap)
- [ ] Add audit log entries

**Deliverables:**
- Revocation modal and endpoint
- Rotation modal and endpoint
- Grace period handling

**Tests:**
- Revocation works immediately
- Rotation creates new key
- Old key works during grace period
- After grace period, old key revoked

---

### 🎨 Task 4.4: API Key Details Page
**Priority:** Medium | **Effort:** 3 hours | **Assignee:** Frontend/Backend Dev

- [ ] Create `templates/admin/api-keys/details.html`
- [ ] Display key information:
  - [ ] Masked key ID
  - [ ] User and role
  - [ ] Label
  - [ ] Created/last used timestamps
  - [ ] Expiration (if set)
  - [ ] Status badge
  - [ ] Metadata (IP whitelist, rate limits)
- [ ] Add usage statistics:
  - [ ] Requests per day (last 30 days chart)
  - [ ] Total requests
  - [ ] Last 10 API calls (from audit logs)
- [ ] Add action buttons: Revoke, Rotate, Edit Label
- [ ] Implement endpoint: `GET /admin/api-keys/{id}`

**Deliverables:**
- Key details page
- Usage statistics
- Action buttons

**Tests:**
- Details page loads
- Statistics accurate
- Actions work from details page

---

### 🎨 Task 4.5: Audit Logs Viewer
**Priority:** Medium | **Effort:** 4 hours | **Assignee:** Frontend/Backend Dev

- [ ] Create `templates/admin/audit-logs/list.html`
- [ ] Implement logs table:
  - [ ] Columns: Timestamp, User, Action, Resource, Status, IP, Details
  - [ ] Color-coded status: Success (green), Failure (red), Denied (orange)
  - [ ] Expandable details row (JSON)
- [ ] Add filters:
  - [ ] Date range picker (last 24h, 7d, 30d, custom)
  - [ ] User dropdown
  - [ ] Action type multi-select
  - [ ] Status checkboxes
  - [ ] IP address search
- [ ] Add export functionality:
  - [ ] "Export as CSV" button
  - [ ] Generate CSV with filtered results
- [ ] Implement endpoints:
  - [ ] `GET /admin/audit-logs` - List with filters
  - [ ] `GET /admin/audit-logs/export` - CSV export
- [ ] Add pagination (100 per page)
- [ ] Optional: HTMX polling for real-time updates

**Deliverables:**
- Audit logs viewer
- Advanced filtering
- CSV export

**Tests:**
- Logs display correctly
- Filters work
- Export generates valid CSV
- Real-time updates work (if enabled)

---

### 🎨 Task 4.6: Project Access Management
**Priority:** Medium | **Effort:** 4 hours | **Assignee:** Frontend/Backend Dev

- [ ] Create `templates/admin/projects/access.html`
- [ ] Display current access list:
  - [ ] Table: User, Role, Granted By, Granted At, Actions
  - [ ] Owner highlighted (cannot be removed)
- [ ] Add grant access form:
  - [ ] User search (HTMX autocomplete)
  - [ ] Role dropdown (project-owner, project-viewer)
  - [ ] "Grant Access" button
- [ ] Add revoke access button for each user
- [ ] Implement endpoints:
  - [ ] `GET /admin/projects/{id}/access` - View access page
  - [ ] `POST /admin/projects/{id}/access` - Grant access
  - [ ] `DELETE /admin/projects/{id}/access/{user_id}` - Revoke access
- [ ] Add HTMX inline updates (no page reload)

**Deliverables:**
- Project access management page
- Grant/revoke functionality
- User search with autocomplete

**Tests:**
- Access list displays correctly
- Grant access works
- Revoke removes access
- Owner cannot be removed

---

## Phase 5: Security Hardening (Week 6)

### 🔐 Task 5.1: CSRF Protection
**Priority:** High | **Effort:** 3 hours | **Assignee:** Backend Dev

- [ ] Install `python-multipart` for form parsing
- [ ] Create CSRF token generation/validation:
  - [ ] Generate token per session
  - [ ] Store in secure cookie
  - [ ] Validate on all POST/PUT/DELETE
- [ ] Add CSRF middleware to admin routes
- [ ] Include CSRF token in all forms (hidden field)
- [ ] Add CSRF token to HTMX requests (meta tag)
- [ ] Return 403 on CSRF validation failure

**Deliverables:**
- CSRF protection middleware
- Token included in all forms
- Validation on state-changing requests

**Tests:**
- Valid CSRF token accepted
- Missing token returns 403
- Invalid token returns 403
- Token rotation works

---

### 🔐 Task 5.2: Rate Limiting
**Priority:** High | **Effort:** 4 hours | **Assignee:** Backend Dev

- [ ] Install `slowapi` for rate limiting
- [ ] Implement global rate limits:
  - [ ] 1000 requests/minute per IP
  - [ ] 10 login attempts/minute per IP
- [ ] Implement per-key rate limits:
  - [ ] Read from `api_keys.metadata.rate_limit`
  - [ ] Default: 100 req/min, 10,000 req/day
  - [ ] Store counters in-memory or Redis
- [ ] Add rate limit headers to responses:
  - [ ] `X-RateLimit-Limit`
  - [ ] `X-RateLimit-Remaining`
  - [ ] `X-RateLimit-Reset`
- [ ] Return 429 on limit exceeded
- [ ] Add rate limit exceeded to audit log

**Deliverables:**
- Rate limiting middleware
- Per-key and global limits
- Clear error responses

**Tests:**
- Rate limits enforced
- Headers included in responses
- 429 returned when exceeded
- Limits reset correctly

---

### 🔐 Task 5.3: IP Whitelisting
**Priority:** Medium | **Effort:** 3 hours | **Assignee:** Backend Dev

- [ ] Implement IP validation in auth middleware:
  - [ ] Read `api_keys.metadata.ip_whitelist`
  - [ ] Parse CIDR notation (e.g., 192.168.1.0/24)
  - [ ] Extract client IP from request
  - [ ] Handle proxy headers (X-Forwarded-For)
- [ ] Add IP check before key verification
- [ ] Return 403 if IP not in whitelist
- [ ] Add IP restriction violation to audit log
- [ ] Create admin UI for setting IP whitelist

**Deliverables:**
- IP whitelisting in auth middleware
- CIDR notation support
- Audit logging

**Tests:**
- Whitelisted IPs allowed
- Non-whitelisted IPs denied
- CIDR ranges work correctly
- Proxy headers handled

---

### 🔐 Task 5.4: SQLCipher Integration (Optional)
**Priority:** Low | **Effort:** 4 hours | **Assignee:** Backend Dev

- [ ] Add `pysqlcipher3` to optional dependencies
- [ ] Update database connection logic:
  - [ ] Check for `AUTH_DB_ENCRYPTION_KEY` env var
  - [ ] Use SQLCipher if key present
  - [ ] Use standard SQLite if key absent
- [ ] Add key derivation (PBKDF2, 256k iterations)
- [ ] Update documentation for encryption setup
- [ ] Add encryption status to health check

**Deliverables:**
- Optional SQLCipher support
- Key derivation
- Documentation

**Tests:**
- Encrypted DB works correctly
- Non-encrypted DB still works
- Key rotation supported

---

### 🔐 Task 5.5: Security Audit & Penetration Testing
**Priority:** High | **Effort:** 8 hours | **Assignee:** Security/QA

- [ ] Run automated security scanners:
  - [ ] OWASP ZAP
  - [ ] Bandit (Python security linter)
  - [ ] Safety (dependency vulnerability check)
- [ ] Manual penetration testing:
  - [ ] SQL injection attempts
  - [ ] XSS attempts
  - [ ] CSRF bypass attempts
  - [ ] Session hijacking attempts
  - [ ] Timing attack attempts (key verification)
  - [ ] Brute force login attempts
- [ ] Test OWASP Top 10:
  - [ ] Broken Access Control
  - [ ] Cryptographic Failures
  - [ ] Injection
  - [ ] Insecure Design
  - [ ] Security Misconfiguration
  - [ ] etc.
- [ ] Document findings and remediation
- [ ] Re-test after fixes

**Deliverables:**
- Security audit report
- Penetration test results
- Remediation plan
- Confirmation of fixes

**Tests:**
- All OWASP Top 10 mitigated
- No critical vulnerabilities
- Automated scans pass

---

## Phase 6: Polish & Production (Week 7-8)

### 📊 Task 6.1: Monitoring & Metrics
**Priority:** High | **Effort:** 5 hours | **Assignee:** DevOps/Backend

- [ ] Install `prometheus-client`
- [ ] Create metrics module `app/adapters/metrics.py`:
  - [ ] `auth_requests_total` counter
  - [ ] `auth_latency_seconds` histogram
  - [ ] `active_sessions_gauge`
  - [ ] `api_keys_total` gauge
  - [ ] `database_size_bytes` gauge
  - [ ] `backup_last_success_timestamp` gauge
- [ ] Add metrics collection in middleware
- [ ] Create `/metrics` endpoint (Prometheus format)
- [ ] Add Grafana dashboard JSON
- [ ] Set up alerts:
  - [ ] Failed auth > 100/min
  - [ ] Database size > 80% capacity
  - [ ] Backup failure

**Deliverables:**
- Prometheus metrics endpoint
- Grafana dashboard
- Alert rules

**Tests:**
- Metrics endpoint works
- Metrics accurate
- Dashboard displays correctly

---

### 📊 Task 6.2: Backup Automation
**Priority:** High | **Effort:** 4 hours | **Assignee:** DevOps

- [ ] Create backup script `scripts/backup-auth-db.sh`:
  - [ ] Copy auth.db to backup location
  - [ ] Compress with gzip
  - [ ] Timestamp filename
  - [ ] Upload to S3 (optional)
- [ ] Implement retention policy:
  - [ ] Keep last 24 hourly backups
  - [ ] Keep last 30 daily backups
  - [ ] Keep last 12 weekly backups
- [ ] Add cron job for scheduled backups
- [ ] Create restore script `scripts/restore-auth-db.sh`
- [ ] Add backup status to health check
- [ ] Test disaster recovery process

**Deliverables:**
- Backup scripts
- Cron configuration
- Restore procedure
- DR documentation

**Tests:**
- Backup creates valid file
- Restore works correctly
- Retention policy enforced
- S3 upload works (if configured)

---

### 📚 Task 6.3: API Documentation
**Priority:** High | **Effort:** 4 hours | **Assignee:** Tech Writer/Dev

- [ ] Update OpenAPI schema with auth:
  - [ ] Bearer token security scheme
  - [ ] All new admin endpoints
  - [ ] Request/response examples
  - [ ] Error responses
- [ ] Write authentication guide:
  - [ ] How to get API key
  - [ ] How to use Bearer token
  - [ ] Permission requirements per endpoint
- [ ] Create admin UI user guide:
  - [ ] Screenshots of all pages
  - [ ] Step-by-step workflows
  - [ ] Common tasks (create user, generate key, etc.)
- [ ] Write security best practices doc:
  - [ ] Key rotation schedule
  - [ ] IP whitelisting recommendations
  - [ ] Monitoring and alerts
- [ ] Add troubleshooting guide

**Deliverables:**
- Updated API documentation
- Admin UI user guide
- Security best practices
- Troubleshooting guide

**Tests:**
- Documentation complete and accurate
- Examples work correctly
- Screenshots up-to-date

---

### 🔧 Task 6.4: Performance Optimization
**Priority:** Medium | **Effort:** 5 hours | **Assignee:** Backend Dev

- [ ] Add database query optimization:
  - [ ] Verify all indexes exist
  - [ ] Add composite indexes for common queries
  - [ ] Use EXPLAIN QUERY PLAN
- [ ] Implement caching:
  - [ ] Cache user permissions (5 min TTL)
  - [ ] Cache project access lists (5 min TTL)
  - [ ] Use in-memory cache or Redis
- [ ] Add connection pooling (if needed)
- [ ] Optimize Argon2 parameters:
  - [ ] Balance security vs performance
  - [ ] Aim for ~50ms verification time
- [ ] Add async background tasks:
  - [ ] Update last_used_at async
  - [ ] Audit log writes async
- [ ] Run performance tests:
  - [ ] 1000+ concurrent requests
  - [ ] Measure auth latency
  - [ ] Identify bottlenecks

**Deliverables:**
- Optimized database queries
- Caching layer
- Performance test results
- Optimization report

**Tests:**
- Auth latency < 10ms (cached)
- Auth latency < 100ms (uncached)
- 1000+ concurrent users supported
- No memory leaks

---

### 🚀 Task 6.5: Deployment Configuration
**Priority:** High | **Effort:** 4 hours | **Assignee:** DevOps

- [ ] Update Dockerfile:
  - [ ] Add auth dependencies
  - [ ] Copy migration scripts
  - [ ] Set proper permissions on /data volume
- [ ] Create docker-compose.yml:
  - [ ] App service
  - [ ] Optional: Redis for caching
  - [ ] Volume mounts for data persistence
- [ ] Add Kubernetes manifests (if needed):
  - [ ] Deployment
  - [ ] Service
  - [ ] ConfigMap for env vars
  - [ ] Secret for encryption key
  - [ ] PersistentVolumeClaim for database
- [ ] Create deployment guide:
  - [ ] Environment variables
  - [ ] Volume requirements
  - [ ] Scaling considerations
  - [ ] Migration procedure
- [ ] Add health check probes

**Deliverables:**
- Updated Docker configuration
- Kubernetes manifests
- Deployment guide
- Production checklist

**Tests:**
- Docker build succeeds
- Docker container runs correctly
- K8s deployment works
- Health checks pass

---

### ✅ Task 6.6: Final Testing & QA
**Priority:** High | **Effort:** 8 hours | **Assignee:** QA Team

- [ ] Run full test suite:
  - [ ] Unit tests (90%+ coverage)
  - [ ] Integration tests
  - [ ] E2E tests (admin UI)
  - [ ] Security tests
  - [ ] Performance tests
- [ ] Manual QA testing:
  - [ ] Complete workflows
  - [ ] Edge cases
  - [ ] Error handling
  - [ ] UI/UX validation
- [ ] Cross-browser testing (admin UI):
  - [ ] Chrome, Firefox, Safari
  - [ ] Mobile browsers
- [ ] Accessibility testing:
  - [ ] Screen reader compatibility
  - [ ] Keyboard navigation
  - [ ] WCAG 2.1 AA compliance
- [ ] Load testing:
  - [ ] Sustained 1000 req/sec
  - [ ] Peak 5000 req/sec
- [ ] Generate test report

**Deliverables:**
- Complete test suite execution
- QA test report
- Bug list (if any)
- Sign-off for production

**Tests:**
- All tests passing
- No critical bugs
- Performance targets met
- Security requirements met

---

### 📚 Task 6.7: Release Preparation
**Priority:** High | **Effort:** 3 hours | **Assignee:** Tech Lead

- [ ] Update CHANGELOG.md:
  - [ ] New features summary
  - [ ] Breaking changes (if any)
  - [ ] Migration guide
- [ ] Update README.md:
  - [ ] New sections for auth
  - [ ] Updated installation instructions
  - [ ] Admin UI access info
- [ ] Create migration guide for existing users:
  - [ ] How to upgrade
  - [ ] Database migration steps
  - [ ] API changes (backward compatible)
- [ ] Tag release version (e.g., v2.0.0)
- [ ] Generate release notes
- [ ] Prepare demo video/screenshots
- [ ] Announce release

**Deliverables:**
- Updated documentation
- Release notes
- Migration guide
- Release announcement

**Tests:**
- Documentation complete
- Migration guide tested
- Release tagged

---

## Summary

**Total Tasks:** 62  
**Total Estimated Hours:** 210 hours (~6 weeks with 1-2 developers)  

**Critical Path:**
1. Database & Auth (Phase 1) → Foundation
2. Project Management (Phase 2) → Multi-tenancy
3. Admin UI (Phase 3-4) → Usability
4. Security (Phase 5) → Production-ready
5. Polish (Phase 6) → Release

**Team Allocation:**
- Backend Dev: ~120 hours
- Frontend Dev: ~50 hours
- DevOps: ~20 hours
- QA/Security: ~20 hours

**Risk Factors:**
- SQLCipher integration complexity (optional)
- Performance tuning may take longer
- Security audit findings may require rework
- Admin UI polish can expand scope

**Success Criteria:**
- ✅ All tests passing (90%+ coverage)
- ✅ Security audit passed
- ✅ Performance targets met
- ✅ Documentation complete
- ✅ Production deployment successful
