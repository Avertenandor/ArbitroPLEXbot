"""
User Search Utilities.

Centralized user lookup supporting multiple input formats:
- @username
- Telegram ID (numeric)
- ID:internal_id (database primary key)
"""

from typing import TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models.user import User


async def search_user_by_input(
    user_input: str,
    session: AsyncSession,
) -> "User | None":
    """
    Universal user search supporting multiple formats.

    Args:
        user_input: @username, Telegram ID, or ID:internal_id
        session: Database session

    Returns:
        User object or None if not found

    Supported formats:
        - @username or username (search by username)
        - 123456789 (search by telegram_id)
        - ID:42 (search by internal database ID)
    """
    from app.services.user_service import UserService

    user_input = user_input.strip()
    user_service = UserService(session)

    # Format: @username
    if user_input.startswith("@"):
        return await user_service.get_by_username(user_input[1:])

    # Format: ID:internal_id
    if user_input.upper().startswith("ID:"):
        try:
            user_id = int(user_input[3:])
            return await user_service.get_by_id(user_id)
        except ValueError:
            return None

    # Format: numeric telegram_id
    if user_input.isdigit():
        return await user_service.get_by_telegram_id(int(user_input))

    # Fallback: try as username without @
    return await user_service.get_by_username(user_input)


def get_supported_formats_hint() -> str:
    """Get help text for supported user input formats."""
    return (
        "Попробуйте другой формат:\n"
        "• @username\n"
        "• Telegram ID (число)\n"
        "• ID:42 (внутренний ID)"
    )
