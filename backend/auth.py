"""Authentication module for GitHub OAuth."""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.httpx_client import AsyncOAuth2Client
from itsdangerous import URLSafeTimedSerializer, BadSignature
from typing import Optional

from .config import (
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    SESSION_SECRET_KEY,
    SESSION_COOKIE_SECURE,
    ALLOWED_GITHUB_USERS,
    FRONTEND_URL,
    OAUTH_CALLBACK_URL,
)

# Session serializer
serializer = URLSafeTimedSerializer(SESSION_SECRET_KEY)

# Cookie settings
SESSION_COOKIE_NAME = "llm_council_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days

# GitHub OAuth URLs
GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"

router = APIRouter(prefix="/auth", tags=["auth"])


def is_auth_enabled() -> bool:
    """Check if authentication is enabled (has OAuth credentials configured)."""
    return bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET and ALLOWED_GITHUB_USERS)


def create_session_cookie(user_data: dict) -> str:
    """Create a signed session cookie with user data."""
    return serializer.dumps(user_data)


def decode_session_cookie(cookie_value: str) -> Optional[dict]:
    """Decode and verify a session cookie. Returns None if invalid."""
    try:
        return serializer.loads(cookie_value, max_age=SESSION_MAX_AGE)
    except BadSignature:
        return None


async def get_current_user(request: Request) -> Optional[dict]:
    """Get the current authenticated user from session cookie."""
    if not is_auth_enabled():
        # Auth disabled, return a dummy user
        return {"login": "anonymous", "auth_disabled": True}
    
    cookie_value = request.cookies.get(SESSION_COOKIE_NAME)
    if not cookie_value:
        return None
    
    return decode_session_cookie(cookie_value)


async def require_auth(request: Request) -> dict:
    """Dependency that requires authentication."""
    user = await get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.get("/status")
async def auth_status():
    """Check if authentication is enabled."""
    return {
        "enabled": is_auth_enabled(),
        "allowed_users_count": len(ALLOWED_GITHUB_USERS) if is_auth_enabled() else 0
    }


@router.get("/login")
async def login(request: Request):
    """Initiate GitHub OAuth flow."""
    if not is_auth_enabled():
        raise HTTPException(status_code=400, detail="Authentication is not configured")
    
    # Build callback URL (use explicit env var if set, otherwise auto-detect)
    callback_url = OAUTH_CALLBACK_URL or str(request.url_for("oauth_callback"))
    
    # Create OAuth client and get authorization URL
    client = AsyncOAuth2Client(
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
    )
    
    authorization_url, state = client.create_authorization_url(
        GITHUB_AUTHORIZE_URL,
        redirect_uri=callback_url,
        scope="read:user"
    )
    
    # Store state in a cookie for CSRF protection
    response = RedirectResponse(url=authorization_url, status_code=302)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="none",  # Required for cross-site cookies (frontend/backend on different domains)
        max_age=600  # 10 minutes
    )
    
    return response


@router.get("/callback")
async def oauth_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle GitHub OAuth callback."""
    if not is_auth_enabled():
        raise HTTPException(status_code=400, detail="Authentication is not configured")
    
    if error:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error={error}")
    
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=no_code")
    
    # Verify state for CSRF protection
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=invalid_state")
    
    # Build callback URL (use explicit env var if set, otherwise auto-detect)
    callback_url = OAUTH_CALLBACK_URL or str(request.url_for("oauth_callback"))
    
    # Exchange code for token
    client = AsyncOAuth2Client(
        client_id=GITHUB_CLIENT_ID,
        client_secret=GITHUB_CLIENT_SECRET,
    )
    
    try:
        token = await client.fetch_token(
            GITHUB_TOKEN_URL,
            code=code,
            redirect_uri=callback_url,
        )
    except Exception:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=token_exchange_failed")
    
    # Fetch user info
    try:
        client.token = token
        resp = await client.get(GITHUB_USER_URL)
        user_data = resp.json()
    except Exception:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=user_fetch_failed")
    
    github_username = user_data.get("login")
    
    # Check if user is in allow list
    if github_username not in ALLOWED_GITHUB_USERS:
        return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=not_authorized")
    
    # Create session data
    session_data = {
        "login": github_username,
        "name": user_data.get("name"),
        "avatar_url": user_data.get("avatar_url"),
    }
    
    # Create response with session cookie
    response = RedirectResponse(url=FRONTEND_URL, status_code=302)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_cookie(session_data),
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="none",  # Required for cross-site cookies (frontend/backend on different domains)
        max_age=SESSION_MAX_AGE
    )
    # Clear the OAuth state cookie
    response.delete_cookie(key="oauth_state")
    
    return response


@router.get("/me")
async def get_me(user: dict = Depends(require_auth)):
    """Get current authenticated user info."""
    return user


@router.post("/logout")
async def logout():
    """Log out the current user by clearing the session cookie."""
    response = RedirectResponse(url=FRONTEND_URL, status_code=302)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response


@router.get("/logout")
async def logout_get():
    """Log out the current user (GET version for browser redirect)."""
    response = RedirectResponse(url=FRONTEND_URL, status_code=302)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    return response
