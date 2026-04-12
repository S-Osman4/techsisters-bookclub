# app/repositories/meeting.py
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

SINGLETON_ID = 1


class MeetingRepository(BaseRepository[Meeting]):
    model = Meeting

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get(self) -> Meeting | None:
        """Return the singleton meeting row."""
        result = await self.session.execute(
            select(Meeting).where(Meeting.id == SINGLETON_ID)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        start_at: datetime,
        meet_link: str,
        is_cancelled: bool = False,
        cancellation_note: Optional[str] = None,
    ) -> Meeting:
        """
        Update the singleton meeting row if it exists, create if not.
        Always operates on id=1.
        """
        meeting = await self.get()
        if meeting:
            meeting.start_at = start_at
            meeting.meet_link = meet_link
            meeting.is_cancelled = is_cancelled
            meeting.cancellation_note = cancellation_note
            await self.session.flush()
            await self.session.refresh(meeting)
            return meeting

        return await self.create(
            id=SINGLETON_ID,
            start_at=start_at,
            meet_link=meet_link,
            is_cancelled=is_cancelled,
            cancellation_note=cancellation_note,
        )