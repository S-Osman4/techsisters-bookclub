# app/services/book.py
import logging
from datetime import datetime, timezone
from typing import Optional

import bleach
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.book import Book
from app.models.book_suggestion import BookSuggestion
from app.repositories.admin_action import AdminActionRepository
from app.repositories.book import BookRepository
from app.repositories.book_suggestion import BookSuggestionRepository
from app.repositories.reading_progress import ReadingProgressRepository

logger = logging.getLogger(__name__)


def _sanitize(text: str, max_length: int = 200) -> str:
    """Strip HTML tags and limit length."""
    cleaned = bleach.clean(text, tags=[], strip=True).strip()
    return cleaned[:max_length]


def _build_chapter_string(chapter_from: int, chapter_to: Optional[int]) -> str:
    """
    Convert numeric chapter inputs to the display string stored in the DB.

    Examples:
        (2, None) → "Chapter 2"
        (2, 2)    → "Chapter 2"
        (1, 3)    → "Chapters 1–3"
    """
    to = chapter_to if chapter_to is not None else chapter_from
    if to < chapter_from:
        raise ValidationError("'To chapter' must be ≥ 'From chapter'.")
    if chapter_from == to:
        return f"Chapter {chapter_from}"
    return f"Chapters {chapter_from}\u2013{to}"


class BookService:
    """
    Handles all book-related operations:
    browsing, suggestions, admin book management.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.book_repo = BookRepository(session)
        self.suggestion_repo = BookSuggestionRepository(session)
        self.progress_repo = ReadingProgressRepository(session)
        self.log_repo = AdminActionRepository(session)

    # ── Public browsing ───────────────────────────────────────────────────────

    async def get_current_book(self) -> Book | None:
        return await self.book_repo.get_current()

    async def get_queue(self) -> list[Book]:
        return await self.book_repo.get_queue()

    async def get_past(self) -> list[Book]:
        return await self.book_repo.get_past()

    async def get_past_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ) -> tuple[list[Book], int]:
        return await self.book_repo.get_past_paginated(page, page_size, search)

    async def get_queue_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ) -> tuple[list[Book], int]:
        return await self.book_repo.get_queue_paginated(page, page_size, search)

    # ── Member suggestions ────────────────────────────────────────────────────

    async def submit_suggestion(
        self,
        user_id: int,
        title: str,
        pdf_url: str,
        cover_image_url: Optional[str],
    ) -> BookSuggestion:
        title = _sanitize(title, 200)
        pdf_url = _sanitize(pdf_url, 500)
        cover_image_url = _sanitize(cover_image_url, 500) if cover_image_url else None

        if not title:
            raise ValidationError("Title cannot be empty.")

        suggestion = await self.suggestion_repo.create(
            title=title,
            pdf_url=pdf_url,
            cover_image_url=cover_image_url,
            user_id=user_id,
            status="pending",
        )

        logger.info("Book suggestion submitted by user_id=%s: %r", user_id, title)
        return suggestion

    async def get_my_suggestions(self, user_id: int) -> list[BookSuggestion]:
        return await self.suggestion_repo.get_by_user(user_id)

    # ── Admin book management ─────────────────────────────────────────────────

    async def approve_suggestion(
        self,
        suggestion_id: int,
        cover_image_url: str,
        admin_id: int,
    ) -> Book:
        suggestion = await self.suggestion_repo.get_by_id_with_user(suggestion_id)

        if not suggestion:
            raise NotFoundError("Suggestion not found.")
        if suggestion.status != "pending":
            raise ConflictError(f"Suggestion is already {suggestion.status}.")

        # Fall back to suggestion's own cover if admin didn't supply one
        resolved_cover = _sanitize(cover_image_url, 500) if cover_image_url else ""
        resolved_cover = resolved_cover or (suggestion.cover_image_url or "")
        if not resolved_cover:
            raise ValidationError(
                "A cover image URL is required. Add one to the suggestion or paste one here."
            )

        await self.suggestion_repo.update_status(suggestion, "approved")

        book = await self.book_repo.create(
            title=suggestion.title,
            pdf_url=suggestion.pdf_url,
            cover_image_url=resolved_cover,
            status="queued",
        )

        await self.log_repo.log(
            admin_id=admin_id,
            action="approve_suggestion",
            target={
                "suggestion_id": suggestion_id,
                "book_title": suggestion.title,
                "user_name": suggestion.user.name if suggestion.user else "unknown",
            },
        )

        logger.info("Admin %s approved suggestion %s: %r", admin_id, suggestion_id, suggestion.title)
        return book

    async def reject_suggestion(self, suggestion_id: int, admin_id: int) -> None:
        suggestion = await self.suggestion_repo.get_by_id_with_user(suggestion_id)

        if not suggestion:
            raise NotFoundError("Suggestion not found.")
        if suggestion.status != "pending":
            raise ConflictError(f"Suggestion is already {suggestion.status}.")

        await self.suggestion_repo.update_status(suggestion, "rejected")

        await self.log_repo.log(
            admin_id=admin_id,
            action="reject_suggestion",
            target={
                "suggestion_id": suggestion_id,
                "book_title": suggestion.title,
                "user_name": suggestion.user.name if suggestion.user else "unknown",
            },
        )

        logger.info("Admin %s rejected suggestion %s: %r", admin_id, suggestion_id, suggestion.title)

    async def get_pending_suggestions(self) -> list[BookSuggestion]:
        return await self.suggestion_repo.get_pending()

    async def set_current_book(
        self,
        book_id: int,
        admin_id: int,
        chapter_from: int,
        chapter_to: Optional[int] = None,
        cover_image_url: Optional[str] = None,
        total_chapters: Optional[int] = None,
    ) -> Book:
        """Move a queued book to current."""
        existing_current = await self.book_repo.get_current()
        if existing_current:
            raise ConflictError(
                f"'{existing_current.title}' is already the current book. "
                "Complete it before setting a new one."
            )

        book = await self.book_repo.get_by_id(book_id)
        if not book:
            raise NotFoundError("Book not found.")
        if book.status != "queued":
            raise ValidationError("Only queued books can be set as current.")

        # Build the display string from numeric inputs
        current_chapters = _build_chapter_string(chapter_from, chapter_to)
        logger.info(
            "Admin %s setting book %s as current — assignment: %r",
            admin_id, book_id, current_chapters,
        )

        updates: dict = {
            "status": "current",
            "current_chapters": current_chapters,
        }
        if cover_image_url:
            updates["cover_image_url"] = _sanitize(cover_image_url, 500)
        if total_chapters:
            updates["total_chapters"] = total_chapters

        book = await self.book_repo.update_fields(book, **updates)

        await self.log_repo.log(
            admin_id=admin_id,
            action="set_current_book",
            target={"book_id": book_id, "book_title": book.title},
        )

        logger.info("Admin %s set book %s as current: %r", admin_id, book_id, book.title)
        return book

    async def update_current_book(
        self,
        admin_id: int,
        title: Optional[str] = None,
        pdf_url: Optional[str] = None,
        cover_image_url: Optional[str] = None,
        chapter_from: Optional[int] = None,
        chapter_to: Optional[int] = None,
        total_chapters: Optional[int] = None,
    ) -> Book:
        """Update fields on the current book. Only provided fields are changed."""
        book = await self.book_repo.get_current()
        if not book:
            raise NotFoundError("No current book is set.")

        # Track old total_chapters before any update
        old_total = book.total_chapters

        updates: dict = {}

        if title is not None:
            updates["title"] = _sanitize(title, 200)
        if pdf_url is not None:
            updates["pdf_url"] = _sanitize(pdf_url, 500)
        if cover_image_url is not None:
            updates["cover_image_url"] = _sanitize(cover_image_url, 500)
        if chapter_from is not None:
            updates["current_chapters"] = _build_chapter_string(chapter_from, chapter_to)
        if total_chapters is not None:
            updates["total_chapters"] = total_chapters

        if updates:
            book = await self.book_repo.update_fields(book, **updates)

        # If total_chapters changed (and is not None), adjust existing progress
        if total_chapters is not None and total_chapters != old_total:
            await self._adjust_user_progress_for_total_change(book.id, total_chapters)

        await self.log_repo.log(
            admin_id=admin_id,
            action="update_current_book",
            target={
                "book_id": book.id,
                "book_title": book.title,
                "fields": list(updates.keys()),
            },
        )

        logger.info("Admin %s updated current book %s: fields=%s", admin_id, book.id, list(updates.keys()))
        return book
    
    async def _adjust_user_progress_for_total_change(self, book_id: int, new_total: int) -> None:
        """
        Clamp existing progress.chapter values to the new total.
        - If chapter == -1 (completed), leave unchanged.
        - If chapter > new_total, reset to 0 (not started).
        - Otherwise, keep as is.
        """
        from app.models.reading_progress import ReadingProgress

        # Fetch all progress records for this book
        progress_records = await self.progress_repo.get_all_for_book(book_id)

        for progress in progress_records:
            if progress.chapter == -1:   # completed flag
                continue
            if progress.chapter > new_total:
                progress.chapter = 0
                self.session.add(progress)   # mark as dirty

        await self.session.commit()
        logger.info("Adjusted progress for book_id=%s: new_total=%s", book_id, new_total)

    async def complete_current_book(self, admin_id: int) -> Book:
        """Mark the current book as completed."""
        book = await self.book_repo.get_current()
        if not book:
            raise NotFoundError("No current book to complete.")

        auto_completed = await self.progress_repo.mark_all_complete_for_book(book.id)

        book = await self.book_repo.update_fields(
            book,
            status="completed",
            completed_date=datetime.now(timezone.utc),
            current_chapters=None,
        )

        await self.log_repo.log(
            admin_id=admin_id,
            action="complete_book",
            target={
                "book_id": book.id,
                "book_title": book.title,
                "auto_completed": auto_completed,
            },
        )

        logger.info(
            "Admin %s completed book %r — %s readings auto-completed",
            admin_id, book.title, auto_completed,
        )
        return book