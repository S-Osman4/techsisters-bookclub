# app/repositories/feedback.py
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback import Feedback
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class FeedbackRepository(BaseRepository[Feedback]):
    model = Feedback

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def create_feedback(
        self,
        type: str,
        message: str,
        email: Optional[str],
        user_id: Optional[int],
    ) -> Feedback:
        """Create a feedback record."""
        return await self.create(
            type=type,
            message=message,
            email=email,
            user_id=user_id,
        )