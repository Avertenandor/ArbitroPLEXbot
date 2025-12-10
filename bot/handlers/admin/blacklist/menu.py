"""
Blacklist menu display handler.

Displays the main blacklist management interface with recent entries.
"""

from typing import Any

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.blacklist_service import BlacklistService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_blacklist_keyboard


router = Router()


@router.message(F.text.in_({"🚫 Управление черным списком", "🚫 Управление blacklist"}))
async def show_blacklist(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show blacklist management menu."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    blacklist_service = BlacklistService(session)

    active_count = await blacklist_service.count_active()
    entries = await blacklist_service.get_all_active(limit=10)

    text = (
        f"🚫 **Управление черным списком**\n\nВсего "
        f"заблокировано: {active_count}\n\n"
    )

    if entries:
        text += "**Последние записи:**\n\n"
        for entry in entries:
            from app.models.blacklist import BlacklistActionType

            action_type_text = {
                BlacklistActionType.REGISTRATION_DENIED: "🚫 Отказ в регистрации",
                BlacklistActionType.TERMINATED: "❌ Терминация",
                BlacklistActionType.BLOCKED: "⚠️ Блокировка",
            }.get(entry.action_type, entry.action_type)

            status_emoji = "🟢" if entry.is_active else "⚫"
            status_text = "Активна" if entry.is_active else "Неактивна"

            created_date = entry.created_at.strftime("%d.%m.%Y %H:%M")
            reason_preview = entry.reason[:60] if entry.reason else 'N/A'
            if entry.reason and len(entry.reason) > 60:
                reason_preview += "..."

            text += (
                f"{status_emoji} **#{entry.id}** - {status_text}\n"
                f"👤 Telegram: {entry.telegram_id or 'N/A'}\n"
                f"📋 Тип: {action_type_text}\n"
                f"📝 Причина: {reason_preview}\n"
                f"📅 Создано: {created_date}\n"
                f"─────────────────────────────\n\n"
            )

        text += "\n**Действия:**\n"
        text += "• `Просмотр #ID` - детали записи\n"
        text += "• `Разблокировать #ID` - удалить из черного списка"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_blacklist_keyboard(),
    )


@router.message(F.text == "👑 Админ-панель")
async def handle_back_to_admin_panel(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to admin panel from blacklist menu."""
    from bot.handlers.admin.panel import handle_admin_panel_button

    await handle_admin_panel_button(message, session, **data)
