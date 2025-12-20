"""
Books API - current book, queue, past books, suggestions, progress
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.params import Form
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.database import get_db
from app.models import Book, Meeting, BookSuggestion, ReadingProgress, User
from app.schemas import (
    BookResponse, SuggestionCreate, SuggestionResponse, 
    ProgressUpdate, ProgressResponse, MessageResponse, SuggestionUpdate
)
from app.dependencies import (
    get_current_user, get_current_user_optional, 
    require_code_verified
)

router = APIRouter()

# ===== Current Book & Meeting =====
@router.get("/current")
async def get_current_book(
    db: Session = Depends(get_db),
    _: bool = Depends(require_code_verified)
):
    """
    Get current book being read and next meeting details
    
    Accessible to both guests (with code) and members
    """
    current_book = db.query(Book).filter(Book.status == "current").first()
    meeting = db.query(Meeting).first()
    
    return {
        "book": current_book,
        "meeting": meeting
    }

# ===== Upcoming Books (Queue) =====
@router.get("/queue", response_model=List[BookResponse])
async def get_queued_books(
    db: Session = Depends(get_db),
    _: bool = Depends(require_code_verified)
):
    """
    Get approved books waiting to be read
    
    Books are returned in FIFO order (oldest first)
    """
    books = db.query(Book).filter(
        Book.status == "queued"
    ).order_by(Book.created_at).all()
    
    return books

# ===== Past Books =====
@router.get("/past", response_model=List[BookResponse])
async def get_past_books(
    db: Session = Depends(get_db),
    _: bool = Depends(require_code_verified)
):
    """
    Get completed books with PDFs available for download
    
    Returns most recent first
    """
    books = db.query(Book).filter(
        Book.status == "completed"
    ).order_by(Book.completed_date.desc()).all()
    
    return books

# ===== Book Suggestions =====
@router.post("/suggestions", response_model=SuggestionResponse)
async def create_suggestion(
    title: str = Form(...),
    pdf_url: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a book suggestion (members only)
    
    Suggestions go to pending status and require admin approval
    """
      # Validate using schema
    suggestion_data = SuggestionCreate(title=title, pdf_url=pdf_url)
    
    new_suggestion = BookSuggestion(
        title=suggestion_data.title.strip(),
        pdf_url=suggestion_data.pdf_url,
        user_id=current_user.id,
        status="pending"
    )
    
    db.add(new_suggestion)
    db.commit()
    db.refresh(new_suggestion)
    
    return new_suggestion

@router.get("/suggestions/my", response_model=List[SuggestionResponse])
async def get_my_suggestions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's book suggestions with status
    
    Shows pending, approved, and rejected suggestions
    """
    suggestions = db.query(BookSuggestion).filter(
        BookSuggestion.user_id == current_user.id
    ).order_by(BookSuggestion.created_at.desc()).all()
    
    return suggestions

# ===== Reading Progress =====
@router.put("/progress", response_model=ProgressResponse)
async def update_progress(
    book_id: int = Form(...),
    chapter: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update reading progress for a book
    
    Chapter values:
    - 0 = not started
    - 1+ = current chapter
    - -1 = completed
    """
      # Validate using schema
    progress_data = ProgressUpdate(book_id=book_id, chapter=chapter)
    
    # Verify book exists
    book = db.query(Book).filter(Book.id == progress_data.book_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found"
        )
   
       # Find existing progress
    existing = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.book_id == progress_data.book_id
    ).first()
    
    if existing:
        existing.chapter = progress_data.chapter
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_progress = ReadingProgress(
            user_id=current_user.id,
            book_id=progress_data.book_id,
            chapter=progress_data.chapter
        )
        db.add(new_progress)
        db.commit()
        db.refresh(new_progress)
        return new_progress
    

@router.get("/progress/my")
async def get_my_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's reading progress for current book
    """
    current_book = db.query(Book).filter(Book.status == "current").first()
    
    if not current_book:
        return {"progress": None, "book": None}
    
    progress = db.query(ReadingProgress).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.book_id == current_book.id
    ).first()
    
    return {
        "progress": progress,
        "book": current_book
    }

@router.get("/progress/community")
async def get_community_progress(
    db: Session = Depends(get_db),
    _: bool = Depends(require_code_verified)
):
    """
    Get community reading progress statistics for current book
    
    Returns breakdown by chapter ranges with percentages
    """
    current_book = db.query(Book).filter(Book.status == "current").first()
    
    if not current_book:
        return {
            "stats": [],
            "total_members": 0,
            "book": None
        }
    
    # Get all progress for current book
    all_progress = db.query(ReadingProgress).filter(
        ReadingProgress.book_id == current_book.id
    ).all()
    
    total_members = len(all_progress)
    
    if total_members == 0:
        return {
            "stats": [],
            "total_members": 0,
            "book": current_book
        }
    
    # Group by chapter ranges
    stats = {}
    for progress in all_progress:
        chapter = progress.chapter
        
        if chapter == -1:
            key = "Completed"
        elif chapter == 0:
            key = "Not Started"
        elif chapter <= 2:
            key = "Chapters 1-2"
        elif chapter <= 4:
            key = "Chapters 3-4"
        elif chapter <= 6:
            key = "Chapters 5-6"
        elif chapter <= 8:
            key = "Chapters 7-8"
        else:
            key = f"Chapter {chapter}+"
        
        stats[key] = stats.get(key, 0) + 1
    
    # Calculate percentages
    result = []
    for range_name, count in stats.items():
        percentage = (count / total_members * 100) if total_members > 0 else 0
        result.append({
            "chapter_range": range_name,
            "member_count": count,
            "percentage": round(percentage, 1)
        })
    
    # Sort by chapter order
    order = ["Not Started", "Chapters 1-2", "Chapters 3-4", "Chapters 5-6", "Chapters 7-8", "Completed"]
    result.sort(key=lambda x: order.index(x["chapter_range"]) if x["chapter_range"] in order else 999)
    
    return {
        "stats": result,
        "total_members": total_members,
        "book": current_book
    }