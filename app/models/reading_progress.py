# app/models/reading_progress.py
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UpdatedAtMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.book import Book



class ReadingProgress(Base, UpdatedAtMixin):
    """
    Tracks a user's progress through a book.

    chapter values:
        0  = not started
        1+ = current chapter number
       -1  = completed
    """
    __tablename__ = "reading_progress"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
    )
    # 0 = not started, -1 = completed, 1+ = chapter number
    chapter: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Relationships ────────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User",
        back_populates="reading_progress",
        lazy="noload",
    )
    book: Mapped["Book"] = relationship(
        "Book",
        back_populates="reading_progress",
        lazy="noload",
    )

    # ── Constraints & indexes ────────────────────────────────────────────────
    __table_args__ = (
        UniqueConstraint("user_id", "book_id", name="uq_progress_user_book"),
        Index("ix_reading_progress_user_id", "user_id"),
        Index("ix_reading_progress_book_id", "book_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ReadingProgress user_id={self.user_id} "
            f"book_id={self.book_id} chapter={self.chapter}>"
        )