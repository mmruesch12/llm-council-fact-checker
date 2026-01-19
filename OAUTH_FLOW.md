# OAuth Flow Diagram

## Before Fix (Incorrect)

```
GitHub OAuth App Configuration:
  Callback URL: https://llm-council-frontend-ux48.onrender.com/auth/callback ❌
                                  ↑
                                  |
                            Points to FRONTEND
                            (but endpoint is in BACKEND)

User Flow:
  1. User clicks "Login" on Frontend
  2. → Frontend sends to Backend /auth/login
  3. → Backend generates OAuth URL with redirect_uri
  4. → User authorizes on GitHub
  5. → GitHub redirects to: frontend/auth/callback ❌
  6. → 404 Error! (no such endpoint on frontend)
```

## After Fix (Correct)

```
GitHub OAuth App Configuration:
  Callback URL: https://llm-council-api-9zfj.onrender.com/auth/callback ✅
                                  ↑
                                  |
                            Points to BACKEND
                            (where endpoint actually exists)

User Flow:
  1. User clicks "Login" on Frontend
     https://llm-council-frontend-ux48.onrender.com
     
  2. → Redirects to Backend /auth/login
     https://llm-council-api-9zfj.onrender.com/auth/login
     
  3. → Backend generates GitHub OAuth URL with redirect_uri:
     redirect_uri=https://llm-council-api-9zfj.onrender.com/auth/callback
     
  4. → User redirected to GitHub to authorize
     https://github.com/login/oauth/authorize?client_id=...&redirect_uri=...
     
  5. → User authorizes app on GitHub
  
  6. → GitHub redirects back to Backend callback:
     https://llm-council-api-9zfj.onrender.com/auth/callback?code=...&state=...
     
  7. → Backend exchanges code for access token
     ✓ Validates user is in ALLOWED_GITHUB_USERS
     ✓ Creates session cookie
     
  8. → Backend redirects to Frontend with session cookie:
     https://llm-council-frontend-ux48.onrender.com
     
  9. → User is logged in! ✅
```

## Key Takeaway

**The OAuth callback URL must ALWAYS point to the backend API where the `/auth/callback` endpoint is implemented, NOT the frontend.**

### Services

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | `https://llm-council-frontend-ux48.onrender.com` | React UI |
| Backend API | `https://llm-council-api-9zfj.onrender.com` | FastAPI with OAuth endpoints |
| OAuth Callback | `https://llm-council-api-9zfj.onrender.com/auth/callback` | Where GitHub redirects after auth |

### Environment Variables

```bash
# Backend (.env or Render dashboard)
FRONTEND_URL=https://llm-council-frontend-ux48.onrender.com
OAUTH_CALLBACK_URL=https://llm-council-api-9zfj.onrender.com/auth/callback
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
ALLOWED_GITHUB_USERS=username1,username2
```
