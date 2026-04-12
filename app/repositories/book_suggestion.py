# app/repositories/book_suggestion.py
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.book_suggestion import BookSuggestion
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class BookSuggestionRepository(BaseRepository[BookSuggestion]):
    model = BookSuggestion

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_pending(self) -> list[BookSuggestion]:
        """
        Return all pending suggestions with user eagerly loaded.
        Avoids N+1 when rendering admin suggestion list.
        """
        result = await self.session.execute(
            select(BookSuggestion)
            .options(joinedload(BookSuggestion.user))
            .where(BookSuggestion.status == "pending")
            .order_by(BookSuggestion.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_user(self, user_id: int) -> list[BookSuggestion]:
        """Return all suggestions for a given user, newest first."""
        result = await self.session.execute(
            select(BookSuggestion)
            .where(BookSuggestion.user_id == user_id)
            .order_by(BookSuggestion.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id_with_user(
        self, suggestion_id: int
    ) -> BookSuggestion | None:
        """Return a suggestion with its user eagerly loaded."""
        result = await self.session.execute(
            select(BookSuggestion)
            .options(joinedload(BookSuggestion.user))
            .where(BookSuggestion.id == suggestion_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self, suggestion: BookSuggestion, status: str
    ) -> BookSuggestion:
        """Update suggestion status (approved/rejected)."""
        suggestion.status = status
        await self.session.flush()
        await self.session.refresh(suggestion)
        return suggestion