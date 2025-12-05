"""
Notification settings handlers.

This module contains handlers for managing user notification preferences.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_notification_service import UserNotificationService
from bot.keyboards.reply import notification_settings_reply_keyboard

router = Router()


@router.message(StateFilter('*'), F.text == "🔔 Настройки уведомлений")
async def show_notification_settings(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show notification settings menu.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    notification_service = UserNotificationService(session)
    settings = await notification_service.get_settings(user.id)
    await session.commit()

    # Build status text
    deposit_status = "✅ Включены" if settings.deposit_notifications else "❌ Выключены"
    withdrawal_status = "✅ Включены" if settings.withdrawal_notifications else "❌ Выключены"
    roi_status = "✅ Включены" if getattr(settings, 'roi_notifications', True) else "❌ Выключены"
    marketing_status = "✅ Включены" if settings.marketing_notifications else "❌ Выключены"

    text = (
        f"🔔 *Настройки уведомлений*\n\n"
        f"Управляйте уведомлениями, которые вы хотите получать:\n\n"
        f"💰 Уведомления о депозитах: {deposit_status}\n"
        f"💸 Уведомления о выводах: {withdrawal_status}\n"
        f"📊 Уведомления о ROI: {roi_status}\n"
        f"📢 Маркетинговые уведомления: {marketing_status}\n\n"
        f"Используйте кнопки ниже для изменения настроек."
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=notification_settings_reply_keyboard(
            deposit_enabled=settings.deposit_notifications,
            withdrawal_enabled=settings.withdrawal_notifications,
            roi_enabled=getattr(settings, 'roi_notifications', True),
            marketing_enabled=settings.marketing_notifications,
        ),
    )


async def _toggle_notification_setting(
    message: Message,
    session: AsyncSession,
    user: User,
    field_name: str,
) -> None:
    """
    Generic notification toggle handler.

    Args:
        message: Telegram message
        session: Database session
        user: User object
        field_name: Name of the notification field to toggle
                   (e.g., 'deposit_notifications', 'withdrawal_notifications')
    """
    notification_service = UserNotificationService(session)
    settings = await notification_service.get_settings(user.id)

    # Get current value and toggle it
    current_value = getattr(settings, field_name, True)
    new_value = not current_value

    # Update the specific field
    await notification_service.update_settings(
        user.id, **{field_name: new_value}
    )
    await session.commit()

    # Refresh settings
    settings = await notification_service.get_settings(user.id)

    # Build status text
    deposit_status = "✅ Включены" if settings.deposit_notifications else "❌ Выключены"
    withdrawal_status = "✅ Включены" if settings.withdrawal_notifications else "❌ Выключены"
    roi_status = "✅ Включены" if getattr(settings, 'roi_notifications', True) else "❌ Выключены"
    marketing_status = "✅ Включены" if settings.marketing_notifications else "❌ Выключены"

    text = (
        f"🔔 *Настройки уведомлений*\n\n"
        f"Управляйте уведомлениями, которые вы хотите получать:\n\n"
        f"💰 Уведомления о депозитах: {deposit_status}\n"
        f"💸 Уведомления о выводах: {withdrawal_status}\n"
        f"📊 Уведомления о ROI: {roi_status}\n"
        f"📢 Маркетинговые уведомления: {marketing_status}\n\n"
        f"Используйте кнопки ниже для изменения настроек."
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=notification_settings_reply_keyboard(
            deposit_enabled=settings.deposit_notifications,
            withdrawal_enabled=settings.withdrawal_notifications,
            roi_enabled=getattr(settings, 'roi_notifications', True),
            marketing_enabled=settings.marketing_notifications,
        ),
    )


@router.message(F.text.in_({
    "✅ Уведомления о депозитах",
    "❌ Уведомления о депозитах",
}))
async def toggle_deposit_notification(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle deposit notifications."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    await _toggle_notification_setting(message, session, user, "deposit_notifications")


@router.message(F.text.in_({
    "✅ Уведомления о выводах",
    "❌ Уведомления о выводах",
}))
async def toggle_withdrawal_notification(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle withdrawal notifications."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    await _toggle_notification_setting(message, session, user, "withdrawal_notifications")


@router.message(F.text.in_({
    "✅ Уведомления о ROI",
    "❌ Уведомления о ROI",
}))
async def toggle_roi_notification(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle ROI notifications."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    await _toggle_notification_setting(message, session, user, "roi_notifications")


@router.message(F.text.in_({
    "✅ Маркетинговые уведомления",
    "❌ Маркетинговые уведомления",
}))
async def toggle_marketing_notification(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle marketing notifications."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    await _toggle_notification_setting(message, session, user, "marketing_notifications")
