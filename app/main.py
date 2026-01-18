"""
Main FastAPI Application
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv

from app.database import DATABASE_URL, create_tables, test_connection, disconnect
from app.routers import auth, books, admin, pages, profile

# Load environment variables
load_dotenv()

# Create FastAPI app
app = FastAPI(
    title="TechSisters Book Club API",
    description="Backend API for TechSisters Book Club",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc"  # ReDoc UI at /redoc
)

# Add session middleware (for cookie-based sessions)
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=2592000,  # 30 days in seconds
    same_site="lax",
    https_only=os.getenv("ENVIRONMENT") == "production"
)

# CORS middleware (for frontend if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (for CSS, JS, images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(books.router, prefix="/api/books", tags=["Books"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(pages.router, tags=["Pages"])

# ===== Custom Error Handlers =====
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with user-friendly messages"""
    # If it's an API request, return JSON
    if request.url.path.startswith(("/api/", "/auth/")):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "success": False,
                "error_type": "http_error"
            }
        )
    
    # For HTML pages, redirect with error message
    if exc.status_code == 404:
        return RedirectResponse("/?error=page_not_found", status_code=302)
    elif exc.status_code == 403:
        return RedirectResponse("/?error=access_denied", status_code=302)
    elif exc.status_code == 401:
        return RedirectResponse("/login?error=login_required", status_code=302)
    else:
        return RedirectResponse("/?error=server_error", status_code=302)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = exc.errors()
    error_messages = []
    
    for error in errors:
        field = ".".join(str(loc) for loc in error.get("loc", []))
        msg = error.get("msg", "Invalid input")
        error_messages.append(f"{field}: {msg}")
    
    error_detail = "; ".join(error_messages)
    
    if request.url.path.startswith(("/api/", "/auth/")):
        return JSONResponse(
            status_code=422,
            content={
                "detail": f"Validation error: {error_detail}",
                "success": False,
                "error_type": "validation_error"
            }
        )
    
    return RedirectResponse("/?error=validation_error", status_code=302)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    # Log the error (in production, use proper logging)
    print(f"Unhandled error: {exc}")
    
    if request.url.path.startswith(("/api/", "/auth/")):
        return JSONResponse(
            status_code=500,
            content={
                "detail": "An unexpected error occurred. Please try again.",
                "success": False,
                "error_type": "server_error"
            }
        )
    
    return RedirectResponse("/?error=server_error", status_code=302)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("🚀 Starting TechSisters Book Club API...")
    
    # Test database connection
    if test_connection():
        print("✅ Database connected")
    else:
        print("❌ Database connection failed!")
        return
    
    # Create tables if they don't exist
    create_tables()
    
    print("✅ Application started successfully!")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"📖 ReDoc: http://localhost:8000/redoc")

# Root endpoint
@app.get("/")
async def root():
    """API root - shows basic info"""
    return {
        "message": "TechSisters Book Club API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "status": "running"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# Add graceful shutdown handler
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("🔴 Shutting down gracefully...")
    # Add any cleanup code here (close database connections, etc.)
    disconnect()
    print("✅ Shutdown complete.")