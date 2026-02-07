"""
Main FastAPI Application - Enhanced for Testing
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
from secure import Secure

from app.database import DATABASE_URL, create_tables, test_connection, disconnect
from app.routers import auth, books, admin, pages, profile, feedback

# Load environment variables
load_dotenv()

# Detect test environment
IS_TEST_ENV = (
    os.getenv("ENVIRONMENT") == "test"
    or os.getenv("RATE_LIMIT_DISABLED") == "true"
    or os.getenv("PYTEST_CURRENT_TEST") is not None
    or "pytest" in os.getenv("_", "")  # Additional pytest detection
)

# Configure logging
if os.getenv("ENVIRONMENT") == "production":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
elif IS_TEST_ENV:
    # Less verbose logging in tests
    logging.basicConfig(level=logging.WARNING)
else:
    logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="TechSisters Book Club API",
    description="Backend API for TechSisters Book Club",
    version="1.0.0",
    docs_url="/docs" if not IS_TEST_ENV else None,  # Disable docs in tests
    redoc_url="/redoc" if not IS_TEST_ENV else None
)

# Rate limiting setup
if IS_TEST_ENV:
    # Mock limiter for tests - completely bypasses rate limiting
    class MockLimiter:
        def limit(self, *args, **kwargs):
            """No-op decorator for tests"""
            def decorator(func):
                return func
            return decorator
        
        def __call__(self, *args, **kwargs):
            """Allow limiter to be called directly"""
            return self.limit(*args, **kwargs)
    
    limiter = MockLimiter()
    logger.info("⚠️ Rate limiting DISABLED for test environment")
else:
    # Real limiter for production/development
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["1000/hour"],  # Global default
        storage_uri="memory://"  # Use in-memory storage
    )
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("✅ Rate limiting ENABLED")

app.state.limiter = limiter

# Session middleware
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if IS_TEST_ENV:
        SECRET_KEY = "test-secret-key-for-testing-only"
        logger.warning("⚠️ Using test SECRET_KEY")
    else:
        raise ValueError("SECRET_KEY environment variable is not set")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=2592000,  # 30 days
    same_site="lax",
    https_only=os.getenv("ENVIRONMENT") == "production",
    session_cookie="session_id"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://techsisters-bookclub.onrender.com",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://testserver",  # For testing
    ] if os.getenv("ENVIRONMENT") == "production" else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Security headers (skip in test environment)
if not IS_TEST_ENV:
    secure_headers = Secure()

    @app.middleware("http")
    async def set_security_headers(request: Request, call_next):
        response = await call_next(request)

        if 300 <= response.status_code < 400:
            return response

        headers = secure_headers.headers
        for k, v in headers.items():
            response.headers[k] = v

        if os.getenv("ENVIRONMENT") == "production":
            if response.status_code == 401 and request.url.path.startswith(("/auth/", "/api/")):
                logger.warning(
                    f"Failed auth attempt: {request.client.host} → {request.url.path}",
                    extra={"user_agent": request.headers.get("user-agent")}
                )
            
            if response.status_code == 429:
                logger.warning(
                    f"Rate limit hit: {request.client.host} → {request.url.path}",
                    extra={"user_agent": request.headers.get("user-agent")}
                )

        return response

# Mount static files (skip in test to avoid directory errors)
if not IS_TEST_ENV and os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(books.router, prefix="/api/books", tags=["Books"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(profile.router, prefix="/api/profile", tags=["Profile"])
app.include_router(pages.router, tags=["Pages"])
app.include_router(feedback.api_router, tags=["Feedback"])

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith(("/api/", "/auth/")):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "success": False,
                "error_type": "http_error"
            }
        )
    
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
    if os.getenv("ENVIRONMENT") == "production":
        logger.error(
            f"Unhandled error on {request.method} {request.url.path}",
            exc_info=True,
            extra={
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        error_message = "An unexpected error occurred. Please try again."
    else:
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        error_message = str(exc) if not IS_TEST_ENV else "Test error"
    
    if request.url.path.startswith(("/api/", "/auth/")):
        return JSONResponse(
            status_code=500,
            content={
                "detail": error_message,
                "success": False,
                "error_type": "server_error"
            }
        )
    
    return RedirectResponse("/?error=server_error", status_code=302)

# Lifecycle events
@app.on_event("startup")
async def startup_event():
    if not IS_TEST_ENV:
        print("🚀 Starting TechSisters Book Club API...")
        
        if test_connection():
            print("✅ Database connected")
        else:
            print("❌ Database connection failed!")
            return
        
        create_tables()
        
        print("✅ Application started successfully!")
        print(f"📚 API Docs: http://localhost:8000/docs")
        print(f"📖 ReDoc: http://localhost:8000/redoc")

@app.get("/")
async def root():
    return {
        "message": "TechSisters Book Club API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "rate_limiting": "disabled" if IS_TEST_ENV else "enabled"
    }

@app.on_event("shutdown")
async def shutdown_event():
    if not IS_TEST_ENV:
        print("🔴 Shutting down gracefully...")
        disconnect()
        print("✅ Shutdown complete.")