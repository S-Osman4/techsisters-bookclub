# app/api/feedback.py
import logging
import os
import resend
from html import escape

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_optional
from app.core.config import settings
from app.database import get_session
from app.models.user import User
from app.models.feedback import Feedback
from app.schemas.feedback import FeedbackCreate
from app.services.feedback import FeedbackService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Feedback"])

resend.api_key = settings.RESEND_API_KEY
ADMIN_EMAIL = settings.ADMIN_EMAIL

logger

@router.post("/feedback", response_class=HTMLResponse)
async def submit_feedback(
    request: Request,
    payload: FeedbackCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    final_email = payload.email or (current_user.email if current_user else None)

    # Save to database
    feedback = Feedback(
        type=payload.type,
        message=payload.message,
        email=final_email,
        user_id=current_user.id if current_user else None,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    # Send email notification
    if ADMIN_EMAIL and resend.api_key:
        print(f"📧 Attempting to send email to: {ADMIN_EMAIL}")
        type_labels = {
            "bug": "🐞 Bug Report",
            "suggestion": "💡 Feature Suggestion",
            "feedback": "💬 General Feedback",
        }
        label = type_labels.get(payload.type, payload.type)
        sender = final_email or "Anonymous"
        user_name = current_user.name if current_user else "Guest"

        try:
            resend.Emails.send({
                "from": "TechSisters Feedback <onboarding@resend.dev>",
                "to": ADMIN_EMAIL,
                "subject": f"[TechSisters] New {label} from {sender}",
                "html": f"""
                    <h2>New Feedback Received 💜</h2>
                    <table>
                        <tr><td><strong>Type:</strong></td><td>{escape(label)}</td></tr>
                        <tr><td><strong>From:</strong></td><td>{escape(sender)}</td></tr>
                        <tr><td><strong>User:</strong></td><td>{escape(user_name)}</td></tr>
                        <tr><td><strong>Message:</strong></td><td>{escape(payload.message)}</td></tr>
                    </table>
                """
            })
            print("✅ Email sent successfully")
        except Exception as e:
            print(f"❌ Email failed: {e}")
            logger.error(f"Failed to send feedback email: {e}")

    else:
                logger.warning("Email skipped: ADMIN_EMAIL or RESEND_API_KEY not set")

    return HTMLResponse("""
        <div class="mt-4 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
            Thank you for your feedback! 💜
        </div>
    """)