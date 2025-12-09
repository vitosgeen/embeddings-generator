"""Authentication domain logic: API key generation, hashing, and verification."""

import re
import secrets
import string
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError


# ============================================================================
# Constants
# ============================================================================

API_KEY_PREFIX = "sk"
API_KEY_RANDOM_LENGTH = 24
# Accept multiple formats for backwards compatibility:
# - Standard: sk-{role}-{random24}  (e.g., sk-admin-m1YHp13elEvafGYLT27H0gmD)
# - Legacy: sk-{role}-{random}      (e.g., sk-admin-test123456789012)
# - Underscore: sk_{any}_{random}   (e.g., sk_test_batch_41c51db7c42f89a7321f74cc)
API_KEY_PATTERN = re.compile(r"^sk[-_][a-zA-Z0-9_-]{3,50}$")

# Argon2 parameters (balance security vs performance)
ARGON2_TIME_COST = 2  # iterations
ARGON2_MEMORY_COST = 65536  # 64 MB
ARGON2_PARALLELISM = 4  # threads


# ============================================================================
# Enums
# ============================================================================

class Role(str, Enum):
    """User roles with different permission levels."""
    
    ADMIN = "admin"
    MONITOR = "monitor"
    SERVICE_APP = "service-app"
    PROJECT_OWNER = "project-owner"
    
    @classmethod
    def from_string(cls, role_str: str) -> "Role":
        """Convert string to Role enum."""
        role_map = {
            "admin": cls.ADMIN,
            "monitor": cls.MONITOR,
            "service-app": cls.SERVICE_APP,
            "service_app": cls.SERVICE_APP,  # Support both formats
            "project-owner": cls.PROJECT_OWNER,
            "project_owner": cls.PROJECT_OWNER,  # Support both formats
        }
        return role_map.get(role_str.lower(), cls.PROJECT_OWNER)
    
    def get_permissions(self) -> List[str]:
        """Get permissions for this role."""
        permissions_map = {
            Role.ADMIN: ["all"],
            Role.MONITOR: [
                "read:health",
                "read:metrics",
                "read:audit-logs",
                "read:projects",
                "read:users",
            ],
            Role.SERVICE_APP: [
                "read:projects",
                "write:projects",  # Allow service apps to create projects
                "read:collections",
                "write:collections",
                "write:vectors",
                "delete:vectors",
                "search:vectors",
            ],
            Role.PROJECT_OWNER: [
                "write:projects",  # Allow project owners to create their own projects
                "read:project",
                "read:collections",
                "write:collections",
                "write:vectors",
                "delete:vectors",
                "search:vectors",
            ],
        }
        return permissions_map.get(self, [])


# ============================================================================
# API Key Management
# ============================================================================

class APIKeyManager:
    """Handles API key generation, hashing, and verification."""
    
    def __init__(self):
        """Initialize with Argon2 hasher."""
        self.hasher = PasswordHasher(
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
        )
    
    def generate_key(self, role: str) -> str:
        """Generate a new API key.
        
        Format: sk-{role}-{24_random_chars}
        
        Args:
            role: User role (used in key format)
            
        Returns:
            Generated API key string
            
        Example:
            sk-admin-x7k2p9m4n8q1r5t3w6y0
        """
        # Normalize role for key format (remove special chars, lowercase)
        role_slug = role.lower().replace("_", "").replace("-", "")[:15]
        
        # Generate cryptographically secure random string
        alphabet = string.ascii_letters + string.digits
        random_part = ''.join(secrets.choice(alphabet) for _ in range(API_KEY_RANDOM_LENGTH))
        
        return f"{API_KEY_PREFIX}-{role_slug}-{random_part}"
    
    def hash_key(self, api_key: str) -> str:
        """Hash an API key using Argon2.
        
        Args:
            api_key: Plaintext API key
            
        Returns:
            Argon2 hash string
        """
        return self.hasher.hash(api_key)
    
    def verify_key(self, api_key: str, key_hash: str) -> bool:
        """Verify an API key against its hash.
        
        Uses constant-time comparison to prevent timing attacks.
        
        Args:
            api_key: Plaintext API key to verify
            key_hash: Stored hash to compare against
            
        Returns:
            True if key matches hash, False otherwise
        """
        try:
            self.hasher.verify(key_hash, api_key)
            return True
        except (VerifyMismatchError, InvalidHashError):
            return False
    
    def validate_format(self, api_key: str) -> bool:
        """Validate API key format.
        
        Args:
            api_key: API key string to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        return bool(API_KEY_PATTERN.match(api_key))
    
    def extract_role_from_key(self, api_key: str) -> Optional[str]:
        """Extract role hint from key format.
        
        Note: This is just a hint from the key format, not authoritative.
        Always use the role from the database.
        
        Args:
            api_key: API key string
            
        Returns:
            Role string or None if format is invalid
        """
        if not self.validate_format(api_key):
            return None
        
        parts = api_key.split("-")
        if len(parts) >= 2:
            role_part = parts[1]
            # Map common role slugs back to full role names
            role_map = {
                "admin": "admin",
                "monitor": "monitor",
                "service": "service-app",
                "serviceapp": "service-app",
                "project": "project-owner",
                "projectowner": "project-owner",
            }
            return role_map.get(role_part, "project-owner")
        
        return None


# ============================================================================
# Domain Models
# ============================================================================

@dataclass
class AuthContext:
    """Authentication context for a request.
    
    Contains user identity, permissions, and accessible projects.
    Injected into request.state by auth middleware.
    """
    
    user_id: int
    username: str
    role: str
    permissions: List[str]
    accessible_projects: List[str]  # project_ids user can access
    api_key_id: str  # For audit logging
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission.
        
        Args:
            permission: Permission string (e.g., 'write:collections')
            
        Returns:
            True if user has permission, False otherwise
        """
        # Admin wildcard permission
        if "all" in self.permissions:
            return True
        
        return permission in self.permissions
    
    def can_access_project(self, project_id: str) -> bool:
        """Check if user can access a specific project.
        
        Args:
            project_id: Project ID to check
            
        Returns:
            True if user can access project, False otherwise
        """
        # Admin can access all projects
        if self.role == "admin":
            return True
        
        return project_id in self.accessible_projects
    
    def require_permission(self, permission: str) -> None:
        """Require a specific permission (raises if not present).
        
        Args:
            permission: Required permission
            
        Raises:
            PermissionError: If permission is not granted
        """
        if not self.has_permission(permission):
            raise PermissionError(
                f"Permission '{permission}' required. User has: {self.permissions}"
            )
    
    def require_project_access(self, project_id: str) -> None:
        """Require access to a specific project (raises if not allowed).
        
        Args:
            project_id: Required project ID
            
        Raises:
            PermissionError: If project access is not granted
        """
        if not self.can_access_project(project_id):
            raise PermissionError(
                f"Access to project '{project_id}' denied. "
                f"Accessible projects: {self.accessible_projects}"
            )


@dataclass
class UserIdentity:
    """User identity and role information."""
    
    id: int
    username: str
    role: Role
    email: Optional[str]
    active: bool
    
    @property
    def permissions(self) -> List[str]:
        """Get permissions for this user's role."""
        return self.role.get_permissions()


# ============================================================================
# Utility Functions
# ============================================================================

def infer_role_from_account_name(account_name: str) -> str:
    """Infer role from account name used in bootstrap.
    
    Used when parsing API_KEYS environment variable.
    
    Args:
        account_name: Account name from environment (e.g., 'admin', 'monitor')
        
    Returns:
        Role string
    """
    name_lower = account_name.lower()
    
    if "admin" in name_lower:
        return Role.ADMIN.value
    elif "monitor" in name_lower or "monitoring" in name_lower:
        return Role.MONITOR.value
    elif "service" in name_lower or "app" in name_lower:
        return Role.SERVICE_APP.value
    else:
        return Role.PROJECT_OWNER.value


def mask_api_key(api_key: str, show_chars: int = 4) -> str:
    """Mask an API key for display purposes.
    
    Shows first and last `show_chars` characters, masks the rest.
    
    Args:
        api_key: Full API key
        show_chars: Number of characters to show at start/end
        
    Returns:
        Masked key (e.g., 'sk-admin-x7k2...w6y0')
    """
    if len(api_key) <= show_chars * 2:
        return api_key
    
    prefix = api_key[:show_chars]
    suffix = api_key[-show_chars:]
    
    return f"{prefix}...{suffix}"


# ============================================================================
# Global Instance
# ============================================================================

# Singleton instance for convenience
api_key_manager = APIKeyManager()
