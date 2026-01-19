# OAuth Cookie Fix for Cross-Domain Authentication

## Problem

After successfully signing in with GitHub, you see a `401 (Unauthorized)` error in the browser console:

```
GET https://llm-council-api-9zfj.onrender.com/auth/me 401 (Unauthorized)
```

## Root Cause

The issue occurs because the frontend and backend are hosted on different domains:

- Frontend: `https://llm-council-frontend-ux48.onrender.com`
- Backend: `https://llm-council-api-9zfj.onrender.com`

When the backend sets a session cookie with `SameSite=Lax` (the previous default), browsers block that cookie from being sent in cross-site AJAX requests. This means:

1. User completes OAuth flow and backend sets session cookie ✓
2. Backend redirects user back to frontend ✓
3. Frontend makes API call to `/auth/me` with `credentials: 'include'` ✗
4. Browser blocks the cookie because it's a cross-site request
5. Backend doesn't receive the cookie, returns 401 Unauthorized

## Solution

Change the cookie `SameSite` attribute from `"lax"` to `"none"` and ensure `Secure=True` is set.

### Technical Details

**Cross-site cookies** require:
- `SameSite=None` - Explicitly allow cross-site usage
- `Secure=True` - Only send over HTTPS (required when using SameSite=None)

### Changes Made

1. **Updated `backend/auth.py`:**
   - OAuth state cookie: Changed `samesite="lax"` → `samesite="none"`
   - Session cookie: Changed `samesite="lax"` → `samesite="none"`
   - Both cookies already use `secure=SESSION_COOKIE_SECURE`

2. **Updated `render.yaml`:**
   - Added `SESSION_COOKIE_SECURE=true` environment variable for production

## Browser Compatibility

Modern browsers (Chrome 80+, Firefox 69+, Safari 13+) require `SameSite=None; Secure` for cross-site cookies. This is a security feature to prevent CSRF attacks.

**Local Development Notes:**
- For local development with HTTP (not HTTPS), you may need to disable `SESSION_COOKIE_SECURE` in your `.env` file:
  ```
  SESSION_COOKIE_SECURE=false
  ```
- However, if testing cross-domain locally (e.g., frontend on one port, backend on another), cookies may still not work with `SameSite=None` over HTTP.

## Verification

After deploying these changes:

1. Navigate to your frontend: `https://llm-council-frontend-ux48.onrender.com`
2. Click "Sign in with GitHub"
3. Complete the OAuth flow
4. You should be redirected back and logged in
5. Open browser DevTools → Network tab
6. Verify the `/auth/me` request returns `200 OK` (not 401)
7. Check Application/Storage → Cookies
8. Verify the `llm_council_session` cookie shows:
   - `SameSite`: `None`
   - `Secure`: `✓` (checked)

## Related Documentation

- [OAuth Flow Documentation](OAUTH_FLOW.md)
- [OAuth Redirect URI Fix](OAUTH_FIX.md)
- [MDN: SameSite cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie/SameSite)

## Summary

**The fix:** Change cookie settings to use `SameSite=None` with `Secure=True` to enable cross-domain authentication between the frontend and backend services.
