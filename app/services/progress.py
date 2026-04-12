# app/services/progress.py
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.repositories.book import BookRepository
from app.repositories.reading_progress import ReadingProgressRepository
from app.models.reading_progress import ReadingProgress
from app.schemas.progress import ChapterRangeStat, CommunityProgressResponse

logger = logging.getLogger(__name__)


def _chapter_label(chapter: int) -> str:
    """Map a chapter number to a display range label."""
    if chapter == -1:
        return "Completed"
    if chapter == 0:
        return "Not Started"
    if chapter <= 2:
        return "Chapters 1-2"
    if chapter <= 4:
        return "Chapters 3-4"
    if chapter <= 6:
        return "Chapters 5-6"
    if chapter <= 8:
        return "Chapters 7-8"
    return f"Chapter {chapter}+"


# Fixed display order for chapter range labels
_LABEL_ORDER = [
    "Not Started",
    "Chapters 1-2",
    "Chapters 3-4",
    "Chapters 5-6",
    "Chapters 7-8",
    "Completed",
]


class ProgressService:
    """Handles reading progress tracking and community stats."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.progress_repo = ReadingProgressRepository(session)
        self.book_repo = BookRepository(session)

    async def update_progress(
        self,
        user_id: int,
        book_id: int,
        chapter: int,
    ) -> ReadingProgress:
        """
        Upsert reading progress for a user/book pair.
        chapter must be >= -1 (enforced by schema before reaching here).
        """
        book = await self.book_repo.get_by_id(book_id)
        if not book:
            raise NotFoundError("Book not found.")

        if book.status == "completed" and chapter != -1:
            raise ValidationError("This book is already completed.")

        progress = await self.progress_repo.upsert(user_id, book_id, chapter)
        logger.debug(
            "Progress updated: user=%s book=%s chapter=%s",
            user_id, book_id, chapter,
        )
        return progress

    async def get_user_progress(
        self,
        user_id: int,
    ) -> ReadingProgress | None:
        """
        Return the user's progress on the current book.
        Returns None if no current book or no progress recorded.
        """
        current = await self.book_repo.get_current()
        if not current:
            return None
        return await self.progress_repo.get_by_user_and_book(user_id, current.id)

    async def get_community_stats(self) -> CommunityProgressResponse | None:
        """
        Return community reading stats for the current book.
        Returns None if no current book exists.
        """
        current = await self.book_repo.get_current()
        if not current:
            return None

        all_progress = await self.progress_repo.get_all_for_book(current.id)
        total = len(all_progress)

        if total == 0:
            return CommunityProgressResponse(
                book_id=current.id,
                book_title=current.title,
                total_readers=0,
                stats=[],
            )

        # Count members per label bucket
        bucket: dict[str, int] = {}
        for record in all_progress:
            label = _chapter_label(record.chapter)
            bucket[label] = bucket.get(label, 0) + 1

        # Build sorted stats list
        stats: list[ChapterRangeStat] = []
        for label in _LABEL_ORDER:
            if label in bucket:
                count = bucket[label]
                stats.append(
                    ChapterRangeStat(
                        label=label,
                        count=count,
                        percentage=round(count / total * 100, 1),
                    )
                )

        # Any labels not in the fixed order (e.g. "Chapter 9+") go at the end
        for label, count in bucket.items():
            if label not in _LABEL_ORDER:
                stats.append(
                    ChapterRangeStat(
                        label=label,
                        count=count,
                        percentage=round(count / total * 100, 1),
                    )
                )

        return CommunityProgressResponse(
            book_id=current.id,
            book_title=current.title,
            total_readers=total,
            stats=stats,
        )