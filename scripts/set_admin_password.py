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
    
    print("\n✅ Password updated in .env file successfully!")
    print(f"📝 Updated file: {env_file}")
    print("\n⚠️  Next steps:")
    print("1. Update app/adapters/rest/admin_routes.py to use config.ADMIN_PASSWORD")
    print("2. Restart the service: make stop && make run")
    print("3. Never commit .env file to git")
    print("\nSee ADMIN_PASSWORD.md for detailed instructions.")

if __name__ == "__main__":
    main()
