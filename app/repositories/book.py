# app/repositories/book.py
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class BookRepository(BaseRepository[Book]):
    model = Book

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_current(self) -> Book | None:
        """Return the single book with status='current', or None."""
        result = await self.session.execute(
            select(Book).where(Book.status == "current")
        )
        return result.scalar_one_or_none()

    async def get_queue(self) -> list[Book]:
        """Return queued books oldest first (FIFO reading order)."""
        result = await self.session.execute(
            select(Book)
            .where(Book.status == "queued")
            .order_by(Book.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_past(self) -> list[Book]:
        """Return completed books most recent first."""
        result = await self.session.execute(
            select(Book)
            .where(Book.status == "completed")
            .order_by(Book.completed_date.desc())
        )
        return list(result.scalars().all())

    async def get_past_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ) -> tuple[list[Book], int]:
        """
        Return paginated past books with optional title search.
        Returns (books, total_count).
        """
        query = select(Book).where(Book.status == "completed")

        if search:
            query = query.where(Book.title.ilike(f"%{search}%"))

        # Total count
        from sqlalchemy import func
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        # Paginated results
        query = (
            query
            .order_by(Book.completed_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def get_queue_paginated(
        self,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
    ) -> tuple[list[Book], int]:
        """
        Return paginated queued books with optional title search.
        Returns (books, total_count).
        """
        query = select(Book).where(Book.status == "queued")

        if search:
            query = query.where(Book.title.ilike(f"%{search}%"))

        from sqlalchemy import func
        count_result = await self.session.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar_one()

        query = (
            query
            .order_by(Book.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all()), total

    async def update_fields(self, book: Book, **kwargs) -> Book:
        """Update arbitrary fields on a book instance."""
        for field, value in kwargs.items():
            setattr(book, field, value)
        await self.session.flush()
        await self.session.refresh(book)
        return book