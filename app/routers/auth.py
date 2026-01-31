"""
Authentication routes - login, register, code verification
"""
import code
import re
import secrets
import bleach
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form

from app.database import get_db
from app.models import User, AccessCode
from app.schemas import UserResponse, MessageResponse
from app.dependencies import get_current_user

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ===== Helper Functions =====
def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain a number"
    
    return True, ""

def sanitize_input(text: str, max_length: int = 200) -> str:
    """
    Sanitize user input to prevent XSS attacks
    
    - Removes all HTML tags
    - Strips whitespace
    - Limits length
    """
    if not text:
        return ""
    
    # Remove all HTML tags
    cleaned = bleach.clean(text, tags=[], strip=True)
    
    # Strip whitespace
    cleaned = cleaned.strip()
    
    # Limit length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned

# ===== Code Verification =====
@router.post("/verify-code", response_model=MessageResponse)
@limiter.limit("10/minute")
async def verify_code(
    request: Request,
    code: str = Form(...),
    db: Session = Depends(get_db)
):
    """
    Verify access code and create guest session
    
    This allows users to browse content without creating an account
    """
     # Clean and validate input
    code = code.strip()
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access code cannot be empty"
        )
    
    # Get stored code from database
    stored_code = db.query(AccessCode).first()
    
    if not stored_code:
        # This shouldn't happen, but handle it gracefully
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Access code not configured. Please contact admin."
        )
    
    # Now compare codes using constant-time comparison
    if not secrets.compare_digest(code.lower(), stored_code.code.lower()):
        # Give a hint if close
        if len(code) == len(stored_code.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid access code. Please check the code and try again."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid access code. The code should be {len(stored_code.code)} characters long."
            )
    # Set session
    request.session["code_verified"] = True
    request.session["verified_at"] = datetime.utcnow().isoformat()
    
    return {
        "message": "Code verified successfully! You can now access the book club.",
        "success": True
    }

# ===== Registration =====
@router.post("/register")
@limiter.limit("5/hour")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    from_param: str = Form(None, alias="from"),
    db: Session = Depends(get_db)
):
    """
    Register a new user account with auto-login
    
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
    
    # Clean and sanitize inputs
    name = sanitize_input(name, max_length=50)
    email = sanitize_input(email, max_length=100).lower()
    
    # Validate input
    # Validate name
    if not name or len(name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must be at least 2 characters long"
        )
    
    if len(name) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name cannot exceed 50 characters"
        )
    
    # Validate email
    if not validate_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid email address"
        )
    
    # Validate password
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    if len(password) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password cannot exceed 100 characters"
        )
    
    # Check if email exists
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is already registered. Please login instead."
        )
    
    # Create user
    try:
        hashed_password = User.hash_password(password)
        new_user = User(
            name=name,
            email=email,
            password_hash=hashed_password,
            is_admin=False
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Regenerate session to prevent session fixation attacks
        old_session_data = dict(request.session)
        request.session.clear()
        # Only preserve code verification if it existed
        if old_session_data.get("code_verified"):
            request.session["code_verified"] = True
    
        # Auto-login the new user
        request.session["user_id"] = new_user.id
        request.session["user_name"] = new_user.name
        request.session["is_admin"] = new_user.is_admin
        
        # Determine redirect URL based on from parameter
        if from_param == "dashboard":
            redirect_url = "/dashboard"
        elif from_param == "suggest":
            redirect_url = "/dashboard#suggest-book"
        else:
            redirect_url = "/dashboard"
        
        # Return redirect response with HX-Redirect header for htmx
        return {
        "success": True,
        "redirect": redirect_url
    }
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again."
        )

# ===== Login =====
@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    from_param: str = Form(None, alias="from"),
    db: Session = Depends(get_db)
):
    """
    Login user with email and password
    
    Creates a session that persists across requests
    """
    # Clean inputs
    email = email.strip().lower()
    
    # Validate email
    if not validate_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter a valid email address"
        )
    
    # Find user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Don't reveal if user exists (security)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    try:
        if not user.verify_password(password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
    except Exception:
        # Handle password verification errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Set session
   # Regenerate session to prevent session fixation attacks
    old_session_data = dict(request.session)
    request.session.clear()
    # Only preserve code verification if it existed
    if old_session_data.get("code_verified"):
        request.session["code_verified"] = True
    
# Set new authenticated session data
    request.session["user_id"] = user.id
    request.session["user_name"] = user.name
    request.session["is_admin"] = user.is_admin
    
    # Determine redirect URL based on from parameter
    if from_param == "dashboard":
        redirect_url = "/dashboard"
    elif from_param == "suggest":
        redirect_url = "/dashboard#suggest-book"
    elif from_param == "suggestions":
        redirect_url = "/dashboard#your-suggestions"
    else:
        redirect_url = "/dashboard"
    
    # Return redirect response with HX-Redirect header for htmx
    return {
    "success": True,
    "redirect": redirect_url
}

# ===== Logout =====
@router.post("/logout")
async def logout(request: Request):
    """
    Logout user and clear all session data
    """
    # Clear all session data (user session and code verification)
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

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