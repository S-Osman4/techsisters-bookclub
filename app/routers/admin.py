"""
Admin API - manage code, books, suggestions, meetings
"""
from fastapi import APIRouter, Depends, Form, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import List
import secrets
import string


from app.database import get_db
from app.models import User, Book, BookSuggestion, Meeting, AccessCode, ReadingProgress, AdminAction
from app.schemas import (
    BookUpdate, MeetingUpdate, CodeUpdate, CodeResponse, MessageResponse
)
from app.dependencies import require_admin

router = APIRouter()

CODE_CHARS = string.ascii_uppercase + string.digits  # e.g. ABC123
DEFAULT_CODE_LENGTH = 8 

def generate_access_code(length: int = DEFAULT_CODE_LENGTH) -> str:
    return ''.join(secrets.choice(CODE_CHARS) for _ in range(length))


# ===== Access Code Management =====
@router.get("/code", response_model=CodeResponse)
async def get_access_code(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get current access code"""
    code = db.query(AccessCode).first()
    if not code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access code not found"
        )
    return code

@router.put("/code", response_model=MessageResponse)
async def update_access_code(
    new_code: str = Form(...), 
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update access code
    
    IMPORTANT: Post the new code in WhatsApp group after updating!
    """
    code = db.query(AccessCode).first()
    
    if not code:
        code = AccessCode(code=new_code)
        db.add(code)
    else:
        old_code = code.code
        code.code = new_code
    
    # Log the admin action
    admin_action = AdminAction(
        admin_id=admin.id,
        action="update_access_code",
        target=f"new_code={new_code}"
    )

    db.add(admin_action)
    db.commit()
    db.refresh(code)
    
    return {
        "message": f"Access code updated to: {code.code}. Remember to post it in the WhatsApp group!",
        "success": True
    }
@router.post("/code/generate", response_model=CodeResponse)
async def generate_access_code_endpoint(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Generate a new random access code and save it.
    """
    new_code = generate_access_code()

    code = db.query(AccessCode).first()
    if not code:
        code = AccessCode(code=new_code)
        db.add(code)
    else:
        code.code = new_code

    admin_action = AdminAction(
        admin_id=admin.id,
        action="update_access_code",
        target=f"new_code={new_code}",
    )
    db.add(admin_action)
    db.commit()
    db.refresh(code)

    return code


# ===== Current Book Management =====
@router.put("/books/current", response_model=MessageResponse)
async def update_current_book(
    title: str = Form(None),
    pdf_url: str = Form(None),
    cover_image_url: str = Form(None),
    current_chapters: str = Form(None),
    total_chapters: int = Form(None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update current book details"""
    current_book = db.query(Book).filter(Book.status == "current").first()
    
    if not current_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current book set. Please set a book from the queue first."
        )
    
    # Update fields if provided
    if title is not None:
        current_book.title = title.strip()
    if pdf_url is not None:
        current_book.pdf_url = pdf_url
    if cover_image_url is not None:
        current_book.cover_image_url = cover_image_url
    if current_chapters is not None:
        current_book.current_chapters = current_chapters
    if total_chapters is not None:
        current_book.total_chapters = total_chapters
    
    # Log the admin action
    admin_action = AdminAction(
        admin_id=admin.id,
        action="update_current_book",
        target=f"book_id={current_book.id}"
    )
    db.add(admin_action)

    db.commit()
    
    return {
        "message": "Current book updated successfully",
        "success": True
    }

@router.post("/books/{book_id}/set-current", response_model=MessageResponse)
async def set_current_book(
    book_id: int,
    current_chapters: str = Body(..., embed=True),
    cover_image_url: str = Body(None, embed=True),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Set a queued book as current
    
    Can only set if there's no current book
    """
    # Check if there's already a current book
    existing_current = db.query(Book).filter(Book.status == "current").first()
    if existing_current:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"There's already a current book: {existing_current.title}. Complete it first."
        )
    
    # Get the book from queue
    book = db.query(Book).filter(
        Book.id == book_id,
        Book.status == "queued"
    ).first()
    
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found in queue"
        )
    
    # Set as current
    book.status = "current"
    book.current_chapters = current_chapters
    if cover_image_url:
        book.cover_image_url = cover_image_url
    
    # Log the admin action  ← ADD THIS
    admin_action = AdminAction(
        admin_id=admin.id,
        action="set_current_book",
        target=f"book_id={book_id}, title={book.title}"
    )
    db.add(admin_action)

    db.commit()
    
    return {
        "message": f"'{book.title}' is now the current book",
        "success": True
    }

@router.post("/books/complete", response_model=MessageResponse)
async def complete_current_book(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Mark current book as completed
    
    AUTO-COMPLETES all in-progress readings (chapter > 0 but not -1)
    to prevent orphaned "reading" states in past books
    """
    current_book = db.query(Book).filter(Book.status == "current").first()
    
    if not current_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current book to complete"
        )
    
    # AUTO-FIX: Mark all incomplete progress as completed (-1)
    # Only affects users who started but didn't mark as complete
    incomplete_progress = db.query(ReadingProgress).filter(
        ReadingProgress.book_id == current_book.id,
        ReadingProgress.chapter > 0,  # Started reading
        ReadingProgress.chapter != -1  # But not completed
    ).all()
    
    auto_completed_count = 0
    for progress in incomplete_progress:
        progress.chapter = -1  # Mark as completed
        auto_completed_count += 1
    
    # Update book status
    current_book.status = "completed"
    current_book.completed_date = datetime.utcnow()
    current_book.current_chapters = None
    
    # Log the admin action
    admin_action = AdminAction(
        admin_id=admin.id,
        action="complete_book",
        target=f"book_id={current_book.id}, title={current_book.title}, auto_completed={auto_completed_count}"
    )
    db.add(admin_action)
    
    db.commit()
    
    message = f"'{current_book.title}' marked as completed."
    if auto_completed_count > 0:
        message += f" {auto_completed_count} in-progress readings auto-completed."
    
    return {
        "message": message,
        "success": True
    }

# ===== Meeting Management =====
@router.get("/meeting")
async def get_meeting(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get current meeting details"""
    meeting = db.query(Meeting).first()
    return meeting

@router.put("/meeting", response_model=MessageResponse)
async def update_meeting(
    start_at_local: str = Form(...),   # "2025-01-10T18:30"
    timezone: str = Form(...),         # "Europe/London"
    meet_link: str = Form(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
   # Parse naive local datetime from input
    try:
        naive = datetime.strptime(start_at_local, "%Y-%m-%dT%H:%M")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid datetime format. Use the datetime picker input.",
        )

    # Attach timezone and convert to UTC
    try:
        local_tz = ZoneInfo(timezone)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timezone identifier.",
        )

    local_dt = naive.replace(tzinfo=local_tz)
    start_at_utc = local_dt.astimezone(ZoneInfo("UTC"))

    meeting = db.query(Meeting).first()
    if not meeting:
        meeting = Meeting(
            start_at=start_at_utc,
            meet_link=meet_link,
        )
        db.add(meeting)
    else:
        meeting.start_at = start_at_utc
        meeting.meet_link = meet_link

    adminaction = AdminAction(
        admin_id=admin.id,
        action="updatemeeting",
        target=f"start_at={local_dt.isoformat()}, tz={timezone}",
    )
    db.add(adminaction)
    db.commit()

    return {"message": "Meeting updated successfully", "success": True}

# ===== Book Suggestions Management =====
@router.get("/suggestions/pending")
async def get_pending_suggestions(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all pending book suggestions with user info"""
    suggestions = db.query(BookSuggestion, User).join(User).filter(
        BookSuggestion.status == "pending"
    ).order_by(BookSuggestion.created_at).all()
    
    result = []
    for suggestion, user in suggestions:
        result.append({
            "id": suggestion.id,
            "title": suggestion.title,
            "pdf_url": suggestion.pdf_url,
            "status": suggestion.status,
            "user_id": suggestion.user_id,
            "user_name": user.name,
            "user_email": user.email,
            "created_at": suggestion.created_at
        })
    
    return result

@router.put("/suggestions/{suggestion_id}/approve", response_model=MessageResponse)
async def approve_suggestion(
    suggestion_id: int,
    cover_image_url: str = Form(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Approve a book suggestion
    
    Adds book to the queue for future reading
    """
    suggestion = db.query(BookSuggestion).filter(
        BookSuggestion.id == suggestion_id
    ).first()
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    
    if suggestion.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Suggestion is already {suggestion.status}"
        )
    
    if not cover_image_url.strip():
        raise HTTPException(
            status_code=400,
            detail="Cover image is required to approve a book"
        )
    
    # Update status
    suggestion.status = "approved"
    
    # Create book in queue

    new_book = Book(
        title=suggestion.title,
        pdf_url=suggestion.pdf_url,
        cover_image_url=cover_image_url.strip(),
        status="queued"
    )

    db.add(new_book)

    # Log the admin action
    admin_action = AdminAction(
        admin_id=admin.id,
        action="approve_suggestion",
        target=f"suggestion_id={suggestion.id}"
    )
    db.add(admin_action)
    
    db.commit()

    # After approval, get updated lists

    
    return {
        "message": f"'{suggestion.title}' approved and added to queue",
        "success": True
    }


@router.put("/suggestions/{suggestion_id}/reject", response_model=MessageResponse)
async def reject_suggestion(
    suggestion_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Reject a book suggestion"""
    suggestion = db.query(BookSuggestion).filter(
        BookSuggestion.id == suggestion_id
    ).first()
    
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )
    
    if suggestion.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Suggestion is already {suggestion.status}"
        )
    
    suggestion.status = "rejected"
    # Log the admin action
    admin_action = AdminAction(
        admin_id=admin.id,
        action="reject_suggestion",
        target=f"suggestion_id={suggestion.id}"
    )
    db.add(admin_action)
    db.commit()
    
    return {
        "message": f"Suggestion rejected",
        "success": True
    }

# ===== Admin Stats =====
@router.get("/stats")
async def get_admin_stats(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get admin dashboard statistics"""
    
    # Total members
    total_members = db.query(func.count(User.id)).scalar()
    
    # New members this month
    first_day_of_month = datetime.utcnow().replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    new_members_this_month = db.query(func.count(User.id)).filter(
        User.created_at >= first_day_of_month
    ).scalar()
    
    # Pending suggestions
    pending_suggestions = db.query(func.count(BookSuggestion.id)).filter(
        BookSuggestion.status == "pending"
    ).scalar()
    
    # Current book engagement
    current_book = db.query(Book).filter(Book.status == "current").first()
    engagement = {
        "tracking_progress": 0,
        "average_chapter": 0,
        "book_title": None
    }
    
    if current_book:
        progress_count = db.query(func.count(ReadingProgress.id)).filter(
            ReadingProgress.book_id == current_book.id
        ).scalar()
        
        avg_chapter = db.query(func.avg(ReadingProgress.chapter)).filter(
            ReadingProgress.book_id == current_book.id,
            ReadingProgress.chapter > 0  # Exclude "not started"
        ).scalar()
        
        engagement["tracking_progress"] = progress_count or 0
        engagement["average_chapter"] = round(float(avg_chapter) if avg_chapter else 0, 1)
        engagement["book_title"] = current_book.title
    
    return {
        "total_members": total_members,
        "new_members_this_month": new_members_this_month,
        "pending_suggestions": pending_suggestions,
        "current_book_engagement": engagement
    }

 # ===== Admin User Management =====

@router.get("/users")
async def get_all_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all users with their roles"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": user.is_admin,
            "created_at": user.created_at
        })
    
    return result


@router.put("/users/{user_id}/promote", response_model=MessageResponse)
async def promote_to_admin(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Promote a user to admin"""
    
    # Get the user to promote
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{user.name} is already an admin"
        )
    
    # Promote user
    user.is_admin = True
    
    # Log the action
    admin_action = AdminAction(
        admin_id=admin.id,
        action="promote_admin",
        target=f"user_id={user.id}, email={user.email}"
    )
    db.add(admin_action)
    
    db.commit()
    
    return {
        "message": f"✅ {user.name} has been promoted to admin",
        "success": True
    }


@router.put("/users/{user_id}/demote", response_model=MessageResponse)
async def demote_from_admin(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Demote an admin to regular user"""
    
    # Prevent self-demotion
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot demote yourself. Ask another admin to do this."
        )
    
    # Get the user to demote
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{user.name} is not an admin"
        )
    
    # Check if this is the last admin
    admin_count = db.query(func.count(User.id)).filter(User.is_admin == True).scalar()
    
    if admin_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote the last admin. Promote another user to admin first."
        )
    
    # Demote user
    user.is_admin = False
    
    # Log the action
    admin_action = AdminAction(
        admin_id=admin.id,
        action="demote_admin",
        target=f"user_id={user.id}, email={user.email}"
    )
    db.add(admin_action)
    
    db.commit()
    
    return {
        "message": f"⚠️ {user.name} has been demoted to regular member",
        "success": True
    }   