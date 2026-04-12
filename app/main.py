# app/main.py
import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.exceptions import AppError
from app.core.middleware import CSRFMiddleware, SecurityHeadersMiddleware

logging.basicConfig(
    level=logging.DEBUG if settings.is_development else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)



# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TechSisters Book Club",
    version="2.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware ────────────────────────────────────────────────────────────────
# Order matters: outermost middleware wraps all inner ones.
# SessionMiddleware must come before CSRFMiddleware so that
# request.session is available when CSRF reads the session ID.

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie=settings.SESSION_COOKIE_NAME,
    max_age=settings.SESSION_MAX_AGE,
    same_site="lax",
    https_only=settings.is_production,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [
            "https://techsisters-bookclub.onrender.com",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        if settings.is_production
        else ["*"]
    ),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*", "X-CSRFToken"],
)

# ── Static files ──────────────────────────────────────────────────────────────
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── Routers ───────────────────────────────────────────────────────────────────
from app.api.auth import router as auth_router          # noqa: E402
from app.api.books import router as books_router        # noqa: E402
from app.api.admin import router as admin_router        # noqa: E402
from app.api.profile import router as profile_router    # noqa: E402
from app.api.feedback import router as feedback_router  # noqa: E402
from app.api.pages import router as pages_router        # noqa: E402

app.include_router(auth_router)
app.include_router(books_router)
app.include_router(admin_router)
app.include_router(profile_router)
app.include_router(feedback_router)
app.include_router(pages_router)


# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "success": False},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Invalid input") if errors else "Invalid input"
    return JSONResponse(
        status_code=422,
        content={"detail": first_msg, "success": False},
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith(("/api/", "/auth/")):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "success": False},
        )
    if exc.status_code == 401:
        return RedirectResponse(url="/login?error=login_required", status_code=302)
    if exc.status_code == 403:
        return RedirectResponse(url="/?error=access_denied", status_code=302)
    return RedirectResponse(url="/?error=server_error", status_code=302)


# ── Lifecycle ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    from app.database import check_connection, create_all_tables
    if not settings.is_testing:
        ok = await check_connection()
        if ok:
            logger.info("Database connected")
            await create_all_tables()
        else:
            logger.error("Database connection failed on startup")


@app.on_event("shutdown")
async def shutdown():
    from app.database import engine
    await engine.dispose()
    logger.info("Database connections closed")


# ── Health check ──────────────────────────────────────────────────────────────
@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    from app.database import check_connection
    db_ok = await check_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "environment": settings.ENVIRONMENT,
    }