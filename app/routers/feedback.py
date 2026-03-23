from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import resend
import os
import logging

from app.database import get_db
from app.dependencies import get_current_user_optional
from app.models import User, Feedback
from html import escape

logger = logging.getLogger(__name__)
api_router = APIRouter(prefix="/api")

resend.api_key = os.getenv("RESEND_API_KEY")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")


@api_router.post("/feedback", response_class=HTMLResponse)
async def submit_feedback(
    request: Request,
    type: str = Form(...),
    message: str = Form(...),
    email: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    final_email = email or (current_user.email if current_user else None)

    # Persist to DB
    feedback = Feedback(
        type=type,
        message=message,
        email=final_email,
        user_id=current_user.id if current_user else None,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    # Send email notification
    if ADMIN_EMAIL and resend.api_key:
        type_labels = {
            "bug": "🐞 Bug Report",
            "suggestion": "💡 Feature Suggestion",
            "feedback": "💬 General Feedback",
        }
        label = type_labels.get(type, type)
        sender = final_email or "Anonymous"

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
                        <tr><td><strong>User:</strong></td><td>{escape(current_user.name if current_user else 'Guest')}</td></tr>
                        <tr><td><strong>Message:</strong></td><td>{escape(message)}</td></tr>
                    </table>
                """
            })
        except Exception as e:
            # Don't fail the request if email fails
            logger.error(f"Failed to send feedback email: {e}")

    return """
    <div class="mt-4 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
      Thank you for your feedback! 💜
    </div>
    """