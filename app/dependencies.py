"""
Authentication and authorization dependencies
"""
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional
import os

from app.database import get_db
from app.models import User

# ===== Session-based Authentication =====

def get_session_user_id(request: Request) -> Optional[int]:
    """Get user ID from session cookie"""
    return request.session.get("user_id")

def get_code_verified(request: Request) -> bool:
    """Check if access code is verified"""
    return request.session.get("code_verified", False) or request.session.get("user_id") is not None

# ===== Dependencies =====

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from session.
    Raises 401 if not authenticated.
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login."
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Clear invalid session
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please login again."
        )
    
    return user

async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise return None.
    Useful for pages that work for both guests and members.
    """
    user_id = request.session.get("user_id")
    
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    return user

async def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure current user is an admin.
    Raises 403 if not admin.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_code_verified(request: Request):
    """
    Ensure access code is verified OR user is logged in.
    Raises 403 if neither condition is met.
    """
    code_verified = request.session.get("code_verified", False)
    user_id = request.session.get("user_id")
    
    if not code_verified and not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access code verification required. Please enter the access code."
        )
    
    return True