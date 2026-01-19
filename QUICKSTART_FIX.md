# Quick Start: Fixing Your OAuth Issue

## What You Need to Do RIGHT NOW

### Step 1: Update Your GitHub OAuth App (5 minutes)

1. Go to: **https://github.com/settings/developers**

2. Click on your **LLM Council OAuth App**

3. Find the field: **"Authorization callback URL"**

4. **Change it from:**
   ```
   https://llm-council-frontend-ux48.onrender.com/auth/callback
   ```

5. **Change it to:**
   ```
   https://llm-council-api-9zfj.onrender.com/auth/callback
   ```

6. Click **"Update application"**

### Step 2: Merge This PR

This PR adds the `OAUTH_CALLBACK_URL` environment variable to your Render configuration. When you merge it, Render will automatically deploy the changes.

### Step 3: Test It

1. Go to: **https://llm-council-frontend-ux48.onrender.com**
2. Click **"Login with GitHub"**
3. You should be redirected to GitHub to authorize
4. After authorizing, you should be redirected back and logged in ✅

## Why This Happened

The OAuth callback URL was pointing to your **frontend** but the actual OAuth endpoint (`/auth/callback`) is in your **backend**.

### The Fix in Simple Terms

```
❌ BEFORE: GitHub → Frontend (no endpoint exists there!)
✅ AFTER:  GitHub → Backend (endpoint exists!) → Frontend (with session)
```

## What Changed in the Code

1. **Added `OAUTH_CALLBACK_URL` environment variable** 
   - Lets you explicitly set the callback URL for production
   - Falls back to auto-detection for local development

2. **Updated `render.yaml`**
   - Sets the correct callback URL for your Render deployment

3. **Updated documentation**
   - README now clearly explains callback URL must point to backend
   - Added comprehensive guides (OAUTH_FIX.md, OAUTH_FLOW.md)

## Files Changed

- `backend/config.py` - Added OAUTH_CALLBACK_URL config
- `backend/auth.py` - Use explicit callback URL when set
- `render.yaml` - Configure callback URL for production
- `README.md` - Updated auth documentation
- `OAUTH_FIX.md` - Detailed explanation of the fix
- `OAUTH_FLOW.md` - Visual diagrams
- `test_oauth_config.py` - Test script to verify configuration

## Need Help?

See the detailed documentation:
- **OAUTH_FIX.md** - Complete explanation and troubleshooting
- **OAUTH_FLOW.md** - Visual diagrams of the OAuth flow
- **README.md** - Updated authentication section

---

**TL;DR**: Update your GitHub OAuth app callback URL to point to your **backend** URL, then merge this PR. That's it! 🎉
