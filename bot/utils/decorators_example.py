"""
Example usage of common decorators.

This file demonstrates how to use the decorators in bot/utils/decorators.py
"""

from typing import Any

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.utils.decorators import (
    handle_db_errors,
    require_admin,
    require_authenticated,
    require_super_admin,
)

router = Router(name="example_decorated_handlers")


# Example 1: Require admin privileges
@router.message(F.text == "Admin Panel")
@require_admin
async def admin_panel_handler(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Handler that requires admin privileges.
    Will automatically check is_admin and block non-admins.
    """
    await message.answer("Welcome to admin panel!")


# Example 2: Require super admin privileges
@router.message(F.text == "Super Admin Settings")
@require_super_admin
async def super_admin_settings_handler(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Handler that requires super admin privileges.
    Will check both is_admin and is_super_admin flags.
    """
    await message.answer("Super admin settings...")


# Example 3: Require authentication (registered user)
@router.message(F.text == "My Profile")
@require_authenticated
async def my_profile_handler(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Handler that requires user to be registered.
    Will check if user exists in database.
    """
    user = data.get("user")
    await message.answer(f"Welcome, {user.username}!")


# Example 4: Handle database errors
@router.message(F.text == "Create Deposit")
@handle_db_errors
async def create_deposit_handler(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Handler with automatic database error handling.
    Any SQLAlchemy errors will be caught and handled gracefully.
    """
    # Code that may cause database errors
    # If an error occurs, user gets friendly message
    # and error is logged
    pass


# Example 5: Multiple decorators (stacking)
@router.message(F.text == "Admin Create User")
@handle_db_errors
@require_admin
async def admin_create_user_handler(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Handler with multiple decorators.
    Decorators are applied bottom-up:
    1. First checks admin status
    2. Then wraps with error handling
    """
    # Create user logic here
    pass


# Example 6: With callback queries
@router.callback_query(F.data == "admin_stats")
@require_admin
async def admin_stats_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Callback query handler with admin requirement.
    Works the same way as Message handlers.
    """
    await callback.answer("Loading stats...")
    await callback.message.answer("Admin statistics...")


# Example 7: Super admin with error handling
@router.message(F.text == "Reset Database")
@handle_db_errors
@require_super_admin
async def reset_database_handler(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Critical operation requiring super admin with error handling.
    Combines authorization and error handling.
    """
    # Critical database operation
    await message.answer("Database reset complete!")
