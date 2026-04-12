# app/api/admin.py
import logging
import secrets
import string
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import handle_app_error, require_admin
from app.core.exceptions import AppError
from app.database import get_session
from app.models.user import User
from app.schemas.access_code import AccessCodeResponse, AccessCodeUpdate
from app.schemas.admin import AdminLogDetailResponse, AdminStatsResponse
from app.schemas.book import BookUpdate, SetCurrentBook
from app.schemas.common import MessageResponse
from app.schemas.meeting import MeetingResponse, MeetingUpdate
from app.schemas.user import UserResponse
from app.services.admin import AdminService
from app.services.book import BookService
from app.services.meeting import MeetingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── Access code ───────────────────────────────────────────────────────────────

@router.get("/code", response_model=AccessCodeResponse)
async def get_access_code(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    from app.repositories.access_code import AccessCodeRepository
    repo = AccessCodeRepository(db)
    code = await repo.get()
    if not code:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Access code not configured.")
    return code


@router.put("/code", response_model=MessageResponse)
async def update_access_code(
    payload: AccessCodeUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    try:
        service = AdminService(db)
        new_code = await service.update_access_code(payload.new_code, admin.id)
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(
        message=f"Access code updated to: {new_code}. Post it in the WhatsApp group!"
    )


@router.post("/code/generate", response_model=dict)
async def generate_code_preview(admin: User = Depends(require_admin)):
    chars = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(chars) for _ in range(8))
    return {"generated_code": code, "message": "Click Update to save this code."}


# ── Meeting ───────────────────────────────────────────────────────────────────

@router.get("/meeting", response_model=Optional[MeetingResponse])
async def get_meeting(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    service = MeetingService(db)
    return await service.get_meeting()


@router.put("/meeting", response_model=MessageResponse)
async def update_meeting(
    payload: MeetingUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    try:
        service = MeetingService(db)
        await service.update_meeting(
            start_at_local=payload.start_at_local,
            timezone=payload.timezone,
            meet_link=str(payload.meet_link),
            admin_id=admin.id,
            is_cancelled=payload.is_cancelled,
            cancellation_note=payload.cancellation_note,
        )
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(message="Meeting updated successfully.")


# ── Books ─────────────────────────────────────────────────────────────────────

@router.put("/books/current", response_model=MessageResponse)
async def update_current_book(
    payload: BookUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """Update fields on the current book."""
    try:
        service = BookService(db)
        await service.update_current_book(
            admin_id=admin.id,
            title=payload.title,
            pdf_url=payload.pdf_url,
            cover_image_url=payload.cover_image_url,
            chapter_from=payload.chapter_from,
            chapter_to=payload.chapter_to,
            total_chapters=payload.total_chapters,
        )
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(message="Current book updated.")


@router.post("/books/{book_id}/set-current", response_model=MessageResponse)
async def set_current_book(
    book_id: int,
    payload: SetCurrentBook,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """Move a queued book to current."""
    logger.info(
        "set_current_book: book_id=%s chapter_from=%s chapter_to=%s",
        book_id, payload.chapter_from, payload.chapter_to,
    )
    try:
        service = BookService(db)
        book = await service.set_current_book(
            book_id=book_id,
            admin_id=admin.id,
            chapter_from=payload.chapter_from,
            chapter_to=payload.chapter_to,
            cover_image_url=payload.cover_image_url,
            total_chapters=payload.total_chapters,
        )
    except AppError as exc:
        logger.error("set_current_book error: %s", exc)
        raise handle_app_error(exc)

    return MessageResponse(message=f"'{book.title}' is now the current book.")


@router.post("/books/complete", response_model=MessageResponse)
async def complete_current_book(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    try:
        service = BookService(db)
        book = await service.complete_current_book(admin.id)
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(message=f"'{book.title}' marked as completed.")


# ── Suggestions ───────────────────────────────────────────────────────────────

@router.get("/suggestions/pending")
async def get_pending_suggestions(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    service = BookService(db)
    return await service.get_pending_suggestions()


@router.put("/suggestions/{suggestion_id}/approve", response_model=MessageResponse)
async def approve_suggestion(
    suggestion_id: int,
    cover_image_url: Annotated[Optional[str], Body(embed=True)] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """Approve a suggestion. cover_image_url falls back to the suggestion's own cover."""
    try:
        service = BookService(db)
        book = await service.approve_suggestion(
            suggestion_id=suggestion_id,
            cover_image_url=cover_image_url or "",
            admin_id=admin.id,
        )
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(message="Suggestion approved and added to queue.")


@router.put("/suggestions/{suggestion_id}/reject", response_model=MessageResponse)
async def reject_suggestion(
    suggestion_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    try:
        service = BookService(db)
        await service.reject_suggestion(suggestion_id=suggestion_id, admin_id=admin.id)
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(message="Suggestion rejected.")


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[UserResponse])
async def get_all_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    service = AdminService(db)
    return await service.get_all_users()


@router.put("/users/{user_id}/promote", response_model=MessageResponse)
async def promote_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    try:
        service = AdminService(db)
        user = await service.promote_user(user_id, admin.id)
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(message=f"{user.name} promoted to admin.")


@router.put("/users/{user_id}/demote", response_model=MessageResponse)
async def demote_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    try:
        service = AdminService(db)
        user = await service.demote_user(user_id, admin.id)
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(message=f"{user.name} demoted to member.")


# ── Stats & logs ──────────────────────────────────────────────────────────────

@router.get("/stats", response_model=AdminStatsResponse)
async def get_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    service = AdminService(db)
    return await service.get_stats()


@router.get("/logs", response_model=AdminLogDetailResponse)
async def get_logs(
    page: int = 1,
    page_size: int = 20,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    service = AdminService(db)
    return await service.get_logs(page=page, page_size=page_size)