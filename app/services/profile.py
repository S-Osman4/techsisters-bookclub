# app/services/profile.py
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError, ValidationError
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class ProfileService:
    """Handles member profile management: name, password, account deletion."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def update_name(self, user: User, new_name: str) -> User:
        """
        Update display name.
        Raises ValidationError if name is unchanged.
        """
        new_name = new_name.strip()
        if new_name.lower() == user.name.strip().lower():
            raise ValidationError("New name must be different from current name.")

        return await self.user_repo.update_name(user, new_name)

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str,
    ) -> User:
        """
        Change password after verifying the current one.
        Raises ValidationError if new password matches current.
        """
        if not verify_password(current_password, user.password_hash):
            raise UnauthorizedError("Current password is incorrect.")

        if verify_password(new_password, user.password_hash):
            raise ValidationError("New password cannot be the same as current password.")

        return await self.user_repo.update_password(user, hash_password(new_password))

    async def delete_account(
        self,
        user: User,
        password: str,
        confirmation: str,
    ) -> None:
        """
        Permanently delete a user account.
        Requires password verification and exact confirmation phrase.
        Cannot delete the last admin.
        """
        if user.is_admin:
            admin_count = await self.user_repo.count_admins()
            if admin_count <= 1:
                raise ForbiddenError(
                    "Cannot delete account — you are the only admin. "
                    "Promote another user first."
                )

        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Password is incorrect.")

        if confirmation.lower().strip() != "delete my account":
            raise ValidationError("Please type 'delete my account' exactly to confirm.")

        await self.user_repo.delete(user)
        logger.info("Account deleted: user_id=%s email=%s", user.id, user.email)