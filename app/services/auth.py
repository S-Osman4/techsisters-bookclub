# app/services/auth.py
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    ExternalServiceError,
    UnauthorizedError,
    ValidationError,
)
from app.core.security import hash_password, verify_password
from app.repositories.access_code import AccessCodeRepository
from app.repositories.user import UserRepository
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthService:
    """
    Handles all authentication flows:
    access code verification, registration, login, logout.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.code_repo = AccessCodeRepository(session)

    async def verify_access_code(self, code: str) -> bool:
        """
        Verify the submitted code against the stored singleton.
        Uses constant-time comparison to prevent timing attacks.
        Returns True on match, raises UnauthorizedError on mismatch.
        """
        import secrets

        stored = await self.code_repo.get()
        if not stored:
            logger.error("Access code not configured — seed.py has not been run")
            raise ValidationError("Access code not configured. Contact an admin.")

        # Constant-time comparison
        match = secrets.compare_digest(
            code.strip().upper(),
            stored.code.strip().upper(),
        )
        if not match:
            logger.warning("Failed access code attempt")
            raise UnauthorizedError("Invalid access code.")

        return True

    async def verify_hcaptcha(self, token: str, client_ip: str) -> None:
        """
        Verify hCaptcha token with hCaptcha servers.
        Raises ExternalServiceError if verification fails.
        Skips verification in test/development environments.
        """
        if settings.is_development or settings.is_testing:
            logger.debug("hCaptcha skipped in %s environment", settings.ENVIRONMENT)
            return

        if not token:
            raise ValidationError("Please complete the captcha verification.")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    "https://hcaptcha.com/siteverify",
                    data={
                        "secret": settings.HCAPTCHA_SECRET,
                        "response": token,
                        "remoteip": client_ip,
                    },
                )
            data = response.json()
            if not data.get("success"):
                errors = data.get("error-codes", [])
                logger.warning("hCaptcha failed: %s", errors)
                raise ValidationError("Captcha verification failed. Please try again.")
        except httpx.TimeoutException:
            logger.error("hCaptcha verification timed out")
            raise ExternalServiceError("Captcha service unavailable. Please try again.")

    async def register(
        self,
        name: str,
        email: str,
        password: str,
    ) -> User:
        """
        Register a new user.
        - Checks for duplicate email
        - Hashes password
        - Returns the created user

        Session verification and hCaptcha must be checked
        in the route before calling this method.
        """
        email = email.lower().strip()

        if await self.user_repo.email_exists(email):
            raise ConflictError("This email is already registered. Please login instead.")

        user = await self.user_repo.create(
            name=name.strip(),
            email=email,
            password_hash=hash_password(password),
            is_admin=False,
        )

        logger.info("New user registered: %s", email)
        return user

    async def login(self, email: str, password: str) -> User:
        """
        Authenticate a user by email and password.
        Raises UnauthorizedError for any failure (no detail on which field
        is wrong — prevents user enumeration).
        """
        email = email.lower().strip()
        user = await self.user_repo.get_by_email(email)

        # Same error whether user not found or password wrong
        if not user or not verify_password(password, user.password_hash):
            logger.warning("Failed login attempt for email: %s", email)
            raise UnauthorizedError("Invalid email or password.")

        logger.info("User logged in: %s", email)
        return user

    @staticmethod
    def build_session(user: User) -> dict:
        """
        Build the session payload for a logged-in user.
        Called after login and register to populate the session.
        """
        return {
            "user_id": user.id,
            "user_name": user.name,
            "is_admin": user.is_admin,
            "session_created_at": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def is_session_expired(session_created_at: str) -> bool:
        """
        Check if the session has exceeded the absolute timeout.
        Returns True if expired.
        """
        from datetime import timedelta

        try:
            created = datetime.fromisoformat(session_created_at)
            # Make aware if naive
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            timeout = timedelta(days=settings.SESSION_ABSOLUTE_TIMEOUT_DAYS)
            return datetime.now(timezone.utc) - created > timeout
        except (ValueError, TypeError):
            return True  # Treat unparseable timestamp as expired