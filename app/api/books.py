# app/api/books.py
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_user,
    get_current_user_optional,
    handle_app_error,
    require_code_verified,
)
from app.core.exceptions import AppError
from app.database import get_session
from app.models.user import User
from app.schemas.book import BookResponse, BookSuggestionResponse
from app.schemas.common import MessageResponse
from app.schemas.progress import CommunityProgressResponse, ProgressResponse
from app.services.book import BookService
from app.services.progress import ProgressService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/books", tags=["Books"])


@router.get("/current")
async def get_current_book(
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(require_code_verified),
):
    """
    Return the current book and meeting details.
    Accessible to guests with verified code and logged-in members.
    """
    service = BookService(db)
    book = await service.get_current_book()
    return {"book": book}


@router.get("/queue", response_model=list[BookResponse])
async def get_queue(
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(require_code_verified),
):
    """Return approved books waiting to be read."""
    service = BookService(db)
    return await service.get_queue()


@router.get("/past", response_model=list[BookResponse])
async def get_past(
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(require_code_verified),
):
    """Return completed books."""
    service = BookService(db)
    return await service.get_past()


@router.post("/suggestions", response_model=MessageResponse)
async def submit_suggestion(
    title: Annotated[str, Form()],
    pdf_url: Annotated[str, Form()],
    cover_image_url: Annotated[Optional[str], Form()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Submit a book suggestion for admin review. Members only."""
    try:
        service = BookService(db)
        await service.submit_suggestion(
            user_id=current_user.id,
            title=title,
            pdf_url=pdf_url,
            cover_image_url=cover_image_url,
        )
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(message="Suggestion submitted! Admins will review it soon.")


@router.get("/suggestions/my", response_model=list[BookSuggestionResponse])
async def get_my_suggestions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Return the current user's submitted suggestions."""
    service = BookService(db)
    return await service.get_my_suggestions(current_user.id)


@router.put("/progress", response_model=MessageResponse)
async def update_progress(
    book_id: Annotated[int, Form()],
    chapter: Annotated[int, Form()],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update reading progress for the current book. Members only."""
    try:
        service = ProgressService(db)
        await service.update_progress(
            user_id=current_user.id,
            book_id=book_id,
            chapter=chapter,
        )
    except AppError as exc:
        raise handle_app_error(exc)

    return MessageResponse(message="Progress updated.")


@router.get("/progress/my")
async def get_my_progress(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Return the current user's progress on the current book."""
    service = ProgressService(db)
    progress = await service.get_user_progress(current_user.id)
    return {"progress": progress}


@router.get("/progress/community")
async def get_community_progress(
    db: AsyncSession = Depends(get_session),
    _: bool = Depends(require_code_verified),
):
    """
    Return community reading stats for the current book.
    Accessible to all verified users.
    """
    service = ProgressService(db)
    stats = await service.get_community_stats()
    return stats