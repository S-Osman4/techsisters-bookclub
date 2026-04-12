# app/services/meeting.py
import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.models.meeting import Meeting
from app.repositories.admin_action import AdminActionRepository
from app.repositories.meeting import MeetingRepository

logger = logging.getLogger(__name__)


class MeetingService:
    """Manages the single meeting record."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.meeting_repo = MeetingRepository(session)
        self.log_repo = AdminActionRepository(session)

    async def get_meeting(self) -> Meeting | None:
        """Return the current meeting details, or None."""
        return await self.meeting_repo.get()

    async def update_meeting(
        self,
        start_at_local: str,
        timezone: str,
        meet_link: str,
        admin_id: int,
        is_cancelled: bool = False,
        cancellation_note: Optional[str] = None,
    ) -> Meeting:
        """
        Parse local datetime + timezone, convert to UTC, save.
        Handles cancellation state alongside time/link updates.
        """
        try:
            local_tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            raise ValidationError(f"Unknown timezone: {timezone!r}")

        try:
            naive_dt = datetime.strptime(start_at_local, "%Y-%m-%dT%H:%M")
        except ValueError:
            raise ValidationError(
                "Invalid datetime format. Expected: YYYY-MM-DDTHH:MM"
            )

        local_dt = naive_dt.replace(tzinfo=local_tz)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))

        meeting = await self.meeting_repo.upsert(
            start_at=utc_dt,
            meet_link=meet_link,
            is_cancelled=is_cancelled,
            cancellation_note=cancellation_note if is_cancelled else None,
        )

        await self.log_repo.log(
            admin_id=admin_id,
            action="update_meeting",
            target={
                "start_at": local_dt.isoformat(),
                "timezone": timezone,
                "meet_link": meet_link,
                "is_cancelled": is_cancelled,
            },
        )

        logger.info(
            "Admin %s updated meeting — cancelled=%s", admin_id, is_cancelled
        )
        return meeting