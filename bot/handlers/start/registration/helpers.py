"""
Helper utilities for registration flow.

Contains various helper functions used across registration handlers.
"""

from loguru import logger
from sqlalchemy.exc import DatabaseError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


def is_skip_command(text: str | None) -> bool:
    """
    Check if text is a skip command.

    Args:
        text: Text to check

    Returns:
        True if text is a skip command
    """
    if not text:
        return False

    skip_commands = ["/skip", "пропустить", "skip"]
    return text.strip().lower() in skip_commands


def format_balance(balance: float) -> str:
    """
    Format balance to avoid scientific notation.

    Args:
        balance: Balance value

    Returns:
        Formatted balance string
    """
    balance_str = f"{balance:.8f}".rstrip('0').rstrip('.')
    if balance_str == '':
        balance_str = '0'
    return balance_str


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram Markdown.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    return (
        text.replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
        .replace("[", "\\[")
    )


async def reset_bot_blocked_flag(
    user: User,
    session: AsyncSession,
) -> None:
    """
    Reset bot_blocked flag if user unblocked the bot.

    Args:
        user: User object
        session: Database session
    """
    try:
        if hasattr(user, 'bot_blocked') and user.bot_blocked:
            user_repo = UserRepository(session)
            await user_repo.update(user.id, bot_blocked=False)
            await session.commit()
            logger.info(
                f"User {user.telegram_id} unblocked bot, flag reset in /start"
            )
    except Exception as reset_error:
        # Don't fail /start if flag reset fails
        logger.warning(f"Failed to reset bot_blocked flag: {reset_error}")


async def handle_database_error(
    error: Exception,
    operation: str,
) -> str:
    """
    Handle database errors and return user-friendly message.

    Args:
        error: Exception that occurred
        operation: Description of operation that failed

    Returns:
        User-friendly error message
    """
    logger.error(
        f"Database error during {operation}: {error}",
        exc_info=True,
    )
    return "⚠️ Системная ошибка. Попробуйте позже."


def normalize_button_text(text: str | None) -> str:
    """
    Normalize button text by removing emoji variation selectors.

    Args:
        text: Button text

    Returns:
        Normalized text
    """
    if not text:
        return ""
    # Remove FE0F (emoji variation selector)
    return text.replace("\ufe0f", "")
