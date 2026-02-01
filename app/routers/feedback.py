from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user_optional
from app.models import User, Feedback

api_router = APIRouter(prefix="/api")


@api_router.post("/feedback", response_class=HTMLResponse)
async def submit_feedback(
    request: Request,
    type: str = Form(...),
    message: str = Form(...),
    email: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    # derive final email
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
    db.refresh(feedback)  # optional, but nice if you later need id/timestamp[web:19]

    # Simple success snippet for HTMX
    return """
    <div class="mt-4 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
      Thank you for your feedback! 💜
    </div>
    """