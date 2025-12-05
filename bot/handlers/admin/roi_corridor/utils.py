"""
ROI Corridor utilities.

Contains utility functions for navigation and notifications.
"""

from __future__ import annotations

from typing import Any

from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.admin.panel import handle_admin_panel_button
from bot.keyboards.buttons import AdminButtons, NavigationButtons
from bot.utils.admin_utils import clear_state_preserve_admin_token


async def check_cancel_or_back(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> bool:
    """
    Check for navigation buttons (cancel/back to admin).

    Returns True if should stop processing (navigation occurred).
    """
    # Import here to avoid circular dependency
    from bot.handlers.admin.roi_corridor.menu import show_roi_corridor_menu

    if message.text == AdminButtons.ADMIN_PANEL:
        await clear_state_preserve_admin_token(state)
        await handle_admin_panel_button(message, session, **data)
        return True

    if message.text == NavigationButtons.CANCEL_ARROW:
        await clear_state_preserve_admin_token(state)
        await show_roi_corridor_menu(message, session, **data)
        return True

    return False


async def notify_other_admins(
    session: AsyncSession,
    admin_id: int,
    level: int,
    mode_text: str,
    config_text: str,
    applies_text: str,
) -> None:
    """
    Notify other admins about corridor change.

    Args:
        session: Database session
        admin_id: Admin who made the change
        level: Changed level
        mode_text: Mode description
        config_text: Configuration description
        applies_text: Application scope description
    """
    try:
        from app.repositories.admin_repository import AdminRepository

        admin_repo = AdminRepository(session)
        all_admins = await admin_repo.get_extended_admins()

        notification_text = (
            "🔔 **Изменены настройки коридора доходности**\n\n"
            f"**Уровень:** {level}\n"
            f"**Режим:** {mode_text}\n"
            f"**Значение:** {config_text}\n"
            f"**Применено к:** {applies_text}\n"
            f"**Изменил:** Admin ID {admin_id}"
        )

        for admin in all_admins:
            if admin.id != admin_id:
                try:
                    from bot.utils.notification import send_telegram_message

                    await send_telegram_message(
                        admin.telegram_id, notification_text
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to notify admin {admin.id}: {e}",
                        extra={"admin_id": admin.id, "error": str(e)},
                    )
    except Exception as e:
        logger.error(
            f"Failed to notify admins: {e}",
            extra={"error": str(e)},
        )


async def notify_other_admins_period(
    session: AsyncSession,
    admin_id: int,
    hours: int,
) -> None:
    """
    Notify other admins about period change.

    Args:
        session: Database session
        admin_id: Admin who made the change
        hours: New period in hours
    """
    try:
        from app.repositories.admin_repository import AdminRepository

        admin_repo = AdminRepository(session)
        all_admins = await admin_repo.get_extended_admins()

        notification_text = (
            "🔔 **Изменен период начисления**\n\n"
            f"**Новый период:** {hours} часов\n"
            f"**Изменил:** Admin ID {admin_id}"
        )

        for admin in all_admins:
            if admin.id != admin_id:
                try:
                    from bot.utils.notification import send_telegram_message

                    await send_telegram_message(
                        admin.telegram_id, notification_text
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to notify admin {admin.id}: {e}",
                        extra={"admin_id": admin.id, "error": str(e)},
                    )
    except Exception as e:
        logger.error(
            f"Failed to notify admins: {e}",
            extra={"error": str(e)},
        )
