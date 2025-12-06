"""
Blacklist checking utilities for registration flow.

Contains functions to check if user/wallet is blacklisted.
"""

from loguru import logger
from sqlalchemy.exc import DatabaseError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blacklist import Blacklist, BlacklistActionType
from app.repositories.blacklist_repository import BlacklistRepository
from app.services.blacklist_service import BlacklistService


async def check_registration_blacklist(
    telegram_id: int,
    session: AsyncSession,
) -> tuple[bool, str | None]:
    """
    Check if user is blacklisted from registration.

    Args:
        telegram_id: User's telegram ID
        session: Database session

    Returns:
        Tuple of (is_blocked, error_message)
    """
    try:
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(telegram_id)

        if blacklist_entry and blacklist_entry.is_active:
            if blacklist_entry.action_type == BlacklistActionType.REGISTRATION_DENIED:
                logger.info(
                    f"[START] Registration denied for telegram_id {telegram_id}"
                )
                return True, (
                    "❌ Регистрация недоступна.\n"
                    "Обратитесь в поддержку."
                )
    except (OperationalError, InterfaceError, DatabaseError) as e:
        logger.error(
            f"Database error checking registration blacklist for {telegram_id}: {e}",
            exc_info=True,
        )
        return True, "⚠️ Системная ошибка. Попробуйте позже."

    return False, None


async def check_wallet_blacklist(
    wallet_address: str,
    session: AsyncSession,
) -> tuple[bool, str | None]:
    """
    Check if wallet is blacklisted.

    Args:
        wallet_address: Wallet address to check
        session: Database session

    Returns:
        Tuple of (is_blocked, error_message)
    """
    try:
        blacklist_service = BlacklistService(session)
        if await blacklist_service.is_blacklisted(
            wallet_address=wallet_address.lower()
        ):
            return True, "❌ Регистрация запрещена. Обращайтесь в поддержку."
    except (OperationalError, InterfaceError, DatabaseError) as e:
        logger.error(
            f"Database error checking wallet blacklist: {e}",
            exc_info=True,
        )
        return True, "⚠️ Системная ошибка. Попробуйте позже или обратитесь в поддержку."

    return False, None


async def get_blacklist_entry(
    telegram_id: int,
    session: AsyncSession | None,
) -> Blacklist | None:
    """
    Get blacklist entry for user.

    Args:
        telegram_id: User's telegram ID
        session: Database session (optional)

    Returns:
        Blacklist entry if found, None otherwise
    """
    if not session:
        return None

    try:
        blacklist_repo = BlacklistRepository(session)
        return await blacklist_repo.find_by_telegram_id(telegram_id)
    except Exception as e:
        logger.warning(
            f"Failed to get blacklist entry for user {telegram_id}: {e}"
        )
        return None
