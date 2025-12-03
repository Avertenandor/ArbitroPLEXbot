"""
Admin Access Control Utilities

This module provides reusable functions for checking admin access permissions
and managing admin-related operations. These utilities are extracted from
repeated patterns across admin handler modules to reduce code duplication.

Usage:
    from bot.handlers.admin.utils.admin_checks import get_admin_or_deny

    async def my_handler(message: Message, session: AsyncSession, **data):
        admin = await get_admin_or_deny(message, session, require_super=True)
        if not admin:
            return  # Message already sent to user

        # Continue with admin operation
        ...
"""

from typing import Any

from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.services.admin_service import AdminService

# Role display mapping for consistent UI text
ROLE_DISPLAY = {
    "super_admin": "👑 Супер-админ",
    "extended_admin": "💼 Расширенный админ",
    "admin": "👨‍💼 Админ",
    "moderator": "👮 Модератор",
}


async def check_admin_access(
    session: AsyncSession,
    telegram_id: int,
    require_super: bool = False,
    require_extended: bool = False,
) -> tuple[bool, Admin | None, str | None]:
    """
    Check if user has admin access.

    This function verifies admin credentials and role requirements.
    It's the core access control function used by all admin operations.

    Args:
        session: Database session
        telegram_id: Telegram user ID to check
        require_super: If True, requires super_admin role
        require_extended: If True, requires extended_admin or super_admin role

    Returns:
        Tuple of (has_access, admin_object, error_message):
        - has_access: Boolean indicating if access is granted
        - admin_object: Admin model instance if found, None otherwise
        - error_message: Error message if access denied, None otherwise

    Examples:
        >>> has_access, admin, error = await check_admin_access(
        ...     session, 123456789, require_super=True
        ... )
        >>> if not has_access:
        ...     await message.answer(error)
        ...     return
    """
    admin_service = AdminService(session)
    admin = await admin_service.get_admin_by_telegram_id(telegram_id)

    if not admin:
        return False, None, "❌ Эта функция доступна только администраторам"

    if require_super and not admin.is_super_admin:
        return (
            False,
            admin,
            "❌ Эта функция доступна только супер-администраторам"
        )

    if require_extended and admin.role not in ["extended_admin", "super_admin"]:
        return (
            False,
            admin,
            "⛔ У вас недостаточно прав для этой операции."
        )

    return True, admin, None


async def get_admin_or_deny(
    message: Message,
    session: AsyncSession,
    require_super: bool = False,
    require_extended: bool = False,
    **data: Any,
) -> Admin | None:
    """
    Get admin or send denial message.

    This is a convenience wrapper around check_admin_access that automatically
    sends the error message to the user if access is denied.

    Args:
        message: Telegram message to reply to if access denied
        session: Database session
        require_super: If True, requires super_admin role
        require_extended: If True, requires extended_admin or super_admin role
        **data: Handler data dict (can contain 'admin' key)

    Returns:
        Admin object if access granted, None otherwise (message already sent)

    Examples:
        >>> admin = await get_admin_or_deny(message, session, require_super=True)
        >>> if not admin:
        ...     return  # Error message already sent
        >>>
        >>> # Continue with admin operation
        >>> await admin_service.do_something(admin.id)
    """
    # Check if admin is already in data (from middleware)
    admin: Admin | None = data.get("admin")
    is_admin = data.get("is_admin", False)

    # Fast path: check middleware data first
    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return None

    # Get telegram_id from message
    telegram_id = message.from_user.id if message.from_user else None
    if not telegram_id:
        await message.answer("❌ Не удалось определить пользователя")
        return None

    # Verify admin access with role requirements
    has_access, admin, error = await check_admin_access(
        session,
        telegram_id,
        require_super=require_super,
        require_extended=require_extended,
    )

    if not has_access:
        await message.answer(error or "❌ Доступ запрещён")
        return None

    return admin


def is_last_super_admin(admin: Admin, all_admins: list[Admin]) -> bool:
    """
    Check if this is the last super admin.

    This function prevents critical operations (like deletion or role change)
    on the last remaining super admin to ensure there's always at least one
    super admin in the system.

    Args:
        admin: Admin object to check
        all_admins: List of all admin objects in the system

    Returns:
        True if this is the last super admin, False otherwise

    Examples:
        >>> if is_last_super_admin(admin, all_admins):
        ...     await message.answer("❌ Нельзя удалить последнего супер-администратора")
        ...     return
    """
    if not admin.is_super_admin:
        return False

    super_admins = [a for a in all_admins if a.is_super_admin]
    return len(super_admins) == 1


async def format_role_display(role: str) -> str:
    """
    Convert role to display text with emoji.

    Args:
        role: Role string (e.g., "super_admin", "admin", "moderator")

    Returns:
        Formatted role display text with emoji

    Examples:
        >>> display = await format_role_display("super_admin")
        >>> print(display)
        👑 Супер-админ
    """
    return ROLE_DISPLAY.get(role, f"❓ {role}")


async def check_self_operation(
    admin: Admin,
    target_admin_id: int,
    operation: str = "эту операцию"
) -> tuple[bool, str | None]:
    """
    Check if admin is trying to perform operation on themselves.

    Some operations (like deletion or blocking) should not be allowed
    on the admin's own account.

    Args:
        admin: Current admin performing the operation
        target_admin_id: ID of admin being operated on
        operation: Description of operation for error message

    Returns:
        Tuple of (is_allowed, error_message):
        - is_allowed: False if trying to operate on self
        - error_message: Error message if not allowed, None otherwise

    Examples:
        >>> is_allowed, error = await check_self_operation(
        ...     admin, target_id, "удалить"
        ... )
        >>> if not is_allowed:
        ...     await message.answer(error)
        ...     return
    """
    if admin.id == target_admin_id:
        return False, f"❌ Нельзя выполнить {operation} на самого себя"

    return True, None


async def verify_admin_permissions(
    admin: Admin,
    target_admin: Admin,
) -> tuple[bool, str | None]:
    """
    Verify that admin has permission to modify target admin.

    Business rules:
    - Only super_admin can modify other admins
    - Cannot modify an admin with equal or higher role
    - Cannot be the last super_admin

    Args:
        admin: Current admin performing the operation
        target_admin: Admin being modified

    Returns:
        Tuple of (has_permission, error_message):
        - has_permission: True if operation is allowed
        - error_message: Error message if not allowed, None otherwise

    Examples:
        >>> has_perm, error = await verify_admin_permissions(admin, target_admin)
        >>> if not has_perm:
        ...     await message.answer(error)
        ...     return
    """
    # Only super_admin can modify admins
    if not admin.is_super_admin:
        return (
            False,
            "❌ Только супер-администраторы могут управлять другими админами"
        )

    # Cannot modify yourself
    if admin.id == target_admin.id:
        return False, "❌ Нельзя изменить свои собственные права"

    # Role hierarchy check (optional, can be removed if not needed)
    role_hierarchy = {
        "moderator": 1,
        "admin": 2,
        "extended_admin": 3,
        "super_admin": 4,
    }

    admin_level = role_hierarchy.get(admin.role, 0)
    target_level = role_hierarchy.get(target_admin.role, 0)

    if target_level >= admin_level:
        return (
            False,
            "❌ Нельзя изменять админа с равным или выше уровнем доступа"
        )

    return True, None


async def get_role_display_map() -> dict[str, str]:
    """
    Get full role display mapping dictionary.

    Returns:
        Dictionary mapping role keys to display strings

    Examples:
        >>> role_map = await get_role_display_map()
        >>> for role, display in role_map.items():
        ...     print(f"{role}: {display}")
    """
    return ROLE_DISPLAY.copy()


async def format_admin_list(
    admins: list[Admin],
    admin_service: AdminService,
    include_creator: bool = True,
) -> str:
    """
    Format list of admins for display.

    Args:
        admins: List of Admin objects to format
        admin_service: AdminService instance for fetching creator info
        include_creator: Whether to include creator information

    Returns:
        Formatted text string ready for display

    Examples:
        >>> text = await format_admin_list(admins, admin_service)
        >>> await message.answer(text, parse_mode="Markdown")
    """
    if not admins:
        return "_Список админов пуст_"

    lines = []
    for idx, admin in enumerate(admins, 1):
        role_display = ROLE_DISPLAY.get(admin.role, admin.role)

        creator_info = ""
        if include_creator and admin.created_by:
            creator = await admin_service.get_admin_by_id(admin.created_by)
            if creator:
                creator_info = f" (создан {creator.display_name})"

        lines.append(
            f"{idx}. {admin.display_name}\n"
            f"   ID: `{admin.telegram_id}`\n"
            f"   Роль: {role_display}{creator_info}"
        )

    return "\n\n".join(lines)
