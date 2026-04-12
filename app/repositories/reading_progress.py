# app/repositories/reading_progress.py
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reading_progress import ReadingProgress
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ReadingProgressRepository(BaseRepository[ReadingProgress]):
    model = ReadingProgress

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_user_and_book(
        self, user_id: int, book_id: int
    ) -> ReadingProgress | None:
        """Return progress record for a specific user+book pair."""
        result = await self.session.execute(
            select(ReadingProgress).where(
                ReadingProgress.user_id == user_id,
                ReadingProgress.book_id == book_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all_for_book(self, book_id: int) -> list[ReadingProgress]:
        """Return all progress records for a book."""
        result = await self.session.execute(
            select(ReadingProgress).where(ReadingProgress.book_id == book_id)
        )
        return list(result.scalars().all())

    async def upsert(
        self, user_id: int, book_id: int, chapter: int
    ) -> ReadingProgress:
        """
        Update chapter if record exists, create it if not.
        Returns the final record either way.
        """
        existing = await self.get_by_user_and_book(user_id, book_id)
        if existing:
            existing.chapter = chapter
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        return await self.create(
            user_id=user_id,
            book_id=book_id,
            chapter=chapter,
        )

    async def mark_all_complete_for_book(self, book_id: int) -> int:
        """
        Set chapter=-1 for all in-progress records on a book.
        Called when admin marks a book as completed.
        Returns the number of records updated.
        """
        records = await self.session.execute(
            select(ReadingProgress).where(
                ReadingProgress.book_id == book_id,
                ReadingProgress.chapter > 0,
                ReadingProgress.chapter != -1,
            )
        )
        rows = list(records.scalars().all())
        for record in rows:
            record.chapter = -1
        await self.session.flush()
        return len(rows)

    async def count_tracking(self, book_id: int) -> int:
        """Return number of users tracking a book (any chapter set)."""
        from sqlalchemy import func
        result = await self.session.execute(
            select(func.count())
            .select_from(ReadingProgress)
            .where(ReadingProgress.book_id == book_id)
        )
        return result.scalar_one()