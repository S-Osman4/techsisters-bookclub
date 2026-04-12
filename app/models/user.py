# app/models/user.py
from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.book_suggestion import BookSuggestion
    from app.models.reading_progress import ReadingProgress
    from app.models.feedback import Feedback
    from app.models.admin_action import AdminAction


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    suggestions: Mapped[list[BookSuggestion]] = relationship(
        "BookSuggestion",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    reading_progress: Mapped[list[ReadingProgress]] = relationship(
        "ReadingProgress",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    feedback: Mapped[list[Feedback]] = relationship(
        "Feedback",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    admin_actions: Mapped[list[AdminAction]] = relationship(
        "AdminAction",
        back_populates="admin",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    __table_args__ = (
        Index("ix_users_email", "email"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"