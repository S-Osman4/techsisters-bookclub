"""
Admin API - manage code, books, suggestions, meetings
"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from typing import List

from app.database import get_db
from app.models import User, Book, BookSuggestion, Meeting, AccessCode, ReadingProgress
from app.schemas import (
    BookUpdate, MeetingUpdate, CodeUpdate, CodeResponse, MessageResponse
)
from app.dependencies import require_admin

router = APIRouter()

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
    code_data: CodeUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update access code
    
    IMPORTANT: Post the new code in WhatsApp group after updating!
    """
    code = db.query(AccessCode).first()
    
    if not code:
        # Create new if doesn't exist
        code = AccessCode(code=code_data.new_code)
        db.add(code)
    else:
        code.code = code_data.new_code
    
    db.commit()
    db.refresh(code)
    
    return {
        "message": f"Access code updated to: {code.code}. Remember to post it in the WhatsApp group!",
        "success": True
    }

# ===== Current Book Management =====
@router.put("/books/current", response_model=MessageResponse)
async def update_current_book(
    title: str = Body(None),
    pdf_url: str = Body(None),
    current_chapters: str = Body(None),
    total_chapters: int = Body(None),
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
    if title:
        current_book.title = title.strip()
    if pdf_url:
        current_book.pdf_url = pdf_url
    if current_chapters:
        current_book.current_chapters = current_chapters
    if total_chapters is not None:
        current_book.total_chapters = total_chapters
    
    db.commit()
    
    return {
        "message": "Current book updated successfully",
        "success": True
    }

@router.post("/books/{book_id}/set-current", response_model=MessageResponse)
async def set_current_book(
    book_id: int,
    current_chapters: str = Body(..., embed=True),
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
    
    Moves book to past books archive
    """
    current_book = db.query(Book).filter(Book.status == "current").first()
    
    if not current_book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current book to complete"
        )
    
    # Update status
    current_book.status = "completed"
    current_book.completed_date = datetime.utcnow()
    current_book.current_chapters = None
    
    db.commit()
    
    return {
        "message": f"'{current_book.title}' marked as completed. You can now set a new current book.",
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
    meeting_data: MeetingUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update meeting details"""
    meeting = db.query(Meeting).first()
    
    if not meeting:
        # Create new if doesn't exist
        meeting = Meeting(
            date=meeting_data.date,
            time=meeting_data.time,
            meet_link=meeting_data.meet_link
        )
        db.add(meeting)
    else:
        meeting.date = meeting_data.date
        meeting.time = meeting_data.time
        meeting.meet_link = meeting_data.meet_link
    
    db.commit()
    
    return {
        "message": "Meeting updated successfully",
        "success": True
    }

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
    
    # Update status
    suggestion.status = "approved"
    
    # Create book in queue
    new_book = Book(
        title=suggestion.title,
        pdf_url=suggestion.pdf_url,
        status="queued"
    )
    db.add(new_book)
    
    db.commit()
    
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