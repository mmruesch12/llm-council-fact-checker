"""Rate limiting middleware for API protection."""

import time
from collections import defaultdict
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RateLimiter(BaseHTTPMiddleware):
    """
    Rate limiting middleware to protect against API abuse.
    
    Implements a sliding window rate limiter with separate limits for:
    - Anonymous users (by IP)
    - Authenticated users (by user ID)
    - Special protection for expensive endpoints
    """
    
    def __init__(self, app, requests_per_minute: int = 60, expensive_requests_per_minute: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.expensive_requests_per_minute = expensive_requests_per_minute
        
        # Storage: {identifier: [(timestamp, endpoint), ...]}
        self.request_history: Dict[str, list] = defaultdict(list)
        
        # Expensive endpoints that need stricter limits
        self.expensive_endpoints = {
            "/api/synthesize",
            "/api/conversations/{conversation_id}/message",
            "/api/conversations/{conversation_id}/message/stream"
        }
    
    def _is_expensive_endpoint(self, path: str) -> bool:
        """Check if endpoint is expensive (uses LLM APIs)."""
        # Direct match or pattern match for conversation endpoints
        if path == "/api/synthesize":
            return True
        if "/message" in path and "/api/conversations/" in path:
            return True
        return False
    
    def _get_identifier(self, request: Request) -> str:
        """Get rate limit identifier (user ID or IP)."""
        # Try to get user from session cookie
        user = getattr(request.state, "user", None)
        if user and user.get("login"):
            return f"user:{user['login']}"
        
        # Fall back to IP address
        # Handle X-Forwarded-For for proxy/load balancer setups
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        
        return f"ip:{ip}"
    
    def _clean_old_requests(self, identifier: str, current_time: float, window_seconds: int):
        """Remove requests older than the time window."""
        cutoff_time = current_time - window_seconds
        self.request_history[identifier] = [
            (ts, endpoint) for ts, endpoint in self.request_history[identifier]
            if ts > cutoff_time
        ]
    
    def _check_rate_limit(self, identifier: str, path: str, current_time: float) -> Tuple[bool, int, int]:
        """
        Check if request should be rate limited.
        
        Returns:
            (is_allowed, remaining_requests, reset_seconds)
        """
        window_seconds = 60
        is_expensive = self._is_expensive_endpoint(path)
        limit = self.expensive_requests_per_minute if is_expensive else self.requests_per_minute
        
        # Clean old requests
        self._clean_old_requests(identifier, current_time, window_seconds)
        
        # Count requests in current window
        request_count = len(self.request_history[identifier])
        
        # Check limit
        if request_count >= limit:
            # Calculate when the oldest request will expire
            oldest_timestamp = min(ts for ts, _ in self.request_history[identifier])
            reset_seconds = int(window_seconds - (current_time - oldest_timestamp)) + 1
            return False, 0, reset_seconds
        
        # Add current request
        self.request_history[identifier].append((current_time, path))
        remaining = limit - request_count - 1
        
        return True, remaining, window_seconds
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health check and auth endpoints
        if request.url.path in ["/", "/auth/status", "/auth/login", "/auth/callback", "/auth/me"]:
            return await call_next(request)
        
        identifier = self._get_identifier(request)
        current_time = time.time()
        path = request.url.path
        
        is_allowed, remaining, reset_seconds = self._check_rate_limit(identifier, path, current_time)
        
        if not is_allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please try again in {reset_seconds} seconds.",
                    "retry_after": reset_seconds
                }
            )
        
        # Process request
        response: Response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(
            self.expensive_requests_per_minute if self._is_expensive_endpoint(path) 
            else self.requests_per_minute
        )
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time) + reset_seconds)
        
        return response
