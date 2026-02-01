"""
HTML Pages Router - Serves templates for the web interface
"""
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import Query

from app.database import get_db
from app.models import Book, Meeting, User, BookSuggestion, ReadingProgress
from app.dependencies import get_current_user_optional, require_admin

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Helper function to check access
def has_access(request: Request) -> bool:
    """Check if user has access (code verified or logged in)"""
    return request.session.get("code_verified", False) or request.session.get("user_id") is not None

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Landing page with code entry"""
    # If already has access, redirect to dashboard
    if has_access(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    # If already logged in, redirect to dashboard
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )

@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page"""
    # If already logged in, redirect to dashboard
    if request.session.get("user_id"):
        return RedirectResponse(url="/dashboard", status_code=302)
    
    # Check if code is verified
    code_verified = request.session.get("code_verified", False)
    
    if not code_verified:
        # Redirect to home to verify code first
        return RedirectResponse(url="/?error=verify_code_first", status_code=302)
    
    return templates.TemplateResponse(
        "register.html",
        {
            "request": request,
            "code_verified": code_verified
        }
    )

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """
    Member dashboard - works for both guests and logged-in users
    """
    # Check access
    if not has_access(request):
        return RedirectResponse(url="/?error=access_required", status_code=302)
    
    # Fetch data
    current_book = db.query(Book).filter(Book.status == "current").first()
    meeting = db.query(Meeting).first()
    uk_tz = ZoneInfo("Europe/London")
    upcoming_books = db.query(Book).filter(Book.status == "queued").order_by(Book.created_at).all()
    past_books = db.query(Book).filter(Book.status == "completed").order_by(Book.completed_date.desc()).all()
    
    # Community progress - FIXED INDENTATION
    community_stats = []
    if current_book:
        all_progress = db.query(ReadingProgress).filter(
            ReadingProgress.book_id == current_book.id
        ).all()
        
        total_members = len(all_progress)
        if total_members > 0:
            stats = {}
            sort_order = {}
            
            # THIS LOOP MUST CONTAIN THE IF/ELIF/ELSE BLOCK
            for progress in all_progress:
                chapter = progress.chapter
                
                # THIS BLOCK MUST BE INSIDE THE LOOP
                if chapter == -1:
                    key = "Completed"
                    order = 999  # Last
                elif chapter == 0:
                    key = "Not Started"
                    order = 0  # First
                elif chapter <= 2:
                    key = "Chapters 1-2"
                    order = 1
                elif chapter <= 4:
                    key = "Chapters 3-4"
                    order = 2
                elif chapter <= 6:
                    key = "Chapters 5-6"
                    order = 3
                else:
                    key = f"Chapter {chapter}+"
                    order = 4
                
                stats[key] = stats.get(key, 0) + 1
                sort_order[key] = order

            # Sort by order, then build the list
            sorted_ranges = sorted(stats.items(), key=lambda x: sort_order[x[0]])

            for range_name, count in sorted_ranges:
                percentage = (count / total_members * 100)
                community_stats.append({
                    "range": range_name,
                    "count": count,
                    "percentage": round(percentage, 1)
                })

    # If logged in, get user-specific data
    user_progress = None
    user_suggestions = []
    
    if current_user:
        if current_book:
            user_progress = db.query(ReadingProgress).filter(
                ReadingProgress.user_id == current_user.id,
                ReadingProgress.book_id == current_book.id
            ).first()
        
        user_suggestions = db.query(BookSuggestion).filter(
            BookSuggestion.user_id == current_user.id
        ).order_by(BookSuggestion.created_at.desc()).all()
   
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "current_book": current_book,
            "meeting": meeting,
            "uk_tz": uk_tz,
            "upcoming_books": upcoming_books,
            "past_books": past_books,
            "user_progress": user_progress,
            "user_suggestions": user_suggestions,
            "community_stats": community_stats,
            "is_guest": current_user is None
        }
    )

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Admin dashboard"""
    from app.models import AccessCode, AdminAction
    from sqlalchemy import func
    from datetime import datetime
    
    # Fetch admin data
    access_code = db.query(AccessCode).first()
    current_book = db.query(Book).filter(Book.status == "current").first()
    meeting = db.query(Meeting).first()
    uk_tz = ZoneInfo("Europe/London")
    
    # Pending suggestions with user names
    pending_suggestions_query = db.query(BookSuggestion, User).join(User).filter(
        BookSuggestion.status == "pending"
    ).all()
    
    pending_suggestions = []
    for suggestion, user in pending_suggestions_query:
        pending_suggestions.append({
            "id": suggestion.id,
            "title": suggestion.title,
            "pdf_url": suggestion.pdf_url,
            "cover_image_url": suggestion.cover_image_url,
            "user_name": user.name,
            "user_email": user.email,
            "created_at": suggestion.created_at
        })
    
    approved_queue = db.query(Book).filter(Book.status == "queued").order_by(Book.created_at).all()
    
    # Stats
    total_members = int(db.query(func.count(User.id)).scalar() or 0)
    first_day_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_members = int(db.query(func.count(User.id)).filter(User.created_at >= first_day_of_month).scalar() or 0)
    pending_count = len(pending_suggestions)
    
    # Current book engagement
    engagement = {"tracking": 0, "avg_chapter": 0}
    if current_book:
        progress_count = db.query(func.count(ReadingProgress.id)).filter(
            ReadingProgress.book_id == current_book.id
        ).scalar()
        
        avg_chapter = db.query(func.avg(ReadingProgress.chapter)).filter(
            ReadingProgress.book_id == current_book.id,
            ReadingProgress.chapter > 0
        ).scalar()
        
        engagement["tracking"] = progress_count or 0
        engagement["avg_chapter"] = round(float(avg_chapter) if avg_chapter else 0, 1)
    
    # Get all users
    all_users = db.query(User).order_by(User.created_at.desc()).all()
    
    users_list = []
    for user in all_users:
        users_list.append({
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": user.is_admin,
            "created_at": user.created_at
        })
    
    # Count admins
    admin_count = int(db.query(func.count(User.id)).filter(User.is_admin == True).scalar() or 0)
    admin_count = int(admin_count) if admin_count else 0

    # Get recent admin logs  ← ADD THIS BLOCK
    recent_logs_query = db.query(AdminAction, User).join(
        User, AdminAction.admin_id == User.id
    ).order_by(
        AdminAction.created_at.desc()
    ).limit(20).all()
    
    admin_logs = []
    for log, user in recent_logs_query:
        admin_logs.append({
            "id": log.id,
            "admin_name": user.name,
            "action": log.action,
            "target": log.target,
            "timestamp": log.created_at
        })
        
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "admin": admin,
            "access_code": access_code,
            "current_book": current_book,
            "meeting": meeting,
            "uk_tz": uk_tz,
            "pending_suggestions": pending_suggestions,
            "approved_queue": approved_queue,
            "total_members": total_members,
            "new_members": new_members,
            "pending_count": pending_count,
            "engagement": engagement,
            "admin_logs": admin_logs,
            "all_users": users_list,
            "admin_count": admin_count
        }
    )

@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """User profile page"""
    
    # Redirect to login if not authenticated
    if not current_user:
        return RedirectResponse(url="/login?error=login_required", status_code=302)
    
    # Get user stats
    from sqlalchemy import func
    
    total_suggestions = db.query(func.count(BookSuggestion.id)).filter(
        BookSuggestion.user_id == current_user.id
    ).scalar()
    
    approved_suggestions = db.query(func.count(BookSuggestion.id)).filter(
        BookSuggestion.user_id == current_user.id,
        BookSuggestion.status == "approved"
    ).scalar()
    
    completed_books = db.query(func.count(ReadingProgress.id)).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.chapter == -1
    ).scalar()
    
    currently_reading = db.query(func.count(ReadingProgress.id)).filter(
        ReadingProgress.user_id == current_user.id,
        ReadingProgress.chapter > 0
    ).scalar()
    
    stats = {
        "total_suggestions": total_suggestions or 0,
        "approved_suggestions": approved_suggestions or 0,
        "completed_books": completed_books or 0,
        "currently_reading": currently_reading or 0
    }
    
    # Check if only admin
    is_only_admin = False
    if current_user.is_admin:
        admin_count = db.query(func.count(User.id)).filter(User.is_admin == True).scalar()
        is_only_admin = (admin_count <= 1)
    
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "is_only_admin": is_only_admin
        }
    )
# GET /past-books
@router.get("/past-books")
async def past_books_page(
    request: Request,
    search: str = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    query = (
        db.query(Book)
        .filter(Book.status == "completed")
        .order_by(Book.completed_date.desc())
    )

    if search:
        query = query.filter(Book.title.ilike(f"%{search}%"))

    total = query.count()
    books = query.offset((page - 1) * 10).limit(10).all()

    is_htmx = request.headers.get("HX-Request") is not None

    context = {
        "request": request,
        "books": books,
        "search": search,
        "page": page,
        "total_pages": (total + 9) // 10,
        "current_user": current_user,
        "total_count": total,
    }

    if is_htmx:
        return templates.TemplateResponse("partials/books_grid.html", context)
    else:
        return templates.TemplateResponse("past_books.html", context)


# GET /upcoming-books
@router.get("/upcoming-books")
async def upcoming_books_page(
    request: Request,
    search: str = Query(None),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    query = (
        db.query(Book)
        .filter(Book.status == "queued")
        .order_by(Book.created_at.asc())
    )

    if search:
        query = query.filter(Book.title.ilike(f"%{search}%"))

    total = query.count()
    books = query.offset((page - 1) * 10).limit(10).all()

    is_htmx = request.headers.get("HX-Request") is not None

    context = {
        "request": request,
        "books": books,
        "search": search,
        "page": page,
        "total_pages": (total + 9) // 10,
        "current_user": current_user,
        "total_count": total,
    }

    if is_htmx:
        return templates.TemplateResponse("partials/books_grid.html", context)
    else:
        return templates.TemplateResponse("upcoming_books.html", context)

# FEEDBACK PAGE
@router.get("/feedback", response_class=HTMLResponse)
async def feedback_page(
    request: Request,
    current_user: User = Depends(get_current_user_optional),
):
    return templates.TemplateResponse(
        "feedback.html",
        {
            "request": request,
            "current_user": current_user,
        },
    )
