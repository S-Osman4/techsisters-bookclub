# app/models/access_code.py
from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utcnow


class AccessCode(Base):
    """
    Singleton table — exactly one row with id=1 always exists.
    Application logic enforces this; the seed script creates it.
    Never insert a second row.
    """
    __tablename__ = "access_codes"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AccessCode code={self.code!r}>"