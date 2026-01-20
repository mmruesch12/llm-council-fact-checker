# API Security Guide

This document describes the security measures implemented to protect the LLM Council API endpoints.

## Overview

The API implements multiple layers of security to protect against abuse, unauthorized access, and common web vulnerabilities:

1. **Rate Limiting** - Prevents API abuse and DoS attacks
2. **Authentication** - GitHub OAuth for user sessions and API keys for programmatic access
3. **Security Headers** - OWASP-recommended headers to prevent common attacks
4. **Request Validation** - Input size limits and type validation
5. **CORS Protection** - Strict origin validation

## Security Features

### 1. Rate Limiting

**Implementation:** Sliding window rate limiter with per-user and per-IP tracking.

**Default Limits:**
- General endpoints: 60 requests/minute
- Expensive endpoints (LLM API calls): 10 requests/minute

**Expensive endpoints:**
- `POST /api/synthesize`
- `POST /api/conversations/{id}/message`
- `POST /api/conversations/{id}/message/stream`

**Configuration:**
```bash
# .env
RATE_LIMIT_GENERAL=60         # General endpoints (requests/minute)
RATE_LIMIT_EXPENSIVE=10       # LLM endpoints (requests/minute)
```

**Rate Limit Headers:**
All responses include rate limit information:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1642518000
```

**Rate Limit Error Response:**
```json
{
  "detail": {
    "error": "Rate limit exceeded",
    "message": "Too many requests. Please try again in 45 seconds.",
    "retry_after": 45
  }
}
```

### 2. Authentication

The API supports two authentication methods:

#### A. GitHub OAuth (Session-based)

For web UI users. See main README for setup instructions.

**Protected endpoints:**
- All conversation management endpoints (when auth enabled)
- Export endpoint (always requires auth)
- Error catalog DELETE endpoint (always requires auth)

**Optional protection:**
- Other endpoints use `optional_auth` - protected only if auth is enabled

#### B. API Key Authentication

For programmatic access and external integrations.

**Generating API Keys:**

```python
# Run this to generate a new API key
python -c "from backend.api_key_auth import generate_api_key; print(generate_api_key())"
```

Output: `sk-council-<64-character-hex-string>`

**Configuration:**
```bash
# .env

# Single API key
API_KEY=sk-council-1234567890abcdef...

# OR multiple API keys (comma-separated)
API_KEYS=sk-council-key1...,sk-council-key2...,sk-council-key3...
```

**Using API Keys:**

Include the API key in the `X-API-Key` header:

```bash
curl -X POST "http://localhost:8001/api/synthesize" \
  -H "X-API-Key: sk-council-1234567890abcdef..." \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What causes climate change?",
    "chairman_model": "x-ai/grok-4.1-fast"
  }'
```

```python
import httpx

headers = {
    "X-API-Key": "sk-council-1234567890abcdef..."
}

response = httpx.post(
    "http://localhost:8001/api/synthesize",
    headers=headers,
    json={
        "question": "What causes climate change?",
        "chairman_model": "x-ai/grok-4.1-fast"
    }
)
```

**Protected Endpoints:**

When authentication is enabled (either OAuth or API keys are configured):

- `POST /api/synthesize` - **Requires auth** (session OR API key)
- `GET /api/errors` - **Requires auth** (session OR API key)
- `DELETE /api/errors` - **Requires session** (API key not accepted for destructive operations)

### 3. Security Headers

All responses include OWASP-recommended security headers:

```
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; ...
Permissions-Policy: geolocation=(), microphone=(), camera=(), payment=()
```

**Protection Against:**
- Clickjacking attacks
- MIME type sniffing
- XSS attacks
- Unauthorized feature access

### 4. Request Validation

**Input Size Limits:**
- Message content: 50KB maximum
- Question field: 50KB maximum
- Response content: 50KB maximum per response

**Validation:**
All request models use Pydantic validation with strict type checking.

**Example Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "content"],
      "msg": "ensure this value has at most 50000 characters",
      "type": "value_error.any_str.max_length"
    }
  ]
}
```

### 5. CORS Protection

**Allowed Origins:**
- Localhost (development): `http://localhost:5173`, `http://localhost:3000`
- Production frontend: Set via `FRONTEND_URL` environment variable
- Additional origins: Set via `ADDITIONAL_CORS_ORIGINS` (comma-separated)
- Render.com subdomains: Regex pattern `https://.*\.onrender\.com`

**Configuration:**
```bash
# .env
FRONTEND_URL=https://your-frontend.com
ADDITIONAL_CORS_ORIGINS=https://domain1.com,https://domain2.com
```

**Security Notes:**
- Origins must start with `http://` or `https://`
- Invalid origins are rejected with a warning
- Credentials are allowed only for whitelisted origins

## Endpoint Security Summary

| Endpoint | Auth Required | Rate Limit | API Key Support |
|----------|--------------|------------|-----------------|
| `GET /` | No | 60/min | N/A |
| `GET /api/models` | Optional* | 60/min | Yes |
| `POST /api/synthesize` | **Yes*** | **10/min** | Yes |
| `GET /api/conversations` | Optional* | 60/min | Yes |
| `POST /api/conversations` | Optional* | 60/min | Yes |
| `GET /api/conversations/{id}` | Optional* | 60/min | Yes |
| `DELETE /api/conversations/{id}` | Optional* | 60/min | Yes |
| `GET /api/conversations/{id}/export` | **Always** | 60/min | No |
| `POST /api/conversations/{id}/message` | Optional* | **10/min** | Yes |
| `POST /api/conversations/{id}/message/stream` | Optional* | **10/min** | Yes |
| `GET /api/errors` | **Yes*** | 60/min | Yes |
| `DELETE /api/errors` | **Always** | 60/min | No |
| `GET /auth/*` | Varies | 60/min | N/A |

**Legend:**
- **Always**: Always requires session authentication (even if auth is disabled)
- **Yes***: Requires auth (session OR API key) only when auth is enabled
- **Optional***: Protected only when auth is enabled (session OR API key)
- **10/min**: Expensive endpoint with stricter rate limit

## Security Best Practices

### For Production Deployments:

1. **Enable Authentication:**
   ```bash
   # GitHub OAuth
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   ALLOWED_GITHUB_USERS=username1,username2
   
   # API Keys
   API_KEYS=sk-council-...,sk-council-...
   ```

2. **Use Secure Cookies:**
   ```bash
   SESSION_COOKIE_SECURE=true  # Requires HTTPS
   SESSION_SECRET_KEY=your_random_64_char_secret
   ```

3. **Configure CORS Properly:**
   ```bash
   FRONTEND_URL=https://your-actual-frontend.com
   # Don't add untrusted domains
   ```

4. **Adjust Rate Limits:**
   ```bash
   RATE_LIMIT_GENERAL=100      # Increase if needed
   RATE_LIMIT_EXPENSIVE=5      # Decrease to control costs
   ```

5. **Monitor Usage:**
   - Check rate limit headers in responses
   - Monitor error catalog for suspicious patterns
   - Review logs for 429 (rate limit) and 401 (auth) errors

6. **Rotate API Keys Regularly:**
   - Generate new keys periodically
   - Remove old keys from environment
   - Update client applications

### For Development:

1. **Optional Authentication:**
   - Leave auth variables unset to disable authentication
   - Useful for local development and testing

2. **Relaxed Rate Limits:**
   ```bash
   RATE_LIMIT_GENERAL=1000
   RATE_LIMIT_EXPENSIVE=100
   ```

3. **Local CORS:**
   - Default localhost origins are automatically allowed

## Security Monitoring

### Rate Limit Events

Monitor for `429 Too Many Requests` responses:
- Indicates potential abuse or misconfigured client
- Check `X-RateLimit-*` headers to diagnose

### Authentication Failures

Monitor for `401 Unauthorized` responses:
- Invalid or missing API keys
- Expired or invalid sessions
- Unauthorized user attempts

### Request Size Validation

Monitor for `422 Unprocessable Entity` responses:
- Oversized requests
- Invalid data types
- Missing required fields

## Troubleshooting

### "Authentication required" error

**Cause:** Endpoint requires auth but no valid session or API key provided.

**Solutions:**
1. Authenticate via GitHub OAuth (for web UI)
2. Provide valid API key in `X-API-Key` header
3. Disable auth by not setting `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `ALLOWED_GITHUB_USERS`

### "Rate limit exceeded" error

**Cause:** Too many requests in time window.

**Solutions:**
1. Wait for `retry_after` seconds (from error response)
2. Implement exponential backoff in client
3. Increase rate limits in production (if legitimate usage)
4. Distribute requests across multiple users/IPs

### CORS errors

**Cause:** Frontend domain not in allowed origins.

**Solutions:**
1. Add domain to `FRONTEND_URL` or `ADDITIONAL_CORS_ORIGINS`
2. Ensure domain starts with `http://` or `https://`
3. Check browser console for specific CORS error

### "Invalid API key" error

**Cause:** API key is malformed, expired, or not configured.

**Solutions:**
1. Verify API key format: `sk-council-<64-hex-chars>`
2. Check API key is in `API_KEY` or `API_KEYS` environment variable
3. Generate new API key if needed
4. Ensure no extra spaces or newlines in environment variable

## Migration Guide

### Upgrading from Unprotected API

If you're upgrading from a version without these security features:

1. **Existing deployments continue to work** - Auth is optional by default
2. **To enable protection:**
   - Set `API_KEYS` environment variable
   - OR configure GitHub OAuth (see main README)
3. **Update external clients:**
   - Add `X-API-Key` header to API requests
   - Implement rate limit retry logic
   - Handle 401 and 429 status codes

### Gradual Rollout

1. **Phase 1:** Deploy with auth disabled (current behavior)
2. **Phase 2:** Generate and distribute API keys to clients
3. **Phase 3:** Enable auth by setting environment variables
4. **Phase 4:** Monitor and adjust rate limits as needed

## API Key Management

### Creating Keys

```python
# Generate a single key
python -c "from backend.api_key_auth import generate_api_key; print(generate_api_key())"

# Generate multiple keys
python -c "from backend.api_key_auth import generate_api_key; print(','.join([generate_api_key() for _ in range(3)]))"
```

### Storing Keys

**In .env file:**
```bash
API_KEYS=sk-council-abc...,sk-council-def...,sk-council-ghi...
```

**In Render.com dashboard:**
1. Go to service → Environment
2. Add `API_KEYS` variable
3. Paste comma-separated keys
4. Save and redeploy

### Revoking Keys

1. Remove key from `API_KEYS` environment variable
2. Restart/redeploy application
3. Removed keys are immediately invalidated

### Key Rotation

Best practice: Rotate keys every 90 days

1. Generate new key
2. Add to `API_KEYS` (keep old keys temporarily)
3. Update clients with new key
4. After grace period, remove old keys
5. Redeploy

## Additional Security Considerations

### HTTPS in Production

**Always use HTTPS in production:**
- Required for secure session cookies (`SESSION_COOKIE_SECURE=true`)
- Prevents API key interception
- Required for OAuth callback

### Environment Variables

**Never commit secrets:**
- Use `.env` file (add to `.gitignore`)
- Use platform secret management (Render.com, AWS Secrets Manager, etc.)
- Rotate secrets if accidentally exposed

### Session Security

**Production cookie settings:**
```python
httponly=True      # Prevent JavaScript access
secure=True        # HTTPS only
samesite="none"    # Cross-site cookies (adjust if frontend/backend same domain)
```

### API Key Security

**Best practices:**
- Generate keys with sufficient entropy (64 hex chars)
- Use HTTPS to prevent interception
- Store securely (environment variables, secret managers)
- Don't log or display keys
- Rotate regularly
- Revoke immediately if compromised

### Defense in Depth

Multiple security layers:
1. Rate limiting (prevent abuse)
2. Authentication (verify identity)
3. Input validation (prevent injection)
4. Security headers (prevent common attacks)
5. CORS (prevent unauthorized origins)

Each layer provides protection even if others fail.

## Support

For security issues, please review this guide first. For additional questions:
- Check main README.md for general setup
- Review endpoint documentation in code
- Examine error messages for specific guidance
