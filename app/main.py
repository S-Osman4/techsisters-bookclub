"""
Main FastAPI Application
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv

from app.database import create_tables, test_connection
from app.routers import auth, books, admin

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

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    return {
        "detail": "Endpoint not found",
        "path": str(request.url)
    }

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors"""
    return {
        "detail": "Internal server error",
        "message": "Something went wrong. Please try again later."
    }