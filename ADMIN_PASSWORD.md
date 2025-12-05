# Admin Password Management

## ✅ Current Implementation (Environment Variable)

The admin password is now **securely configured via environment variable**:

- **Default Password**: `admin123`
- **Configuration**: Set via `ADMIN_PASSWORD` in `.env` file
- **Security**: Password is not hardcoded, kept in `.env` (git-ignored)

### How It Works

1. Password is read from `ADMIN_PASSWORD` environment variable
2. Falls back to default `admin123` if not set
3. Used for authentication at `/admin/login`

## 🔐 How to Change the Admin Password

### Method 1: Edit .env File (Recommended)

**Step 1**: Open or create `.env` file:
```bash
nano .env
# or
code .env
```

**Step 2**: Add or update the ADMIN_PASSWORD line:
```bash
# Change this to your secure password
ADMIN_PASSWORD=YourSecurePassword123!
```

**Step 3**: Restart the service:
```bash
make stop
make run
```

That's it! The new password is now active.

### Method 2: Use the Password Setup Script

**Run the interactive script**:
```bash
python3 scripts/set_admin_password.py
```

The script will:
- Prompt for new password (hidden input)
- Confirm the password
- Update `.env` file automatically
- Show next steps

**Then restart**:
```bash
make stop
make run
```

### Method 3: Environment Variable (Docker/Production)

For containerized or production deployments:

```bash
# Set environment variable directly
export ADMIN_PASSWORD="your-secure-password"

# Or in docker-compose.yml:
environment:
  - ADMIN_PASSWORD=your-secure-password

# Or in Kubernetes secret:
kubectl create secret generic admin-creds \
  --from-literal=ADMIN_PASSWORD='your-secure-password'
```

## Security Best Practices

### ⚠️ Important Notes:

1. **Never commit passwords to git**
   - Add `.env` to `.gitignore` (already done)
   - Use environment variables for passwords

2. **Use strong passwords**
   - Minimum 12 characters
   - Mix of uppercase, lowercase, numbers, and symbols
   - Example: `Adm1n!Secur3@2025`

3. **For production**
   - Implement proper password hashing (argon2, bcrypt)
   - Add password reset functionality
   - Enable 2FA/MFA
   - Use HTTPS/TLS only
   - Implement rate limiting on login attempts

## Quick Reference

### Current Default Credentials
```
Username: admin
Password: admin123
URL: http://localhost:8000/admin/login
```

### After Changing Password
1. Stop the service: `make stop`
2. Make your changes
3. Start the service: `make run`
4. Clear browser cookies if needed
5. Login with new credentials

## Script: Set Admin Password Tool

Create `scripts/set_admin_password.py`:

```python
#!/usr/bin/env python3
"""Set admin password in .env file."""

import os
import getpass
from pathlib import Path

def main():
    print("🔐 Admin Password Configuration Tool")
    print("=" * 50)
    
    # Get current directory
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    
    # Get new password
    print("\nEnter new admin password:")
    password = getpass.getpass("Password: ")
    password_confirm = getpass.getpass("Confirm password: ")
    
    if password != password_confirm:
        print("❌ Passwords don't match!")
        return
    
    if len(password) < 8:
        print("⚠️  Warning: Password should be at least 8 characters")
        confirm = input("Continue anyway? (y/n): ")
        if confirm.lower() != 'y':
            return
    
    # Read existing .env
    env_content = ""
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.read()
    
    # Update or add ADMIN_PASSWORD
    if "ADMIN_PASSWORD=" in env_content:
        # Replace existing
        lines = env_content.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith("ADMIN_PASSWORD="):
                new_lines.append(f"ADMIN_PASSWORD={password}")
            else:
                new_lines.append(line)
        env_content = '\n'.join(new_lines)
    else:
        # Add new
        env_content += f"\n\n# Admin Authentication\nADMIN_PASSWORD={password}\n"
    
    # Write back
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print("\n✅ Password updated successfully!")
    print(f"📝 Updated file: {env_file}")
    print("\n⚠️  Remember to:")
    print("1. Restart the service: make stop && make run")
    print("2. Update admin_routes.py to use config.ADMIN_PASSWORD")
    print("3. Never commit .env file to git")

if __name__ == "__main__":
    main()
```

Make it executable:
```bash
chmod +x scripts/set_admin_password.py
```

Run it:
```bash
python3 scripts/set_admin_password.py
```

## Troubleshooting

### Can't login after changing password
1. Check if you updated the correct file
2. Verify the service was restarted: `make stop && make run`
3. Clear browser cookies: Go to `/admin/logout`
4. Check logs for error messages

### Forgot the password
1. Edit `app/adapters/rest/admin_routes.py`
2. Temporarily change back to `"admin123"`
3. Restart and login
4. Set a new password

### Service won't start after changes
1. Check for syntax errors: `python3 -m py_compile app/adapters/rest/admin_routes.py`
2. Revert changes if needed
3. Check logs in terminal output

## Future Improvements

Consider implementing:
- [ ] Password hashing with argon2/bcrypt
- [ ] Password reset via email
- [ ] Multi-factor authentication (2FA/MFA)
- [ ] Session management with proper tokens
- [ ] Password complexity requirements
- [ ] Login attempt rate limiting
- [ ] Account lockout after failed attempts
- [ ] Password expiration policy
- [ ] Audit logging for authentication events
