# app/repositories/access_code.py
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.access_code import AccessCode
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

SINGLETON_ID = 1


class AccessCodeRepository(BaseRepository[AccessCode]):
    model = AccessCode

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self) -> AccessCode | None:
        """Return the singleton access code row."""
        result = await self.session.execute(
            select(AccessCode).where(AccessCode.id == SINGLETON_ID)
        )
        return result.scalar_one_or_none()

    async def upsert(self, code: str) -> AccessCode:
        """
        Update the singleton access code if it exists, create it if not.
        Always operates on id=1.
        """
        existing = await self.get()
        if existing:
            existing.code = code.upper().strip()
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        return await self.create(
            id=SINGLETON_ID,
            code=code.upper().strip(),
        )