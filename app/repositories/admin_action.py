# app/repositories/admin_action.py
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.admin_action import AdminAction
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AdminActionRepository(BaseRepository[AdminAction]):
    model = AdminAction

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def log(
        self,
        admin_id: int,
        action: str,
        target: dict[str, Any] | None = None,
    ) -> AdminAction:
        """
        Write an audit log entry.
        target dict is serialised to JSON string before storage.
        """
        return await self.create(
            admin_id=admin_id,
            action=action,
            target=json.dumps(target) if target else None,
        )

    async def get_recent(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[AdminAction], int]:
        """
        Return recent admin actions with admin user eagerly loaded.
        Returns (records, total_count).
        """
        from sqlalchemy import func

        total_result = await self.session.execute(
            select(func.count()).select_from(AdminAction)
        )
        total = total_result.scalar_one()

        result = await self.session.execute(
            select(AdminAction)
            .options(joinedload(AdminAction.admin))
            .order_by(AdminAction.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total