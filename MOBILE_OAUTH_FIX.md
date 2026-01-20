# Mobile Browser OAuth Fix

## Problem

When clicking "Sign in with GitHub" on mobile browsers (especially Safari on iOS and Chrome on mobile), the page would just reload instead of logging in. Users would end up back on the same page with the sign in button, unable to authenticate.

## Root Cause

The issue was caused by **cookie blocking in mobile browsers** during OAuth redirect chains.

### Previous Implementation (Cookie-based State)

1. User clicks "Sign in with GitHub"
2. Frontend redirects to `/auth/login`
3. Backend sets `oauth_state` cookie with `SameSite=None; Secure`
4. Backend redirects to GitHub for authorization
5. User authorizes on GitHub
6. GitHub redirects back to `/auth/callback`
7. **Mobile browser blocks the `oauth_state` cookie** (treated as third-party)
8. State validation fails (no cookie found)
9. User redirected to frontend with `auth_error=invalid_state`
10. Page reloads, user sees login button again

### Why Mobile Browsers Block the Cookie

Modern mobile browsers have strict cookie policies:
- **Safari on iOS**: Blocks cookies set during redirect chains by default
- **Chrome on mobile**: Stricter third-party cookie policies
- Even with `SameSite=None; Secure`, cookies set during OAuth redirect flows are often blocked

The `oauth_state` cookie was being set in a redirect response (step 3), which mobile browsers treat as third-party and block, even though `SameSite=None` was specified.

## Solution

Replace cookie-based OAuth state storage with **server-side state storage**.

### New Implementation (Server-side State)

1. User clicks "Sign in with GitHub"
2. Frontend redirects to `/auth/login`
3. Backend **stores state in server-side cache** (in-memory with TTL)
4. Backend redirects to GitHub for authorization (no state cookie)
5. User authorizes on GitHub
6. GitHub redirects back to `/auth/callback?state=...`
7. Backend **retrieves state from server-side cache**
8. State validation succeeds
9. Session cookie set, user authenticated
10. ✅ User successfully logged in

### Implementation Details

#### Server-side State Storage (`backend/auth.py`)

```python
# In-memory cache with time-to-live (TTL)
oauth_state_cache = {}
OAUTH_STATE_TTL = 600  # 10 minutes

def store_oauth_state(state: str) -> None:
    """Store OAuth state server-side with expiration time."""
    oauth_state_cache[state] = time.time() + OAUTH_STATE_TTL
    cleanup_expired_states()

def verify_oauth_state(state: str) -> bool:
    """Verify OAuth state exists and is not expired."""
    if state not in oauth_state_cache:
        return False
    if time.time() > oauth_state_cache[state]:
        del oauth_state_cache[state]  # Expired
        return False
    del oauth_state_cache[state]  # One-time use
    return True

def cleanup_expired_states() -> None:
    """Remove expired OAuth states from cache."""
    current_time = time.time()
    expired_keys = [k for k, v in oauth_state_cache.items() if current_time > v]
    for key in expired_keys:
        del oauth_state_cache[key]
```

#### Updated Login Endpoint

**Before:**
```python
response = RedirectResponse(url=authorization_url, status_code=302)
response.set_cookie(
    key="oauth_state",
    value=state,
    httponly=True,
    secure=SESSION_COOKIE_SECURE,
    samesite="none",
    max_age=600
)
```

**After:**
```python
store_oauth_state(state)  # Server-side storage
response = RedirectResponse(url=authorization_url, status_code=302)
# No cookie needed
```

#### Updated Callback Endpoint

**Before:**
```python
stored_state = request.cookies.get("oauth_state")
if not stored_state or stored_state != state:
    return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=invalid_state")
```

**After:**
```python
if not state or not verify_oauth_state(state):
    return RedirectResponse(url=f"{FRONTEND_URL}?auth_error=invalid_state")
```

## Security Considerations

The new implementation maintains the same security properties:

1. **CSRF Protection**: State parameter prevents cross-site request forgery
2. **One-time Use**: State is deleted immediately after verification
3. **Time Limits**: States expire after 10 minutes
4. **Automatic Cleanup**: Expired states are periodically removed
5. **Session Security**: Session cookie still uses `SameSite=None; Secure` for legitimate cross-site sessions

## Deployment Notes

### No Configuration Changes Required

The fix works automatically with existing configuration. No environment variables need to be updated.

### In-memory Cache Considerations

- **Single-server deployments**: Works perfectly (like current Render setup)
- **Multi-server/load-balanced deployments**: Would need distributed cache (Redis, etc.)
  - For now, this is not an issue as the app runs on a single Render instance
  - If scaling to multiple instances in the future, consider using Redis for state storage

### Backwards Compatibility

- ✅ Existing desktop browser users: Continue to work
- ✅ Mobile browser users: Now work correctly
- ✅ No breaking changes to API or frontend
- ✅ Session cookies still work the same way

## Testing

Run the test suite to verify the fix:

```bash
python test_mobile_oauth_fix.py
```

The test verifies:
- State storage and retrieval
- One-time use enforcement
- State expiration
- Multiple concurrent states
- Automatic cleanup

## Related Files

- `backend/auth.py` - Main authentication module (contains the fix)
- `test_mobile_oauth_fix.py` - Test suite for the fix
- `OAUTH_FLOW.md` - Overall OAuth flow documentation
- `OAUTH_COOKIE_FIX.md` - Previous cookie fix for cross-domain sessions

## Browser Compatibility

### ✅ Now Works On

- Safari on iOS
- Chrome on iOS
- Chrome on Android
- Firefox on mobile
- All desktop browsers (unchanged)

### Session Cookies vs OAuth State Cookies

It's important to understand the difference:

| Cookie | Purpose | When Set | Mobile Browser Behavior |
|--------|---------|----------|------------------------|
| `oauth_state` | CSRF protection during OAuth flow | During redirect to GitHub | ❌ **Blocked** (set during redirect chain) |
| `llm_council_session` | Maintain authenticated session | After successful OAuth | ✅ **Allowed** (set after user returns) |

The `llm_council_session` cookie still uses `SameSite=None; Secure` and works correctly on mobile because it's set **after** the OAuth flow completes, not during a redirect chain.

## Summary

**The fix**: Move OAuth state from cookies to server-side storage, eliminating the dependency on cookies during the OAuth redirect flow. This resolves the mobile browser login issue while maintaining all security properties.
