"""
Admin emergency stop handler.

R17-3: Allows super_admin to toggle emergency stop flags for
deposits, withdrawals and ROI accruals via reply keyboard buttons.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from app.utils.cache_invalidation import invalidate_global_settings_cache
from bot.keyboards.admin.emergency_keyboards import emergency_stops_keyboard
from bot.keyboards.reply import get_admin_keyboard_from_data


router = Router()


def _format_status_flag(enabled: bool) -> str:
    return "⏸ Остановлено" if enabled else "▶ Активно"


async def show_emergency_menu(
    message: Message,
    session: AsyncSession,
    data: dict,
) -> None:
    """Show emergency stops menu with current status."""
    repo = GlobalSettingsRepository(session)
    settings = await repo.get_settings()

    text = (
        "🚨 **Аварийные стопы платформы**\n\n"
        "Используйте эти флаги только при инцидентах (ошибка блокчейна, "
        "подозрение на взлом, критические баги).\n\n"
        f"💰 Депозиты: {_format_status_flag(settings.emergency_stop_deposits)}\n"
        f"💸 Выводы: {_format_status_flag(settings.emergency_stop_withdrawals)}\n"
        f"📈 Начисление ROI: {_format_status_flag(settings.emergency_stop_roi)}\n\n"
        "Нажмите кнопку для переключения статуса."
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=emergency_stops_keyboard(
            deposits_stopped=settings.emergency_stop_deposits,
            withdrawals_stopped=settings.emergency_stop_withdrawals,
            roi_stopped=settings.emergency_stop_roi,
        ),
    )


@router.message(F.text == "🚨 Аварийные стопы")
async def show_emergency_menu_handler(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show emergency stop status and controls."""
    is_admin = data.get("is_admin", False)
    is_super_admin = data.get("is_super_admin", False)

    if not is_admin:
        await message.answer("❌ Эта функция доступна только администраторам")
        return

    if not is_super_admin:
        await message.answer(
            "❌ Доступ к управлению аварийными стопами есть только у супер-админа."
        )
        return

    await show_emergency_menu(message, session, data)


@router.message(F.text.in_({"⏸ Остановить депозиты", "▶️ Запустить депозиты"}))
async def handle_toggle_deposits(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle deposits emergency stop."""
    is_super_admin = data.get("is_super_admin", False)
    if not is_super_admin:
        await message.answer("❌ Доступ только для супер-админа")
        return

    redis_client = data.get("redis_client")
    repo = GlobalSettingsRepository(session, redis_client)
    settings = await repo.get_settings()

    new_value = not settings.emergency_stop_deposits
    await repo.update_settings(emergency_stop_deposits=new_value)

    status = "остановлены" if new_value else "запущены"
    await message.answer(f"✅ Депозиты {status}")
    await show_emergency_menu(message, session, data)


@router.message(F.text.in_({"⏸ Остановить выводы", "▶️ Запустить выводы"}))
async def handle_toggle_withdrawals(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle withdrawals emergency stop."""
    is_super_admin = data.get("is_super_admin", False)
    if not is_super_admin:
        await message.answer("❌ Доступ только для супер-админа")
        return

    redis_client = data.get("redis_client")
    repo = GlobalSettingsRepository(session, redis_client)
    settings = await repo.get_settings()

    new_value = not settings.emergency_stop_withdrawals
    await repo.update_settings(emergency_stop_withdrawals=new_value)

    status = "остановлены" if new_value else "запущены"
    await message.answer(f"✅ Выводы {status}")
    await show_emergency_menu(message, session, data)


@router.message(F.text.in_({"⏸ Остановить ROI", "▶️ Запустить ROI"}))
async def handle_toggle_roi(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle ROI emergency stop."""
    is_super_admin = data.get("is_super_admin", False)
    if not is_super_admin:
        await message.answer("❌ Доступ только для супер-админа")
        return

    redis_client = data.get("redis_client")
    repo = GlobalSettingsRepository(session, redis_client)
    settings = await repo.get_settings()

    new_value = not settings.emergency_stop_roi
    await repo.update_settings(emergency_stop_roi=new_value)

    status = "остановлено" if new_value else "запущено"
    await message.answer(f"✅ Начисление ROI {status}")
    await show_emergency_menu(message, session, data)


@router.message(F.text == "🔄 Обновить статус стопов")
async def handle_refresh_emergency_status(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Refresh emergency stops status."""
    is_super_admin = data.get("is_super_admin", False)
    if not is_super_admin:
        await message.answer("❌ Доступ только для супер-админа")
        return

    await show_emergency_menu(message, session, data)


@router.message(F.text == "◀️ Назад в админку")
async def handle_back_to_admin_from_emergency(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to admin panel from emergency stops."""
    await message.answer(
        "👑 **Панель администратора**\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard_from_data(data),
    )
