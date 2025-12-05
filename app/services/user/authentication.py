"""
User authentication functionality.

Handles financial password verification with rate limiting.
"""

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository


class UserAuthenticationMixin:
    """
    Mixin for user authentication functionality.

    Provides financial password verification with rate limiting.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user authentication mixin."""
        self.session = session
        self.user_repo = UserRepository(session)

    async def verify_financial_password(
        self, user_id: int, password: str
    ) -> tuple[bool, str | None]:
        """
        Verify financial password with rate limiting.

        Args:
            user_id: User ID
            password: Plain password to verify

        Returns:
            Tuple (success, error_message). Error is None if success.
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return False, "Пользователь не найден"

        # Rate limiting: check if user is locked out
        MAX_ATTEMPTS = 5
        LOCKOUT_MINUTES = 15

        if user.finpass_attempts >= MAX_ATTEMPTS:
            if user.finpass_locked_until and user.finpass_locked_until > datetime.now(UTC):
                remaining = (user.finpass_locked_until - datetime.now(UTC)).seconds // 60 + 1
                return False, (
                    f"🔒 Слишком много неудачных попыток!\n\n"
                    f"Повторите через {remaining} мин."
                )
            else:
                # Lockout expired, reset attempts
                user.finpass_attempts = 0
                user.finpass_locked_until = None
                await self.session.commit()

        # Verify password using model method
        is_valid = user.verify_financial_password(password)

        if is_valid:
            # Reset attempts on success
            should_commit = False

            if user.finpass_attempts > 0 or user.finpass_locked_until:
                user.finpass_attempts = 0
                user.finpass_locked_until = None
                should_commit = True

            # Unblock earnings if blocked (Recovery Logic - First successful use unblocks)
            if getattr(user, "earnings_blocked", False):
                user.earnings_blocked = False
                logger.info(
                    f"User {user_id} earnings unblocked after successful "
                    f"finpass verification"
                )
                should_commit = True

            if should_commit:
                await self.session.commit()

            return True, None
        else:
            # Increment attempts
            user.finpass_attempts = (user.finpass_attempts or 0) + 1
            attempts_left = MAX_ATTEMPTS - user.finpass_attempts

            if user.finpass_attempts >= MAX_ATTEMPTS:
                user.finpass_locked_until = datetime.now(UTC) + timedelta(minutes=LOCKOUT_MINUTES)
                await self.session.commit()
                return False, (
                    f"🔒 Превышено количество попыток!\n\n"
                    f"Аккаунт заблокирован на {LOCKOUT_MINUTES} минут."
                )

            await self.session.commit()
            return False, (
                f"❌ Неверный финансовый пароль.\n"
                f"Осталось попыток: {attempts_left}"
            )
