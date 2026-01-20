"""Rate limiting middleware for API protection."""

import time
import threading
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
        
        # Thread lock for thread-safe operations
        self._lock = threading.Lock()
        
        # Last cleanup time to prevent excessive cleanup operations
        self._last_cleanup = time.time()
        
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
        
        # If identifier has no recent requests, remove it to prevent memory leak
        if not self.request_history[identifier]:
            del self.request_history[identifier]
    
    def _cleanup_inactive_identifiers(self, current_time: float):
        """
        Periodically clean up identifiers with no recent activity.
        
        This prevents unbounded memory growth from inactive users/IPs.
        Runs at most once per hour to minimize overhead.
        """
        # Only cleanup once per hour
        if current_time - self._last_cleanup < 3600:
            return
        
        self._last_cleanup = current_time
        window_seconds = 60  # Standard window
        cutoff_time = current_time - window_seconds
        
        # Remove identifiers with no recent requests
        identifiers_to_remove = [
            identifier for identifier, history in self.request_history.items()
            if not history or max(ts for ts, _ in history) < cutoff_time
        ]
        
        for identifier in identifiers_to_remove:
            del self.request_history[identifier]
    
    def _check_rate_limit(self, identifier: str, path: str, current_time: float) -> Tuple[bool, int, int]:
        """
        Check if request should be rate limited.
        
        Thread-safe implementation using locks.
        
        Returns:
            (is_allowed, remaining_requests, reset_seconds)
        """
        window_seconds = 60
        is_expensive = self._is_expensive_endpoint(path)
        limit = self.expensive_requests_per_minute if is_expensive else self.requests_per_minute
        
        with self._lock:
            # Periodic cleanup of inactive identifiers
            self._cleanup_inactive_identifiers(current_time)
            
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
