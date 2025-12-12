"""
Authentication routes - login, register, code verification
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import User, AccessCode
from app.schemas import UserResponse, MessageResponse
from app.dependencies import get_current_user

router = APIRouter()

# ===== Code Verification =====
@router.post("/verify-code", response_model=MessageResponse)
async def verify_code(
    request: Request,
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Verify access code and create guest session
    
    This allows users to browse content without creating an account
    """
    # Get stored code from database
    stored_code = db.query(AccessCode).first()
    
    if not stored_code or code.lower().strip() != stored_code.code.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid access code. Please check the code and try again."
        )
    
    # Set session
    request.session["code_verified"] = True
    request.session["verified_at"] = datetime.utcnow().isoformat()
    
    return {
        "message": "Code verified successfully! You can now access the book club.",
        "success": True
    }

# ===== Registration =====
@router.post("/register", response_model=UserResponse)
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Register a new user account
    
    Requirements:
    - Access code must be verified first
    - Email must be unique
    - Password minimum 8 characters
    """
    # Check if code is verified
    if not request.session.get("code_verified") and not request.session.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify access code first"
        )
    
    # Validate input
    if not name or not name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name is required"
        )
    
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )
    
    # Check if email exists
    existing_user = db.query(User).filter(User.email == email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered. Please login instead."
        )
    
    # Create user
    hashed_password = User.hash_password(password)
    new_user = User(
        name=name.strip(),
        email=email.lower(),
        password_hash=hashed_password,
        is_admin=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Auto-login by setting session
    request.session["user_id"] = new_user.id
    request.session["user_name"] = new_user.name
    request.session["is_admin"] = new_user.is_admin
    
    return new_user

# ===== Login =====
@router.post("/login", response_model=MessageResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Login user with email and password
    
    Creates a session that persists across requests
    """
    # Find user
    user = db.query(User).filter(User.email == email.lower()).first()
    
    if not user or not user.verify_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Set session
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["is_admin"] = user.is_admin
    
    return {
        "message": f"Welcome back, {user.name}!",
        "success": True
    }

# ===== Logout =====
@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request):
    """
    Logout user and clear session
    """
    request.session.clear()
    return {
        "message": "Logged out successfully",
        "success": True
    }

# ===== Get Current User =====
@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information
    
    Useful for frontend to check if user is logged in
    """
    return current_user

# ===== Check Session Status =====
@router.get("/status")
async def check_status(request: Request):
    """
    Check authentication status
    
    Returns info about current session without requiring authentication
    """
    user_id = request.session.get("user_id")
    code_verified = request.session.get("code_verified", False)
    
    return {
        "authenticated": user_id is not None,
        "code_verified": code_verified or user_id is not None,
        "is_admin": request.session.get("is_admin", False) if user_id else False,
        "user_name": request.session.get("user_name") if user_id else None
    }