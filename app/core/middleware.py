# app/core/middleware.py
import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.security import generate_csrf_token, verify_csrf_token

logger = logging.getLogger(__name__)

# ── Routes exempt from CSRF ───────────────────────────────────────────────────
# Health check and hCaptcha callback have no session context
CSRF_EXEMPT_PATHS = {
    "/health",
    "/openapi.json",
    "/docs",
    "/redoc",
}

# Methods that mutate state and require a valid CSRF token
CSRF_PROTECTED_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection using signed double-submit cookie pattern.

    GET requests:
        - If no csrftoken cookie exists, generate and set one.
        - The token is signed with the current session ID using
          itsdangerous.TimestampSigner so it cannot be forged or
          reused across sessions.

    POST / PUT / DELETE / PATCH requests:
        - Read token from X-CSRFToken header or _csrf_token form field.
        - Verify signature and session binding.
        - Return 403 if missing or invalid.

    HTMX sends the token via the X-CSRFToken header automatically
    when we configure it in base.js (Step 9).
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip static files and exempt paths
        if path.startswith("/static") or path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        if request.method == "GET":
            response = await call_next(request)
            self._ensure_csrf_cookie(request, response)
            return response

        if request.method in CSRF_PROTECTED_METHODS:
            session_id = self._get_or_create_session_id(request)
            token = await self._extract_token(request)

            if not token or not verify_csrf_token(token, session_id):
                logger.warning(
                    "CSRF validation failed: %s %s from %s",
                    request.method,
                    path,
                    request.client.host if request.client else "unknown",
                )
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF token missing or invalid.", "success": False},
                )

        return await call_next(request)

    def _get_or_create_session_id(self, request: Request) -> str:
        """
        Return a stable session ID used only for CSRF token binding.
        This ID persists across login/logout because it's separate from user_id.
        """
        csrf_id = request.session.get("_csrf_session_id")
        if not csrf_id:
            csrf_id = str(uuid.uuid4())
            request.session["_csrf_session_id"] = csrf_id
        return csrf_id

    def _ensure_csrf_cookie(self, request: Request, response: Response) -> None:
        """
        Always set a fresh CSRF cookie bound to the current _csrf_session_id.
        This ensures the token is up‑to‑date after session changes.
        """
        csrf_id = self._get_or_create_session_id(request)
        token = generate_csrf_token(csrf_id)

        response.set_cookie(
            key="csrftoken",
            value=token,
            max_age=settings.CSRF_TOKEN_MAX_AGE,
            httponly=False,   # JavaScript must be able to read it
            samesite="lax",
            secure=settings.is_production and not settings.debug,
            path="/",
        )

    @staticmethod
    async def _extract_token(request: Request) -> str | None:
        """
        Extract CSRF token from:
        1. X-CSRFToken header (HTMX / fetch requests)
        2. _csrf_token form field (plain HTML form fallback)
        """
        # Header takes priority
        token = request.headers.get("X-CSRFToken")
        if token:
            return token

        # Form field fallback
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type or \
           "multipart/form-data" in content_type:
            try:
                form = await request.form()
                return form.get("_csrf_token")
            except Exception:
                return None

        return None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all non-redirect responses.
    Only applied in production — relaxed in development for
    easier debugging with browser dev tools.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Don't add headers to redirects
        if 300 <= response.status_code < 400:
            return response

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            # CSP is relaxed to allow HTMX inline event handlers and
            # CDN resources (Tailwind, Lucide, hCaptcha)
            # hCaptcha requires: js.hcaptcha.com (script), newassets.hcaptcha.com (frame),
            # and *.hcaptcha.com + *.hcaptcha.io (connect) for verification API calls.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' "
                    "https://cdn.tailwindcss.com "
                    "https://unpkg.com "
                    "https://js.hcaptcha.com "
                    "https://newassets.hcaptcha.com; "
                "style-src 'self' 'unsafe-inline' "
                    "https://cdn.tailwindcss.com "
                    "https://fonts.googleapis.com "
                    "https://newassets.hcaptcha.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' "
                    "https://hcaptcha.com "
                    "https://*.hcaptcha.com "
                    "https://*.hcaptcha.io; "
                "frame-src https://hcaptcha.com https://newassets.hcaptcha.com;"
            )

        return response