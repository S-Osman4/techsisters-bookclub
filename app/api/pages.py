# app/api/pages.py
from __future__ import annotations

import logging
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.api.deps import get_current_user_optional, require_admin
from app.core.config import settings
from app.core.template_helpers import (
    format_meeting_time,
    mask_email,
    meeting_state,
    pluralise,
    suggestion_status_label,
)
from app.database import get_session
from app.models.user import User
from app.services.admin import AdminService
from app.services.book import BookService
from app.services.meeting import MeetingService
from app.services.progress import ProgressService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pages"])
templates = Jinja2Templates(directory="app/templates")

# ── Register custom filters ───────────────────────────────────────────────────
templates.env.filters["meeting_state"]          = meeting_state
templates.env.filters["format_meeting_time"]    = format_meeting_time
templates.env.filters["mask_email"]             = mask_email
templates.env.filters["pluralise"]              = pluralise
templates.env.filters["suggestion_status_label"] = suggestion_status_label


def _base_context(request: Request) -> dict:
    """
    Context variables available on every page.
    Includes config values templates need (WhatsApp link etc).
    """
    return {
        "request": request,
        "whatsapp_link": settings.WHATSAPP_GROUP_LINK,
        "uk_tz": ZoneInfo("Europe/London"),
        "now": datetime.now(timezone.utc),
    }


def _has_access(request: Request) -> bool:
    """Return True if user has code_verified or is logged in."""
    return (
        request.session.get("code_verified", False)
        or request.session.get("user_id") is not None
    )


# ── Landing ───────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """
    Landing page with access code modal.
    Redirects to dashboard if user already has access.
    """
    if _has_access(request):
        return RedirectResponse(url="/dashboard", status_code=302)

    return templates.TemplateResponse(
        "pages/index.html",
        {**_base_context(request)},
    )


# ── Auth pages ────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)

    return templates.TemplateResponse(
        "pages/login.html",
        {
            **_base_context(request),
            "from_param": request.query_params.get("from", ""),
        },
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)

    if not request.session.get("code_verified"):
        return RedirectResponse(
            url="/?error=verify_code_first", status_code=302
        )

    return templates.TemplateResponse(
        "pages/register.html",
        {
            **_base_context(request),
            "from_param": request.query_params.get("from", ""),
             "hcaptcha_site_key": settings.HCAPTCHA_SITE_KEY,
        },
    )



# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if not _has_access(request):
        return RedirectResponse(url="/?error=access_required", status_code=302)

    book_service     = BookService(db)
    meeting_service  = MeetingService(db)
    progress_service = ProgressService(db)

    current_book     = await book_service.get_current_book()
    meeting          = await meeting_service.get_meeting()
    upcoming_books   = await book_service.get_queue()
    past_books       = await book_service.get_past()
    community_stats  = await progress_service.get_community_stats()

    user_progress    = None
    user_suggestions = []

    if current_user:
        user_progress    = await progress_service.get_user_progress(current_user.id)
        user_suggestions = await book_service.get_my_suggestions(current_user.id)

    return templates.TemplateResponse(
        "pages/dashboard.html",
        {
            **_base_context(request),
            "current_user":    current_user,
            "current_book":    current_book,
            "meeting":         meeting,
            "upcoming_books":  upcoming_books,
            "past_books":      past_books,
            "community_stats": community_stats,
            "user_progress":   user_progress,
            "user_suggestions": user_suggestions,
            "is_guest":        current_user is None,
        },
    )


# ── Books ─────────────────────────────────────────────────────────────────────

@router.get("/past-books", response_class=HTMLResponse)
async def past_books_page(
    request: Request,
    search: str = Query(None),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if not _has_access(request):
        return RedirectResponse(url="/?error=access_required", status_code=302)

    service = BookService(db)
    books, total = await service.get_past_paginated(
        page=page, page_size=12, search=search
    )
    total_pages = max(1, (total + 11) // 12)
    is_htmx = request.headers.get("HX-Request") is not None

    context = {
        **_base_context(request),
        "current_user": current_user,
        "books":        books,
        "search":       search or "",
        "page":         page,
        "total_pages":  total_pages,
        "total_count":  total,
        "page_type":    "past",
    }

    if is_htmx:
        return templates.TemplateResponse(
            "partials/_books_grid.html", context
        )
    return templates.TemplateResponse("pages/past_books.html", context)


@router.get("/upcoming-books", response_class=HTMLResponse)
async def upcoming_books_page(
    request: Request,
    search: str = Query(None),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if not _has_access(request):
        return RedirectResponse(url="/?error=access_required", status_code=302)

    service = BookService(db)
    books, total = await service.get_queue_paginated(
        page=page, page_size=12, search=search
    )
    total_pages = max(1, (total + 11) // 12)
    is_htmx = request.headers.get("HX-Request") is not None

    context = {
        **_base_context(request),
        "current_user": current_user,
        "books":        books,
        "search":       search or "",
        "page":         page,
        "total_pages":  total_pages,
        "total_count":  total,
        "page_type":    "upcoming",
    }

    if is_htmx:
        return templates.TemplateResponse(
            "partials/_books_grid.html", context
        )
    return templates.TemplateResponse("pages/upcoming_books.html", context)


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if not current_user:
        return RedirectResponse(url="/login?error=login_required", status_code=302)

    from sqlalchemy import func, select
    from app.models.book_suggestion import BookSuggestion
    from app.models.reading_progress import ReadingProgress
    from app.repositories.user import UserRepository

    user_repo = UserRepository(db)

    # Reading stats
    async with db as session:
        total_suggestions = (await session.execute(
            select(func.count(BookSuggestion.id))
            .where(BookSuggestion.user_id == current_user.id)
        )).scalar_one()

        approved_suggestions = (await session.execute(
            select(func.count(BookSuggestion.id))
            .where(
                BookSuggestion.user_id == current_user.id,
                BookSuggestion.status == "approved",
            )
        )).scalar_one()

        books_completed = (await session.execute(
            select(func.count(ReadingProgress.id))
            .where(
                ReadingProgress.user_id == current_user.id,
                ReadingProgress.chapter == -1,
            )
        )).scalar_one()

        books_reading = (await session.execute(
            select(func.count(ReadingProgress.id))
            .where(
                ReadingProgress.user_id == current_user.id,
                ReadingProgress.chapter > 0,
            )
        )).scalar_one()

    admin_count = await user_repo.count_admins()

    return templates.TemplateResponse(
        "pages/profile.html",
        {
            **_base_context(request),
            "current_user": current_user,
            "stats": {
                "total_suggestions":    total_suggestions or 0,
                "approved_suggestions": approved_suggestions or 0,
                "books_completed":      books_completed or 0,
                "books_reading":        books_reading or 0,
            },
            "is_only_admin": current_user.is_admin and admin_count <= 1,
        },
    )


# ── Feedback ──────────────────────────────────────────────────────────────────

@router.get("/feedback", response_class=HTMLResponse)
async def feedback_page(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        "pages/feedback.html",
        {
            **_base_context(request),
            "current_user": current_user,
        },
    )


# ── Admin ─────────────────────────────────────────────────────────────────────

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    db: AsyncSession = Depends(get_session),
    admin: User = Depends(require_admin),
):
    book_service    = BookService(db)
    meeting_service = MeetingService(db)
    admin_service   = AdminService(db)

    current_book        = await book_service.get_current_book()
    meeting             = await meeting_service.get_meeting()
    pending_suggestions = await book_service.get_pending_suggestions()
    approved_queue      = await book_service.get_queue()
    stats               = await admin_service.get_stats()
    logs                = await admin_service.get_logs(page=1, page_size=20)
    all_users           = await admin_service.get_all_users()

    from app.repositories.access_code import AccessCodeRepository
    from app.repositories.user import UserRepository
    code_repo = AccessCodeRepository(db)
    user_repo = UserRepository(db)
    access_code  = await code_repo.get()
    admin_count  = await user_repo.count_admins()

    return templates.TemplateResponse(
        "pages/admin.html",
        {
            **_base_context(request),
            "admin":               admin,
            "current_book":        current_book,
            "meeting":             meeting,
            "pending_suggestions": pending_suggestions,
            "approved_queue":      approved_queue,
            "stats":               stats,
            "logs":                logs,
            "all_users":           all_users,
            "access_code":         access_code,
            "admin_count":         admin_count,
        },
    )