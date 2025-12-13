"""
AI Services Common Utilities.

Shared functions and classes for all AI service modules.
Eliminates code duplication across ai_*_service.py files.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository


async def verify_admin(
    session: AsyncSession,
    admin_telegram_id: int | None,
) -> tuple[Admin | None, str | None]:
    """
    Verify admin credentials.

    Args:
        session: Database session
        admin_telegram_id: Admin's Telegram ID

    Returns:
        Tuple of (admin, error_message). If admin is valid, error is None.
    """
    if not admin_telegram_id:
        return None, "❌ Не удалось определить администратора"

    admin_repo = AdminRepository(session)
    admin = await admin_repo.get_by_telegram_id(admin_telegram_id)

    if not admin:
        return None, "❌ Администратор не найден"

    if admin.is_blocked:
        return None, "❌ Администратор заблокирован"

    return admin, None


async def find_user_by_identifier(
    session: AsyncSession,
    identifier: str,
    user_repo: UserRepository | None = None,
) -> tuple[User | None, str | None]:
    """
    Find user by @username, telegram_id, or wallet address.

    Args:
        session: Database session
        identifier: User identifier (@username, telegram_id, or wallet 0x...)
        user_repo: Optional UserRepository instance (creates one if not provided)

    Returns:
        Tuple of (user, error_message). If user is found, error is None.
    """
    if user_repo is None:
        user_repo = UserRepository(session)

    identifier = identifier.strip()

    # By username (@username or plain username)
    if identifier.startswith("@"):
        username = identifier[1:]
        user = await user_repo.get_by_username(username)
        if user:
            return user, None
        return None, f"❌ Пользователь @{username} не найден"

    # Plain username (alphanumeric + underscore)
    if all(c.isalnum() or c == "_" for c in identifier) and not identifier.isdigit():
        user = await user_repo.get_by_username(identifier)
        if user:
            return user, None
        return None, f"❌ Пользователь @{identifier} не найден"

    # By telegram ID
    if identifier.isdigit():
        telegram_id = int(identifier)
        user = await user_repo.get_by_telegram_id(telegram_id)
        if user:
            return user, None
        return None, f"❌ Пользователь с ID {telegram_id} не найден"

    # By wallet address
    if identifier.startswith("0x") and len(identifier) == 42:
        stmt = select(User).where(User.wallet_address == identifier)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            return user, None
        return None, f"❌ Пользователь с кошельком {identifier[:10]}... не найден"

    return None, "❌ Укажите @username, telegram_id или адрес кошелька"


class AIServiceResponse:
    """
    Standard response builder for AI services.

    Provides consistent response format across all AI services.
    """

    @staticmethod
    def success(message: str, **extra: Any) -> dict[str, Any]:
        """
        Create a success response.

        Args:
            message: Success message
            **extra: Additional fields to include

        Returns:
            Response dictionary with success=True
        """
        return {"success": True, "message": message, **extra}

    @staticmethod
    def error(error: str, **extra: Any) -> dict[str, Any]:
        """
        Create an error response.

        Args:
            error: Error message
            **extra: Additional fields to include

        Returns:
            Response dictionary with success=False
        """
        return {"success": False, "error": error, **extra}

    @staticmethod
    def data(data: Any, message: str | None = None) -> dict[str, Any]:
        """
        Create a data response.

        Args:
            data: Data to return
            message: Optional message

        Returns:
            Response dictionary with success=True and data
        """
        result: dict[str, Any] = {"success": True, "data": data}
        if message:
            result["message"] = message
        return result


# Convenience aliases
response = AIServiceResponse()
