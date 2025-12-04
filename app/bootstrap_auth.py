"""Bootstrap authentication database from environment variables.

Reads API_KEYS from environment and creates initial users and API keys in the database.
This process is idempotent - it only runs if the database doesn't exist.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Tuple, List

from app import config
from app.domain.auth import api_key_manager, infer_role_from_account_name
from app.adapters.infra.auth_storage import (
    AuthDatabase,
    UserStorage,
    APIKeyStorage,
    AuditLogStorage,
)

logger = logging.getLogger(__name__)


def parse_api_keys_from_env() -> List[Tuple[str, str]]:
    """Parse API_KEYS environment variable.
    
    Format: account_name:api_key,account_name2:api_key2
    
    Returns:
        List of (account_name, api_key) tuples
    """
    api_keys_env = os.getenv("API_KEYS", "")
    if not api_keys_env:
        return []
    
    result = []
    for pair in api_keys_env.split(","):
        pair = pair.strip()
        if ":" in pair:
            account, key = pair.split(":", 1)
            result.append((account.strip(), key.strip()))
    
    return result


def should_bootstrap(db_path: str) -> bool:
    """Check if database needs bootstrapping.
    
    Args:
        db_path: Path to database file
        
    Returns:
        True if database doesn't exist or is empty
    """
    db_file = Path(db_path)
    
    # Database doesn't exist
    if not db_file.exists():
        return True
    
    # Database exists but is empty (size = 0)
    if db_file.stat().st_size == 0:
        return True
    
    return False


def ensure_data_directory(db_path: str):
    """Ensure the data directory exists with proper permissions.
    
    Args:
        db_path: Path to database file
    """
    db_file = Path(db_path)
    data_dir = db_file.parent
    
    # Create directory if it doesn't exist
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Set directory permissions (owner read/write/execute)
    try:
        os.chmod(data_dir, 0o700)
    except Exception as e:
        logger.warning(f"Could not set directory permissions: {e}")


def set_database_permissions(db_path: str):
    """Set secure permissions on database file.
    
    Args:
        db_path: Path to database file
    """
    try:
        # Set file permissions to 600 (owner read/write only)
        os.chmod(db_path, 0o600)
        logger.info(f"Set database permissions to 600 (owner read/write only)")
    except Exception as e:
        logger.warning(f"Could not set database file permissions: {e}")


def bootstrap_auth_database(db_path: str = None) -> bool:
    """Bootstrap authentication database from environment.
    
    This function:
    1. Checks if database needs bootstrapping
    2. Creates database and tables
    3. Parses API_KEYS environment variable
    4. Creates users and hashed API keys
    5. Logs the bootstrap process
    
    Args:
        db_path: Path to database file (uses config if not provided)
        
    Returns:
        True if bootstrap was performed, False if skipped
    """
    if db_path is None:
        db_path = config.AUTH_DB_PATH
    
    # Check if bootstrap is needed
    if not should_bootstrap(db_path):
        logger.info(f"Auth database already exists at {db_path}, skipping bootstrap")
        return False
    
    logger.info("=" * 60)
    logger.info("Starting authentication database bootstrap...")
    logger.info("=" * 60)
    
    # Ensure data directory exists
    ensure_data_directory(db_path)
    
    # Initialize database
    logger.info(f"Creating database at: {db_path}")
    auth_db = AuthDatabase(db_path)
    auth_db.create_tables()
    logger.info("✓ Database tables created successfully")
    
    # Set secure permissions
    set_database_permissions(db_path)
    
    # Initialize storage layers
    user_storage = UserStorage(auth_db)
    key_storage = APIKeyStorage(auth_db)
    audit_storage = AuditLogStorage(auth_db)
    
    # Parse API keys from environment
    api_keys_list = parse_api_keys_from_env()
    
    if not api_keys_list:
        logger.warning("No API_KEYS found in environment - creating empty database")
        logger.warning("Set API_KEYS environment variable to bootstrap users")
        logger.warning("Example: API_KEYS=admin:sk-admin-abc123,monitor:sk-monitor-def456")
        return True
    
    logger.info(f"Found {len(api_keys_list)} API keys in environment")
    
    # Create users and keys
    created_users = []
    for account_name, plaintext_key in api_keys_list:
        try:
            # Infer role from account name
            role = infer_role_from_account_name(account_name)
            
            logger.info(f"Creating user: {account_name} (role: {role})")
            
            # Create user
            user = user_storage.create_user(
                username=account_name,
                role=role,
                active=True,
                metadata={"source": "bootstrap", "created_from_env": True}
            )
            
            # Hash the API key
            key_hash = api_key_manager.hash_key(plaintext_key)
            
            # Create API key record
            api_key = key_storage.create_api_key(
                user_id=user.id,
                key_id=plaintext_key,  # Store full key as identifier
                key_hash=key_hash,
                label=f"Bootstrap Key - {account_name}",
                metadata={
                    "source": "bootstrap",
                    "created_from_env": True,
                }
            )
            
            # Create audit log
            audit_storage.create_log(
                action="bootstrap_user_created",
                user_id=user.id,
                resource_type="user",
                resource_id=str(user.id),
                status="success",
                details={
                    "username": account_name,
                    "role": role,
                    "source": "environment",
                }
            )
            
            created_users.append((user.username, role))
            logger.info(f"✓ Created user '{account_name}' with API key")
            
        except Exception as e:
            logger.error(f"✗ Failed to create user '{account_name}': {e}")
            continue
    
    # Log summary
    logger.info("=" * 60)
    logger.info(f"Bootstrap complete: {len(created_users)} users created")
    for username, role in created_users:
        logger.info(f"  - {username} ({role})")
    logger.info("=" * 60)
    
    # Close database connection
    auth_db.close()
    
    return True


def get_bootstrap_status(db_path: str = None) -> Dict[str, any]:
    """Get bootstrap status information.
    
    Args:
        db_path: Path to database file (uses config if not provided)
        
    Returns:
        Dictionary with bootstrap status info
    """
    if db_path is None:
        db_path = config.AUTH_DB_PATH
    
    db_file = Path(db_path)
    
    status = {
        "database_exists": db_file.exists(),
        "database_path": str(db_file.absolute()),
        "needs_bootstrap": should_bootstrap(db_path),
    }
    
    if db_file.exists():
        status["database_size_bytes"] = db_file.stat().st_size
        
        # Try to count users
        try:
            auth_db = AuthDatabase(db_path)
            user_storage = UserStorage(auth_db)
            users = user_storage.list_users(limit=1000)
            status["users_count"] = len(users)
            status["user_roles"] = {}
            for user in users:
                status["user_roles"][user.role] = status["user_roles"].get(user.role, 0) + 1
            auth_db.close()
        except Exception as e:
            status["error"] = str(e)
    
    return status


if __name__ == "__main__":
    """Run bootstrap as standalone script."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Show current status
    status = get_bootstrap_status()
    print("\nCurrent Bootstrap Status:")
    print(f"  Database exists: {status['database_exists']}")
    print(f"  Database path: {status['database_path']}")
    print(f"  Needs bootstrap: {status['needs_bootstrap']}")
    
    if status['database_exists']:
        print(f"  Database size: {status.get('database_size_bytes', 0)} bytes")
        print(f"  Users count: {status.get('users_count', 0)}")
        if status.get('user_roles'):
            print("  User roles:")
            for role, count in status['user_roles'].items():
                print(f"    - {role}: {count}")
    
    # Run bootstrap
    print()
    bootstrap_auth_database()
