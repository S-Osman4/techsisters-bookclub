# app/models/book_suggestion.py
from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class BookSuggestion(Base, TimestampMixin):
    __tablename__ = "book_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    pdf_url: Mapped[str] = mapped_column(String(500), nullable=False)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    user: Mapped[User] = relationship(
        "User",
        back_populates="suggestions",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_book_suggestions_status", "status"),
        Index("ix_book_suggestions_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<BookSuggestion id={self.id} title={self.title!r} status={self.status!r}>"