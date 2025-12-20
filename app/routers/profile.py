"""
User profile management routes
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import User, BookSuggestion, ReadingProgress
from app.schemas import MessageResponse
from app.dependencies import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's reading statistics"""
    
    # Count suggestions
    total_suggestions = db.query(func.count(BookSuggestion.id)).filter(
        BookSuggestion.user_id == current_user.id
    ).scalar()
    
    approved_suggestions = db.query(func.count(BookSuggestion.id)).filter(
        BookSuggestion.user_id == current_user.id,
        BookSuggestion.status == "approved"
    ).scalar()
    
    # Count completed books
    completed_books = db.query(func.count(ReadingProgress.id)).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.chapter == -1
    ).scalar()
    
    # Get current reading
    currently_reading = db.query(func.count(ReadingProgress.id)).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.chapter > 0
    ).scalar()
    
    return {
        "total_suggestions": total_suggestions or 0,
        "approved_suggestions": approved_suggestions or 0,
        "completed_books": completed_books or 0,
        "currently_reading": currently_reading or 0,
        "member_since": current_user.created_at
    }


@router.put("/name", response_model=MessageResponse)
async def update_name(
    request: Request,
    new_name: str = Form(..., min_length=2, max_length=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's name"""
    old_name = current_user.name
    current_user.name = new_name.strip()
    db.commit()
    db.refresh(current_user)
    
    # Update session
    # Note: We'll handle session update in the frontend via reload
    request.session["user_name"] = current_user.name

    # ← ADD: Verify database update
    db_user = db.query(User).filter(User.id == current_user.id).first()
    if db_user.name != new_name.strip():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update name in database"
        )
    
    return {
        "message": f"Name updated from '{old_name}' to '{current_user.name}'",
        "success": True
    }

@router.put("/password", response_model=MessageResponse)
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(..., min_length=8, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user's password"""
    
    # Verify current password
    if not current_user.verify_password(current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = User.hash_password(new_password)
    db.commit()
    db.refresh(current_user) 
    
    # Verify database update
    db_user = db.query(User).filter(User.id == current_user.id).first()
    if not db_user.verify_password(new_password):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password in database"
        )
    
    # Clear session (force re-login)
    request.session.clear()
    
    return {
        "message": "Password changed successfully. Logging out for security...",
        "success": True
    }


@router.delete("/account", response_model=MessageResponse)
async def delete_account(
    password: str = Form(...),
    confirmation: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user account (requires password confirmation)"""
    
    # Check if user is an admin
    if current_user.is_admin:
        # Count total admins
        admin_count = db.query(func.count(User.id)).filter(User.is_admin == True).scalar()
        
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete account. You are the only admin. Please assign another admin first or contact support."
            )
    
    # Verify password
    if not current_user.verify_password(password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect"
        )
    
    # Check confirmation text
    if confirmation.lower() != "delete my account":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please type 'delete my account' exactly to confirm"
        )
    
    # Delete user (cascade will handle related records)
    db.delete(current_user)
    db.commit()
    
    return {
        "message": "Account deleted successfully. You will be redirected to the home page.",
        "success": True
    }