"""API key authentication for external API access."""

import os
import secrets
from typing import Optional
from fastapi import HTTPException, Security, Header
from fastapi.security import APIKeyHeader

from .config import SESSION_SECRET_KEY

# API key configuration
# In production, this should be stored in environment variable
# Format: "sk-council-" + 32 random hex characters
API_KEY_PREFIX = "sk-council-"
API_KEY_ENV_VAR = "API_KEY"

# Allow multiple API keys (comma-separated)
API_KEYS_ENV_VAR = "API_KEYS"


def get_valid_api_keys() -> set:
    """
    Get valid API keys from environment.
    
    Returns a set of valid API keys. If no keys are configured,
    returns an empty set (API key auth disabled).
    """
    keys = set()
    
    # Single API key
    single_key = os.getenv(API_KEY_ENV_VAR)
    if single_key:
        keys.add(single_key.strip())
    
    # Multiple API keys (comma-separated)
    multiple_keys = os.getenv(API_KEYS_ENV_VAR, "")
    if multiple_keys:
        for key in multiple_keys.split(","):
            key = key.strip()
            if key:
                keys.add(key)
    
    return keys


def generate_api_key() -> str:
    """Generate a new API key with the proper format."""
    return f"{API_KEY_PREFIX}{secrets.token_hex(32)}"


def is_api_key_auth_enabled() -> bool:
    """Check if API key authentication is enabled."""
    return bool(get_valid_api_keys())


# API key header security scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """
    Dependency to extract and validate API key from header.
    
    Returns the API key if valid, None if not provided or invalid.
    This is a permissive check - use require_api_key for enforcement.
    """
    if not is_api_key_auth_enabled():
        # API key auth is disabled, allow request
        return None
    
    if not api_key:
        return None
    
    valid_keys = get_valid_api_keys()
    if api_key in valid_keys:
        return api_key
    
    return None


async def require_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Dependency that requires a valid API key.
    
    Raises HTTPException if API key is missing or invalid.
    Use this for endpoints that must be protected by API key.
    """
    if not is_api_key_auth_enabled():
        raise HTTPException(
            status_code=503,
            detail="API key authentication is not configured on this server"
        )
    
    validated_key = await get_api_key(api_key)
    if not validated_key:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Invalid or missing API key",
                "message": "Please provide a valid API key in the X-API-Key header"
            }
        )
    
    return validated_key


async def optional_api_key(api_key: Optional[str] = Security(api_key_header)) -> Optional[str]:
    """
    Dependency for optional API key authentication.
    
    If API key auth is enabled and key is provided, validates it.
    If API key auth is disabled, allows request.
    If API key auth is enabled but no key provided, rejects request.
    """
    if not is_api_key_auth_enabled():
        # API key auth disabled, allow request
        return None
    
    # API key auth is enabled, require valid key
    return await require_api_key(api_key)
