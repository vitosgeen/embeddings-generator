"""Authentication module for API key validation."""
from typing import Optional

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app import config

# Authentication constants
AUTH_SCHEME = "Bearer"
ERROR_INVALID_API_KEY = "Invalid API key"
HEADER_WWW_AUTHENTICATE = "WWW-Authenticate"

security = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Validate API key and return account name.
    
    Args:
        credentials: Bearer token from Authorization header
        
    Returns:
        Account name associated with the API key
        
    Raises:
        HTTPException: If API key is invalid
    """
    api_key = credentials.credentials
    
    if api_key not in config.VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_API_KEY,
            headers={HEADER_WWW_AUTHENTICATE: AUTH_SCHEME},
        )
    
    return config.API_KEYS[api_key]


def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[str]:
    """Optionally validate API key, return None if no credentials provided.
    
    Args:
        credentials: Optional bearer token from Authorization header
        
    Returns:
        Account name if valid API key provided, None otherwise
        
    Raises:
        HTTPException: If API key is provided but invalid
    """
    if credentials is None:
        return None
    
    api_key = credentials.credentials
    
    if api_key not in config.VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_INVALID_API_KEY,
            headers={HEADER_WWW_AUTHENTICATE: AUTH_SCHEME},
        )
    
    return config.API_KEYS[api_key]