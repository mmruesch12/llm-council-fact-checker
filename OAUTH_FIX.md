# OAuth GitHub Redirect URI Fix

## Problem

You're seeing this error when attempting GitHub OAuth login:

```
Be careful!
The redirect_uri is not associated with this application.
The application might be misconfigured or could be trying to redirect you to a website you weren't expecting.
```

## Root Cause

The GitHub OAuth callback URL was incorrectly configured. The callback URL registered in your GitHub OAuth app settings was:

❌ **Incorrect**: `https://llm-council-frontend-ux48.onrender.com/auth/callback`

This points to the **frontend**, but the OAuth callback endpoint exists in the **backend** at `/auth/callback`.

## Solution

### Step 1: Update GitHub OAuth App Settings

1. Go to your GitHub OAuth app settings: https://github.com/settings/developers
2. Find your LLM Council OAuth app
3. Update the "Authorization callback URL" to:

✅ **Correct**: `https://llm-council-api-9zfj.onrender.com/auth/callback`

This points to your **backend** service where the OAuth handler exists.

### Step 2: Code Improvements (Already Done)

The code has been updated to:

1. **Add `OAUTH_CALLBACK_URL` environment variable** - Allows explicit configuration of the callback URL
2. **Update `render.yaml`** - Sets the correct callback URL for production deployment
3. **Update README.md** - Documents the correct callback URL configuration

### Step 3: Deploy the Changes

After merging this PR, Render will automatically deploy the updated configuration with the `OAUTH_CALLBACK_URL` environment variable set.

## How It Works

The OAuth flow now works as follows:

1. User clicks "Login with GitHub" on frontend
2. Frontend redirects to **backend** `/auth/login` endpoint
3. Backend generates OAuth authorization URL with `redirect_uri` pointing to **backend** `/auth/callback`
4. User authorizes on GitHub
5. GitHub redirects to **backend** `/auth/callback` with authorization code
6. Backend exchanges code for access token, validates user, creates session
7. Backend redirects user to **frontend** with session cookie

## Local Development vs Production

### Local Development
- Backend: `http://localhost:8001`
- Frontend: `http://localhost:5173`
- Callback URL: `http://localhost:8001/auth/callback` (auto-detected)

### Production (Render)
- Backend: `https://llm-council-api-9zfj.onrender.com`
- Frontend: `https://llm-council-frontend-ux48.onrender.com`
- Callback URL: `https://llm-council-api-9zfj.onrender.com/auth/callback` (explicitly set via `OAUTH_CALLBACK_URL`)

## Testing

After updating the GitHub OAuth app callback URL:

1. Navigate to: `https://llm-council-frontend-ux48.onrender.com`
2. Click "Login with GitHub"
3. Authorize the application
4. You should be redirected back to the frontend, successfully logged in

## Environment Variables

The following environment variables are now used for OAuth configuration:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GITHUB_CLIENT_ID` | Yes | GitHub OAuth app client ID | `Ov23abcdef123456` |
| `GITHUB_CLIENT_SECRET` | Yes | GitHub OAuth app client secret | `abc123...` |
| `ALLOWED_GITHUB_USERS` | Yes | Comma-separated list of allowed GitHub usernames | `user1,user2,user3` |
| `FRONTEND_URL` | Yes | Frontend URL for post-auth redirect | `https://llm-council-frontend-ux48.onrender.com` |
| `OAUTH_CALLBACK_URL` | Optional | Explicit OAuth callback URL (auto-detected if not set) | `https://llm-council-api-9zfj.onrender.com/auth/callback` |
| `SESSION_SECRET_KEY` | Optional | Secret key for session signing (auto-generated if not set) | Random hex string |
| `SESSION_COOKIE_SECURE` | **Required for production** | Use secure cookies (must be `true` for HTTPS/cross-domain) | `true` |

**Important:** For production deployments with separate frontend and backend domains, `SESSION_COOKIE_SECURE` **must** be set to `true`. The session cookies use `SameSite=None` to work across domains, which requires the `Secure` flag.

## Summary

The fix involves two changes:

1. **Update GitHub OAuth app settings** (manual step required)
   - Change callback URL from frontend to backend URL
   
2. **Code enhancement** (already completed in this PR)
   - Add `OAUTH_CALLBACK_URL` environment variable for explicit configuration
   - Update cookie settings to use `SameSite=None` for cross-domain compatibility
   - Require `SESSION_COOKIE_SECURE=true` in production
   - Update documentation to clarify callback URL must point to backend

After completing Step 1 (updating GitHub OAuth app settings), the authentication flow will work correctly.
