# app/services/feedback.py
import logging
from typing import Optional

import resend
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.feedback import Feedback
from app.repositories.feedback import FeedbackRepository

logger = logging.getLogger(__name__)


class FeedbackService:
    """Handles feedback submission and email notification."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.feedback_repo = FeedbackRepository(session)

    async def submit_feedback(
        self,
        type: str,
        message: str,
        email: Optional[str],
        user_id: Optional[int],
    ) -> Feedback:
        """
        Save feedback to database and send email notification to admin.
        Email failure does not fail the request.
        """
        feedback = await self.feedback_repo.create_feedback(
            type=type,
            message=message,
            email=email,
            user_id=user_id,
        )

        await self._send_notification(type, message, email)
        return feedback

    async def _send_notification(
        self,
        type: str,
        message: str,
        sender_email: Optional[str],
    ) -> None:
        """
        Send email notification to admin via Resend.
        Silently logs errors — never raises.
        """
        if not settings.RESEND_API_KEY or not settings.ADMIN_EMAIL:
            logger.debug("Email notification skipped — RESEND_API_KEY or ADMIN_EMAIL not set")
            return

        labels = {
            "bug": "Bug Report",
            "suggestion": "Feature Suggestion",
            "feedback": "General Feedback",
        }
        label = labels.get(type, type)
        sender = sender_email or "Anonymous"

        try:
            resend.api_key = settings.RESEND_API_KEY
            resend.Emails.send({
                "from": "TechSisters Feedback <onboarding@resend.dev>",
                "to": settings.ADMIN_EMAIL,
                "subject": f"[TechSisters] New {label} from {sender}",
                "html": (
                    f"<h2>New Feedback</h2>"
                    f"<p><strong>Type:</strong> {label}</p>"
                    f"<p><strong>From:</strong> {sender}</p>"
                    f"<p><strong>Message:</strong> {message}</p>"
                ),
            })
            logger.info("Feedback notification sent to %s", settings.ADMIN_EMAIL)
        except Exception as exc:
            logger.error("Failed to send feedback email: %s", exc)