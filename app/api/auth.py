# app/api/auth.py
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, handle_app_error
from app.core.exceptions import AppError, UnauthorizedError
from app.database import get_session
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import UserResponse
from app.services.auth import AuthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/verify-code", response_model=MessageResponse)
@limiter.limit("5/minute")
async def verify_code(
    request: Request,
    code: Annotated[str, Form()],
    db: AsyncSession = Depends(get_session),
):
    """
    Verify the shared access code.
    Sets code_verified=True in session on success.
    """
    try:
        service = AuthService(db)
        await service.verify_access_code(code)
    except AppError as exc:
        if isinstance(exc, UnauthorizedError):
            raise HTTPException(status_code=403, detail=exc.detail)
        raise handle_app_error(exc)

    request.session["code_verified"] = True
    return MessageResponse(message="Code verified. Welcome to TechSisters Book Club!")


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def register(
    request: Request,
    name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    h_captcha_response: Annotated[str, Form(alias="h-captcha-response")] = "",
    from_param: Annotated[str, Form(alias="from")] = "",
    db: AsyncSession = Depends(get_session),
):
    """
    Register a new member account.
    Requires code_verified in session.
    Rate limited: 5/hour.
    """
    if not request.session.get("code_verified") and not request.session.get("user_id"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Please verify the access code first.")

    client_ip = request.client.host if request.client else "unknown"

    try:
        service = AuthService(db)
        await service.verify_hcaptcha(h_captcha_response, client_ip)
        user = await service.register(name=name, email=email, password=password)
    except AppError as exc:
        raise handle_app_error(exc)
    
    # Preserve CSRF binding ID before clearing the session
    csrf_session_id = request.session.get("_csrf_session_id")
    old_code_verified = request.session.get("code_verified", False)

    request.session.clear()
    if csrf_session_id:
        request.session["_csrf_session_id"] = csrf_session_id
    request.session["code_verified"] = old_code_verified
    request.session.update(AuthService.build_session(user))

    old_code_verified = request.session.get("code_verified", False)
    request.session.clear()
    request.session["code_verified"] = old_code_verified
    request.session.update(AuthService.build_session(user))

    redirect_map = {
        "suggest": "/dashboard#suggest-book",
        "dashboard": "/dashboard",
    }
    redirect_url = redirect_map.get(from_param, "/dashboard")

    return Response(
        status_code=status.HTTP_200_OK,
        headers={"HX-Redirect": redirect_url},
    )


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    from_param: Annotated[str, Form(alias="from")] = "",
    db: AsyncSession = Depends(get_session),
):
    """
    Authenticate with email and password.
    Rate limited: 5/minute.
    """
    try:
        service = AuthService(db)
        user = await service.login(email=email, password=password)
    except AppError as exc:
        raise handle_app_error(exc)

    # Preserve CSRF binding ID before clearing the session
    csrf_session_id = request.session.get("_csrf_session_id")
    old_code_verified = request.session.get("code_verified", False)

    request.session.clear()
    if csrf_session_id:
        request.session["_csrf_session_id"] = csrf_session_id
    request.session["code_verified"] = old_code_verified
    request.session.update(AuthService.build_session(user))

    old_code_verified = request.session.get("code_verified", False)
    request.session.clear()
    request.session["code_verified"] = old_code_verified
    request.session.update(AuthService.build_session(user))

    redirect_map = {
        "suggest": "/dashboard#suggest-book",
        "suggestions": "/dashboard#your-suggestions",
        "dashboard": "/dashboard",
    }
    redirect_url = redirect_map.get(from_param, "/dashboard")

    return Response(
        status_code=status.HTTP_200_OK,
        headers={"HX-Redirect": redirect_url},
    )


@router.post("/logout")
async def logout(request: Request):
    """Clear session and redirect home."""
    request.session.clear()
    return Response(
        status_code=status.HTTP_200_OK,
        headers={"HX-Redirect": "/"},
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the current user's profile."""
    return current_user