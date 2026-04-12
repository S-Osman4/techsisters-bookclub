# app/models/admin_action.py
from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class AdminAction(Base, TimestampMixin):
    """
    Audit log for all admin operations.

    target column stores a JSON string — always use
    json.dumps() before saving and json.loads() after reading.
    """
    __tablename__ = "admin_actions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    admin_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # e.g. "approve_suggestion", "set_current_book", "promote_user"
    action: Mapped[str] = mapped_column(String(100), nullable=False)

    # JSON string — use json.dumps/json.loads
    target: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────────────
    admin: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="admin_actions",
        lazy="noload",
    )

    # ── Indexes ──────────────────────────────────────────────────────────────
    __table_args__ = (
        Index("ix_admin_actions_admin_id", "admin_id"),
    )

    def __repr__(self) -> str:
        return f"<AdminAction id={self.id} action={self.action!r}>"