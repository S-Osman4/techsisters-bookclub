# app/api/deps.py
import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from app.core.exceptions import AppError
from app.database import get_session
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.auth import AuthService

logger = logging.getLogger(__name__)


# ── Session helpers ───────────────────────────────────────────────────────────

def _get_session_data(request: Request) -> dict:
    """Return raw session dict."""
    return dict(request.session)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """
    Resolve the current authenticated user from session.

    Checks:
    1. user_id present in session
    2. Session not expired (7-day absolute timeout)
    3. User exists in database

    Raises HTTP 401 on any failure.
    """
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    # Check absolute session timeout
    session_created_at = request.session.get("session_created_at")
    if not session_created_at or AuthService.is_session_expired(session_created_at):
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again.",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please log in again.",
        )

    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """
    Return the current user if authenticated, otherwise None.
    Used for pages that work for both guests and members.
    """
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Ensure the current user is an admin.
    Raises HTTP 403 otherwise.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


async def require_code_verified(request: Request) -> bool:
    """
    Ensure the access code has been verified OR user is logged in.
    Raises HTTP 403 otherwise.
    """
    code_verified = request.session.get("code_verified", False)
    user_id = request.session.get("user_id")

    if not code_verified and not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access code verification required.",
        )
    return True


# ── Error mapping ─────────────────────────────────────────────────────────────

def handle_app_error(exc: Exception) -> HTTPException:
    """
    Convert domain AppError or Pydantic ValidationError into a FastAPI HTTPException.
    """
    if isinstance(exc, ValidationError):
        # Format Pydantic errors into a readable string
        errors = exc.errors()
        messages = []
        for err in errors:
            loc = " -> ".join(str(x) for x in err["loc"])
            messages.append(f"{loc}: {err['msg']}")
        detail = "; ".join(messages) if messages else "Invalid input."
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

    if isinstance(exc, AppError):
        return HTTPException(status_code=exc.status_code, detail=exc.detail)

    # Fallback for unexpected errors (shouldn't happen here)
    logger.exception("Unhandled exception in handle_app_error")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred.",
    )