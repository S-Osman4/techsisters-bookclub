# app/repositories/user.py
import logging
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    model = User

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_email(self, email: str) -> User | None:
        """Return user by email address (case-insensitive)."""
        result = await self.session.execute(
            select(User).where(func.lower(User.email) == email.lower().strip())
        )
        return result.scalar_one_or_none()

    async def get_all_ordered(self) -> list[User]:
        """Return all users ordered by creation date descending."""
        result = await self.session.execute(
            select(User).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def count_admins(self) -> int:
        """Return total number of admin users."""
        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.is_admin.is_(True))
        )
        return result.scalar_one()

    async def count_new_since(self, since: datetime) -> int:
        """Return number of users registered after the given datetime."""
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(User.created_at >= since)
        )
        return result.scalar_one()

    async def email_exists(self, email: str) -> bool:
        """Return True if a user with this email already exists."""
        result = await self.session.execute(
            select(func.count())
            .select_from(User)
            .where(func.lower(User.email) == email.lower().strip())
        )
        return result.scalar_one() > 0

    async def update_name(self, user: User, new_name: str) -> User:
        """Update user display name."""
        user.name = new_name.strip()
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_password(self, user: User, new_hash: str) -> User:
        """Replace password hash."""
        user.password_hash = new_hash
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def set_admin(self, user: User, is_admin: bool) -> User:
        """Promote or demote a user."""
        user.is_admin = is_admin
        await self.session.flush()
        await self.session.refresh(user)
        return user