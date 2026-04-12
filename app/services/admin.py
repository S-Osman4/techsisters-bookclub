# app/services/admin.py
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.user import User
from app.repositories.access_code import AccessCodeRepository
from app.repositories.admin_action import AdminActionRepository
from app.repositories.book import BookRepository
from app.repositories.book_suggestion import BookSuggestionRepository
from app.repositories.reading_progress import ReadingProgressRepository
from app.repositories.user import UserRepository
from app.schemas.admin import AdminLogResponse, AdminLogDetailResponse, AdminStatsResponse

logger = logging.getLogger(__name__)


class AdminService:
    """Handles admin-only operations: user management, stats, logs, access code."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.book_repo = BookRepository(session)
        self.suggestion_repo = BookSuggestionRepository(session)
        self.progress_repo = ReadingProgressRepository(session)
        self.code_repo = AccessCodeRepository(session)
        self.log_repo = AdminActionRepository(session)

    # ── Access code ───────────────────────────────────────────────────────────

    async def update_access_code(
        self, new_code: str, admin_id: int
    ) -> str:
        """
        Update the singleton access code.
        Returns the new code.
        """
        code = await self.code_repo.upsert(new_code)

        await self.log_repo.log(
            admin_id=admin_id,
            action="update_access_code",
            target={"new_code": new_code},
        )

        logger.info("Admin %s updated access code", admin_id)
        return code.code

    # ── User management ───────────────────────────────────────────────────────

    async def get_all_users(self) -> list[User]:
        """Return all users ordered by join date."""
        return await self.user_repo.get_all_ordered()

    async def promote_user(self, user_id: int, admin_id: int) -> User:
        """Promote a member to admin."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")

        if user.is_admin:
            raise ConflictError(f"{user.name} is already an admin.")

        user = await self.user_repo.set_admin(user, True)

        await self.log_repo.log(
            admin_id=admin_id,
            action="promote_user",
            target={"user_id": user_id, "user_name": user.name},
        )

        logger.info("Admin %s promoted user %s (%s)", admin_id, user_id, user.name)
        return user

    async def demote_user(self, user_id: int, admin_id: int) -> User:
        """
        Demote an admin to regular member.
        Cannot demote self or the last remaining admin.
        """
        if user_id == admin_id:
            raise ForbiddenError("You cannot demote yourself.")

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found.")

        if not user.is_admin:
            raise ConflictError(f"{user.name} is not an admin.")

        admin_count = await self.user_repo.count_admins()
        if admin_count <= 1:
            raise ForbiddenError(
                "Cannot demote the last admin. Promote another user first."
            )

        user = await self.user_repo.set_admin(user, False)

        await self.log_repo.log(
            admin_id=admin_id,
            action="demote_user",
            target={"user_id": user_id, "user_name": user.name},
        )

        logger.info("Admin %s demoted user %s (%s)", admin_id, user_id, user.name)
        return user

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def get_stats(self) -> AdminStatsResponse:
        """Return dashboard statistics for the admin panel."""
        from sqlalchemy import func, select
        from app.models.reading_progress import ReadingProgress

        # Total members
        total_members = await self.user_repo.count()

        # New this month
        first_of_month = datetime.now(timezone.utc).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        new_this_month = await self.user_repo.count_new_since(first_of_month)

        # Pending suggestions
        pending = await self.suggestion_repo.get_pending()
        pending_count = len(pending)

        # Queue size
        queue = await self.book_repo.get_queue()
        queue_count = len(queue)

        # Current book engagement
        tracking = 0
        avg_chapter = 0.0
        current = await self.book_repo.get_current()
        if current:
            tracking = await self.progress_repo.count_tracking(current.id)
            all_progress = await self.progress_repo.get_all_for_book(current.id)
            active = [p.chapter for p in all_progress if p.chapter > 0]
            avg_chapter = round(sum(active) / len(active), 1) if active else 0.0

        return AdminStatsResponse(
            total_members=total_members,
            new_members_this_month=new_this_month,
            pending_suggestions=pending_count,
            books_in_queue=queue_count,
            tracking_progress=tracking,
            avg_chapter=avg_chapter,
        )

    # ── Logs ──────────────────────────────────────────────────────────────────

    async def get_logs(
        self,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminLogDetailResponse:
        """
        Return paginated admin activity logs.
        Parses JSON target field before returning.
        """
        offset = (page - 1) * page_size
        records, total = await self.log_repo.get_recent(
            limit=page_size,
            offset=offset,
        )

        logs: list[AdminLogResponse] = []
        for record in records:
            target_data = None
            if record.target:
                try:
                    target_data = json.loads(record.target)
                except (json.JSONDecodeError, TypeError):
                    target_data = {"raw": record.target}

            logs.append(
                AdminLogResponse(
                    id=record.id,
                    admin_id=record.admin_id,
                    admin_name=record.admin.name if record.admin else "Deleted user",
                    action=record.action,
                    target_data=target_data,
                    created_at=record.created_at,
                )
            )

        return AdminLogDetailResponse(
            logs=logs,
            total=total,
            page=page,
            page_size=page_size,
        )