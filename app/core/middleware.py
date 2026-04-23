"""
Production middleware stack.
Provides request logging, rate limiting, error handling, and security headers.
Includes Redis-backed rate limiting with in-memory fallback.
"""
import time
import uuid
from typing import Callable, Optional
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import json

logger = logging.getLogger("devtrack.middleware")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every request with timing, status code, and request ID.
    Attaches a unique request_id to each request for tracing.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        start_time = time.time()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration = round((time.time() - start_time) * 1000, 2)

            # Don't log static asset requests
            if not path.startswith("/assets/") and not path.startswith("/widget/"):
                logger.info(
                    f"{method} {path} -> {response.status_code} ({duration}ms) [{request_id}]"
                )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration}ms"
            return response

        except Exception as exc:
            duration = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"{method} {path} -> 500 ({duration}ms) [{request_id}] Error: {exc}",
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiter with Redis backend and in-memory fallback.
    Supports per-endpoint and per-user rate limiting.
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60,
                 auth_max_requests: int = 10, redis_url: str = None):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.auth_max_requests = auth_max_requests
        self.redis_client = None
        self.clients: dict = {}  # In-memory fallback

        # Try to connect to Redis for distributed rate limiting
        if redis_url:
            try:
                import redis
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                logger.info("✅ Rate limiter using Redis backend")
            except Exception as e:
                logger.warning(f"⚠️ Redis rate limiter unavailable, using in-memory: {e}")
                self.redis_client = None

    def _get_limit_for_path(self, path: str) -> int:
        """Get rate limit based on the endpoint."""
        if "/auth/" in path:
            return self.auth_max_requests
        if "/chat/" in path or "/whatsapp/" in path:
            return self.max_requests * 2  # Higher limit for chat
        return self.max_requests

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks, static files, and docs
        skip_paths = ("/api/health", "/", "/api/docs", "/api/redoc", "/assets/", "/widget/")
        if any(request.url.path.startswith(p) for p in skip_paths):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        limit = self._get_limit_for_path(path)

        # Build rate limit key
        rate_key = f"rl:{client_ip}:{path.split('/')[3] if len(path.split('/')) > 3 else 'default'}"

        is_limited = False

        if self.redis_client:
            # Redis-backed rate limiting
            try:
                current = self.redis_client.incr(rate_key)
                if current == 1:
                    self.redis_client.expire(rate_key, self.window_seconds)
                is_limited = current > limit
            except Exception:
                # Fall through to in-memory if Redis fails
                pass
        
        if not self.redis_client:
            # In-memory fallback
            now = time.time()
            if rate_key in self.clients:
                self.clients[rate_key] = [
                    t for t in self.clients[rate_key]
                    if now - t < self.window_seconds
                ]
            else:
                self.clients[rate_key] = []

            is_limited = len(self.clients[rate_key]) >= limit
            if not is_limited:
                self.clients[rate_key].append(now)

        if is_limited:
            logger.warning(f"Rate limit exceeded for {client_ip} on {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds production security headers to all responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https:; connect-src 'self' ws: wss: https:;"
        return response


class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """
    Catches all unhandled exceptions and returns a clean JSON error.
    Prevents stack traces from leaking to clients in production.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(f"Unhandled exception: {exc}", exc_info=True)

            # Send to Sentry if configured
            try:
                from app.core.config import settings
                if settings.SENTRY_DSN:
                    import sentry_sdk
                    sentry_sdk.capture_exception(exc)
            except Exception:
                pass

            return JSONResponse(
                status_code=500,
                content={
                    "detail": "An unexpected error occurred. Our team has been notified.",
                    "type": "internal_error",
                },
            )


def setup_middleware(app: FastAPI, debug: bool = False):
    """Register all middleware in the correct order."""
    from app.core.config import settings

    # Order matters: outermost middleware runs first
    if not debug:
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=200,
            window_seconds=60,
            auth_max_requests=10,
            redis_url=settings.REDIS_URL,
        )
    else:
        app.add_middleware(
            RateLimitMiddleware,
            max_requests=1000,
            window_seconds=60,
            auth_max_requests=50,
        )

    app.add_middleware(GlobalExceptionMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
