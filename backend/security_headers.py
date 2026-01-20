"""Security headers middleware for enhanced protection."""

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi import Request


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Implements OWASP recommended security headers to protect against
    common web vulnerabilities.
    """
    
    def __init__(self, app):
        super().__init__(app)
        # Get CSP mode from environment (default: relaxed for development)
        self.csp_mode = os.getenv("CSP_MODE", "relaxed")
    
    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response: Response = await call_next(request)
        
        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection in older browsers (legacy header)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy for privacy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy - configurable for production vs development
        if self.csp_mode == "strict":
            # Production mode: Strict CSP without unsafe directives
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://openrouter.ai; "
                "frame-ancestors 'none';"
            )
        else:
            # Development mode: Relaxed CSP with unsafe directives for easier debugging
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://openrouter.ai; "
                "frame-ancestors 'none';"
            )
        response.headers["Content-Security-Policy"] = csp
        
        # Permissions policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        
        return response
