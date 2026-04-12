# app/models/base.py
from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, mapped_column, MappedColumn


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """
    Shared declarative base for all models.
    All models inherit created_at automatically via the mixin below.
    """
    pass


class TimestampMixin:
    """
    Adds created_at to any model that inherits it.
    Use UpdatedAtMixin for tables that also need updated_at.
    """
    created_at: MappedColumn[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


class UpdatedAtMixin(TimestampMixin):
    """
    Adds created_at + updated_at to any model that inherits it.
    """
    updated_at: MappedColumn[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )