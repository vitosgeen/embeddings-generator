# Admin UI Quick Start

## Access the Admin UI

**URL**: http://localhost:8000/admin/

**Authentication Required**: Add this header to all requests:
```
Authorization: Bearer sk-admin-XXXXXXXXXXXXXXXXXXXX
```

## Browser Access

Since the UI requires Bearer token authentication, you need to configure your browser:

### Option 1: ModHeader Extension (Recommended)
1. Install [ModHeader](https://modheader.com/) for Chrome/Firefox
2. Add request header:
   - Name: `Authorization`
   - Value: `Bearer sk-admin-m1YHp13elEvafGYLT27H0gmD` (use your actual key)
3. Navigate to http://localhost:8000/admin/

### Option 2: Requestly Extension
1. Install [Requestly](https://requestly.io/)
2. Create rule to inject Authorization header
3. Navigate to http://localhost:8000/admin/

### Option 3: curl/httpie
```bash
# Dashboard
curl -H "Authorization: Bearer $ADMIN_KEY" http://localhost:8000/admin/

# Users
curl -H "Authorization: Bearer $ADMIN_KEY" http://localhost:8000/admin/users

# Keys
curl -H "Authorization: Bearer $ADMIN_KEY" http://localhost:8000/admin/keys

# Logs
curl -H "Authorization: Bearer $ADMIN_KEY" http://localhost:8000/admin/logs
```

## Features

### Dashboard (`/admin/`)
- Total/active users and API keys
- Recent activity feed

### Users (`/admin/users`)
- List all users with role badges
- Create new users (username, email, role)
- Deactivate/delete users
- Filter by role

### API Keys (`/admin/keys`)
- List all API keys with status
- Generate new keys with optional expiration
- Revoke/delete keys
- See last used timestamps

### Audit Logs (`/admin/logs`)
- View all operations
- Filter by action type
- See user, status, details

## Quick Actions

### Create User
1. Go to `/admin/users`
2. Click "New User" button
3. Fill form: username, email (optional), role
4. Click "Create"

### Generate API Key
1. Go to `/admin/keys`
2. Click "New API Key" button
3. Select user, enter label, choose expiration
4. Click "Generate Key"
5. **Copy the key immediately** (shown only once!)

### View Logs
1. Go to `/admin/logs`
2. Optionally filter by action type
3. See all operations with details

## Demo Script

Run the automated demo:
```bash
export ADMIN_KEY="sk-admin-m1YHp13elEvafGYLT27H0gmD"
./scripts/demo_admin_ui.sh
```

## Permissions

| Route | Required Permission |
|-------|---------------------|
| Dashboard | `admin:users` |
| Users | `admin:users` |
| Keys | `admin:api_keys` |
| Logs | `read:audit-logs` |

## Security Notes

- API keys are only shown in plaintext at creation time
- All operations are logged to audit trail
- Revoked keys cannot be reactivated
- Delete operations are permanent (use deactivate for soft delete)

## Troubleshooting

### "Unauthorized" error
- Check your API key is correct
- Verify Authorization header is being sent
- Ensure key hasn't been revoked

### "Forbidden" error
- Your user doesn't have required permissions
- Admin role needed for most operations
- Monitor role can only view logs

### Templates not rendering
- Check server logs: `tail -f /tmp/server.log`
- Verify templates directory exists
- Restart server

## Tech Stack

- **Backend**: FastAPI + SQLAlchemy
- **Frontend**: HTMX + Tailwind CSS
- **Database**: SQLite
- **Auth**: Bearer token (API key)

## Documentation

- Full guide: `docs/PHASE2_ADMIN_UI.md`
- Summary: `docs/PHASE2_SUMMARY.md`
- Architecture: See inline comments in `app/adapters/rest/admin_routes.py`

## Next Steps

After Phase 2, consider:
- Add login page for cookie-based sessions
- Implement project-level access control
- Add pagination for large lists
- Export functionality (CSV, JSON)
- Rate limiting dashboard
