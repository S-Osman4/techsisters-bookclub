# app/models/book.py
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UpdatedAtMixin

if TYPE_CHECKING:
    from app.models.reading_progress import ReadingProgress


class Book(Base, UpdatedAtMixin):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    pdf_url: Mapped[str] = mapped_column(String(500), nullable=False)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    total_chapters: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # current | queued | completed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")

    # Only populated when status == "current".
    # Built from chapter_from / chapter_to inputs in the service layer.
    # e.g. "Chapter 2" or "Chapters 1–3"
    current_chapters: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Populated when status == "completed"
    completed_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ────────────────────────────────────────────────────────
    reading_progress: Mapped[list["ReadingProgress"]] = relationship(
        "ReadingProgress",
        back_populates="book",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_books_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Book id={self.id} title={self.title!r} status={self.status!r}>"