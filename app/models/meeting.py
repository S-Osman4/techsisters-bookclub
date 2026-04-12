# app/models/meeting.py
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class Meeting(Base):
    """
    Singleton table — exactly one row with id=1 always exists.
    MeetingService always updates this row, never inserts a new one.
    """
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    start_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    meet_link: Mapped[str] = mapped_column(String(500), nullable=False)
    is_cancelled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    cancellation_note: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Meeting start_at={self.start_at!r} cancelled={self.is_cancelled}>"