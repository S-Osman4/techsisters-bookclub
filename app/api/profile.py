# app/api/profile.py
import logging

from fastapi import APIRouter, Depends, Request, Response, status
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
    payload: UpdateName,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update the current user's display name."""
    try:
        service = ProfileService(db)
        user = await service.update_name(current_user, payload.new_name)
    except AppError as exc:
        raise handle_app_error(exc)

    # Keep session name in sync
    request.session["user_name"] = user.name
    return MessageResponse(message=f"Name updated to '{user.name}'.")


@router.put("/password", response_model=MessageResponse)
async def change_password(
    request: Request,
    payload: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Change the current user's password.
    Clears session after success — user must log in again.
    """
    try:
        service = ProfileService(db)
        await service.change_password(
            current_user,
            payload.current_password,
            payload.new_password,
        )
    except AppError as exc:
        raise handle_app_error(exc)

    request.session.clear()
    return MessageResponse(
        message="Password changed. Please log in again."
    )


@router.delete("/account", response_model=MessageResponse)
async def delete_account(
    request: Request,
    payload: DeleteAccount,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Permanently delete the current user's account.
    Requires password and confirmation phrase.
    """
    try:
        service = ProfileService(db)
        await service.delete_account(
            current_user,
            payload.password,
            payload.confirmation,
        )
    except AppError as exc:
        raise handle_app_error(exc)

    request.session.clear()
    return MessageResponse(message="Account deleted. Goodbye!")