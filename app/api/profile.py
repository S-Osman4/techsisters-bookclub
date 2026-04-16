import logging

from fastapi import APIRouter, Depends, Form, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, handle_app_error
from app.core.exceptions import AppError
from app.database import get_session
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.user import ChangePassword, DeleteAccount, UpdateName
from app.services.profile import ProfileService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/profile", tags=["Profile"])


@router.put("/name", response_model=MessageResponse)
async def update_name(
    request: Request,
    new_name: str = Form(..., min_length=2, max_length=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update the current user's display name."""
    # Validate with Pydantic schema (enforces no HTML, etc.)
    try:
        payload = UpdateName(new_name=new_name)
    except ValidationError as e:
        # Convert to HTTP 422 using the same error handler
        raise handle_app_error(e) from e

    try:
        service = ProfileService(db)
        user = await service.update_name(current_user, payload.new_name)
    except AppError as exc:
        raise handle_app_error(exc) from exc

    # Keep session name in sync
    request.session["user_name"] = user.name
    return MessageResponse(message=f"Name updated to '{user.name}'.")


@router.put("/password", response_model=MessageResponse)
async def change_password(
    request: Request,
    current_password: str = Form(..., min_length=1, max_length=100),
    new_password: str = Form(..., min_length=8, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Change the current user's password.
    Clears session after success — user must log in again.
    """
    # Validate password strength via Pydantic schema
    try:
        payload = ChangePassword(
            current_password=current_password,
            new_password=new_password,
        )
    except ValidationError as e:
        raise handle_app_error(e) from e

    try:
        service = ProfileService(db)
        await service.change_password(
            current_user,
            payload.current_password,
            payload.new_password,
        )
    except AppError as exc:
        raise handle_app_error(exc) from exc

    request.session.clear()
    return MessageResponse(
        message="Password changed. Please log in again."
    )


@router.delete("/account", response_model=MessageResponse)
async def delete_account(
    request: Request,
    password: str = Form(..., min_length=1, max_length=100),
    confirmation: str = Form(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Permanently delete the current user's account.
    Requires password and confirmation phrase.
    """
    # Validate confirmation phrase via Pydantic schema
    try:
        payload = DeleteAccount(password=password, confirmation=confirmation)
    except ValidationError as e:
        raise handle_app_error(e) from e

    try:
        service = ProfileService(db)
        await service.delete_account(
            current_user,
            payload.password,
            payload.confirmation,
        )
    except AppError as exc:
        raise handle_app_error(exc) from exc

    request.session.clear()
    return MessageResponse(message="Account deleted. Goodbye!")