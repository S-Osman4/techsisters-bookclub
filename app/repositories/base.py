# app/repositories/base.py
import logging
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

logger = logging.getLogger(__name__)

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    Generic async repository providing common CRUD operations.
    All entity repositories inherit from this class.

    Usage:
        class UserRepository(BaseRepository[User]):
            model = User
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, record_id: int) -> ModelT | None:
        """Return a single record by primary key, or None."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[ModelT]:
        """Return all records ordered by id descending."""
        result = await self.session.execute(
            select(self.model).order_by(self.model.id.desc())
        )
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelT:
        """
        Create and persist a new record.
        Returns the refreshed instance with DB-generated fields populated.
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()   # get DB-generated id without committing
        await self.session.refresh(instance)
        return instance

    async def delete(self, instance: ModelT) -> None:
        """Delete a record and flush."""
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self) -> int:
        """Return total row count for this model."""
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()