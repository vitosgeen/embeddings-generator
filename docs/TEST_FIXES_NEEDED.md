# Test Fixes for Phase 3 (Database-Backed Authentication)

## Summary

After implementing Phase 3 (project-level access control with database-backed authentication), the test suite needs to be updated from the old environment-variable based auth system to the new database system.

## Changes Made

### 1. Updated `tests/conftest.py`

Added comprehensive test fixtures:

- `test_auth_db`: Creates a temporary SQLite database with test users and API keys
  - Admin user: `test_admin` with generated admin API key
  - Service user: `test_service` with generated service-app API key  
  - Monitor user: `test_monitor` with generated monitor API key

- `admin_auth_headers`: Authorization header with admin API key
- `service_auth_headers`: Authorization header with service-app API key
- `monitor_auth_headers`: Authorization header with monitor API key

- `setup_test_auth`: Auto-use fixture that injects test database into auth middleware

### 2. Updated Auth Middleware (`app/adapters/rest/auth_middleware.py`)

Added test dependency injection functions:

- `set_test_auth_storage()`: Inject test database storage
- `reset_auth_storage()`: Clean up after tests

### 3. Updated Tests

#### Fixed in `tests/test_auth.py`:
✅ `test_embed_endpoint_requires_auth` - Changed expected code from 403 to 401
✅ `test_embed_endpoint_invalid_api_key` - Updated assertion
✅ `test_embed_endpoint_valid_api_key` - Now uses `admin_auth_headers` fixture
✅ `test_multiple_api_keys` - Now uses `admin_auth_headers` and `service_auth_headers`
✅ `test_batch_embedding_authentication` - Now uses `service_auth_headers`

#### Updated in `tests/integration/test_vdb_api.py`:
✅ Removed old environment variable setup
✅ Added `vdb_auth_headers` fixture that creates test projects with access grants
✅ Added backward-compatible `api_key` and `auth_headers` aliases

## Test Results

Current Status (after fixes):
- ✅ 36/40 tests passing in auth_domain tests
- ✅ 4/8 tests passing in test_auth.py  
- ❌ Still failing: Tests using the old client fixture without proper auth setup

## Remaining Work

### High Priority (Breaks Many Tests)

1. **Fix remaining `tests/test_auth.py` failures**:
   - `test_malformed_authorization_header` - Remove @patch decorators, use fixtures
   
2. **Fix `tests/integration/test_rest_api.py` (15 failures)**:
   - All tests use hardcoded `Authorization: Bearer test-key-123`
   - Need to update to use `admin_auth_headers` or `service_auth_headers` fixtures
   - Example pattern:
     ```python
     # OLD:
     def test_embed_single_text(self, client):
         response = client.post("/embed", 
             headers={"Authorization": "Bearer test-key-123"},
             json={"text": "test"})
     
     # NEW:
     def test_embed_single_text(self, client, service_auth_headers):
         response = client.post("/embed",
             headers=service_auth_headers,
             json={"text": "test"})
     ```

3. **Fix `tests/integration/test_vdb_api.py` (18 failures)**:
   - Tests need project access grants in auth database
   - Current `vdb_auth_headers` fixture creates projects but may need refinement
   - Each test project must exist in auth DB before VDB operations

4. **Fix `tests/unit/test_auth_storage.py` (1 failure)**:
   - `test_create_user` - Check why it's failing with new database schema

### Medium Priority

5. **Add Tests for New Features**:
   - Project access control (grant/revoke)
   - Project filtering by user access
   - VDB endpoint project access checks
   - Admin UI project management

6. **Add Integration Tests**:
   - End-to-end user → project → VDB access flow
   - Multi-tenant isolation (user A can't see user B's projects)
   - Role-based permissions (project-owner vs project-viewer)

### Low Priority

7. **Update Test Documentation**:
   - Document new test fixture usage
   - Add examples of testing with different roles
   - Explain project access test patterns

## Quick Fix Script

For bulk fixing REST API tests, use this pattern:

```python
# In tests/integration/test_rest_api.py

# At the top, add to class:
@pytest.fixture(autouse=True)
def setup_auth(self, test_auth_db):
    """Setup auth for all REST API tests."""
    pass

# Then update each test method signature:
async def test_embed_single_text(self, client, service_auth_headers):
    # Old: headers={"Authorization": "Bearer test-key-123"}
    # New: headers=service_auth_headers
```

## Testing Strategy

1. **Run tests by category**:
   ```bash
   # Unit tests (should all pass)
   pytest tests/unit/ -v
   
   # Auth tests (4/8 passing)
   pytest tests/test_auth.py -v
   
   # Integration tests (need fixes)
   pytest tests/integration/ -v
   ```

2. **Fix in order**:
   - ✅ Unit tests (mostly done)
   - 🔄 Auth tests (in progress)
   - ❌ REST API integration tests (needs bulk fix)
   - ❌ VDB API integration tests (needs project setup)

3. **Verify server works**:
   ```bash
   # Manual test with real keys
   curl -H "Authorization: Bearer sk-admin-m1YHp13elEvafGYLT27H0gmD" \
        http://localhost:8000/vdb/projects
   ```

## Expected Timeline

- **Quick win**: Fix REST API tests (2-3 bulk replacements) - 15 mins
- **Medium effort**: Fix VDB API tests (project access setup) - 30 mins
- **Polish**: Add new feature tests - 1 hour

Total estimated time to green test suite: **2 hours**

## Notes

- All new tests should use fixtures from `conftest.py`
- Never hardcode API keys in tests
- Always use `test_auth_db` fixture for database-backed tests
- Project access must be granted in auth DB before VDB operations
- Admin role bypasses project access checks
