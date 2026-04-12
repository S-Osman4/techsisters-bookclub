# seed.py
"""
Seed script — run once after setting up the database.

Creates:
  - The singleton AccessCode row (id=1)
  - The singleton Meeting row (id=1) with placeholder values
  - An admin user from ADMIN_EMAIL / ADMIN_PASSWORD env vars

Safe to re-run — existing rows are updated, not duplicated.

Usage:
    python seed.py
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s — %(message)s",
)
logger = logging.getLogger(__name__)


async def seed() -> None:
    # Import here so .env is loaded first
    from app.database import AsyncSessionFactory, create_all_tables
    from app.models.access_code import AccessCode
    from app.models.meeting import Meeting
    from app.models.user import User
    from app.core.security import hash_password

    logger.info("Creating tables if they don't exist...")
    await create_all_tables()

    admin_email = os.getenv("ADMIN_EMAIL", "").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()

    if not admin_email or not admin_password:
        logger.error(
            "ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env to seed an admin user."
        )
        sys.exit(1)

    async with AsyncSessionFactory() as session:
        try:
            await _seed_access_code(session)
            await _seed_meeting(session)
            await _seed_admin(session, admin_email, admin_password)
            await session.commit()
            logger.info("Seed complete.")
        except Exception as exc:
            await session.rollback()
            logger.error("Seed failed: %s", exc)
            raise


async def _seed_access_code(session) -> None:
    """Create or update the singleton access code."""
    from sqlalchemy import select
    from app.models.access_code import AccessCode

    result = await session.execute(
        select(AccessCode).where(AccessCode.id == 1)
    )
    existing = result.scalar_one_or_none()

    if existing:
        logger.info("Access code already exists: %r — skipping.", existing.code)
        return

    code = AccessCode(id=1, code="TECHSISTERS2026")
    session.add(code)
    logger.info("Access code created: TECHSISTERS2026")


async def _seed_meeting(session) -> None:
    """Create the singleton meeting row with placeholder values."""
    from sqlalchemy import select
    from app.models.meeting import Meeting

    result = await session.execute(
        select(Meeting).where(Meeting.id == 1)
    )
    existing = result.scalar_one_or_none()

    if existing:
        logger.info("Meeting row already exists — skipping.")
        return

    # Default: one week from now at 18:00 UTC
    default_start = datetime.now(timezone.utc).replace(
        hour=18, minute=0, second=0, microsecond=0
    ) + timedelta(days=7)

    meeting = Meeting(
        id=1,
        start_at=default_start,
        meet_link="https://meet.google.com/placeholder",
    )
    session.add(meeting)
    logger.info("Meeting row created with placeholder values.")


async def _seed_admin(session, email: str, password: str) -> None:
    """Create admin user if email does not already exist."""
    from sqlalchemy import func, select
    from app.models.user import User

    result = await session.execute(
        select(User).where(func.lower(User.email) == email.lower())
    )
    existing = result.scalar_one_or_none()

    if existing:
        if not existing.is_admin:
            existing.is_admin = True
            logger.info("Existing user %r promoted to admin.", email)
        else:
            logger.info("Admin user %r already exists — skipping.", email)
        return

    from app.core.security import hash_password
    admin = User(
        name="Admin",
        email=email.lower(),
        password_hash=hash_password(password),
        is_admin=True,
    )
    session.add(admin)
    logger.info("Admin user created: %s", email)


if __name__ == "__main__":
    asyncio.run(seed())