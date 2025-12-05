"""
Admin blockchain settings handler.

Uses reply keyboard buttons instead of inline for better UX consistency.
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from app.services.blockchain_service import get_blockchain_service
from bot.keyboards.admin.blockchain_keyboards import blockchain_settings_keyboard
from bot.keyboards.reply import get_admin_keyboard_from_data

router = Router()


async def get_status_text() -> str:
    """Get formatted status text for blockchain settings."""
    bs = get_blockchain_service()
    # Force refresh local settings from DB just in case
    await bs.force_refresh_settings()

    status = await bs.get_providers_status()

    text = "📡 *Управление Блокчейном*\n\n"
    text += f"Текущий провайдер: *{bs.active_provider_name.upper()}*\n"
    text += f"Авто-смена: *{'ВКЛ' if bs.is_auto_switch_enabled else 'ВЫКЛ'}*\n\n"

    text += "*Статус провайдеров:*\n"
    for name, data in status.items():
        icon = "✅" if data.get("connected") else "❌"
        active_mark = " (ACTIVE)" if data.get("active") else ""
        block = data.get("block", "N/A")
        error = f" Error: {data.get('error')}" if data.get("error") else ""
        text += f"{icon} *{name.upper()}*{active_mark}: Block {block}{error}\n"

    return text


async def show_blockchain_menu(message: Message, session: AsyncSession) -> None:
    """Show blockchain settings menu with reply keyboard."""
    text = await get_status_text()
    bs = get_blockchain_service()

    await message.answer(
        text,
        reply_markup=blockchain_settings_keyboard(
            bs.active_provider_name, bs.is_auto_switch_enabled
        ),
        parse_mode="Markdown",
    )


@router.message(F.text == "📡 Блокчейн Настройки")
async def show_blockchain_settings(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show blockchain settings menu."""
    await show_blockchain_menu(message, session)


@router.message(F.text.in_({"QuickNode", "✅ QuickNode"}))
async def handle_set_quicknode(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Set QuickNode as active provider."""
    repo = GlobalSettingsRepository(session)
    bs = get_blockchain_service()

    await repo.update_settings(active_rpc_provider="quicknode")
    await session.commit()
    await bs.force_refresh_settings()

    await message.answer("✅ Провайдер изменён на QuickNode")
    await show_blockchain_menu(message, session)


@router.message(F.text.in_({"NodeReal", "✅ NodeReal"}))
async def handle_set_nodereal(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Set NodeReal as active provider."""
    repo = GlobalSettingsRepository(session)
    bs = get_blockchain_service()

    await repo.update_settings(active_rpc_provider="nodereal")
    await session.commit()
    await bs.force_refresh_settings()

    await message.answer("✅ Провайдер изменён на NodeReal")
    await show_blockchain_menu(message, session)


@router.message(F.text.in_({"✅ Авто-смена ВКЛ", "❌ Авто-смена ВЫКЛ"}))
async def handle_toggle_auto_switch(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle auto-switch setting."""
    repo = GlobalSettingsRepository(session)
    bs = get_blockchain_service()

    # First ensure we have latest settings
    await bs.force_refresh_settings()
    new_val = not bs.is_auto_switch_enabled
    await repo.update_settings(is_auto_switch_enabled=new_val)
    await session.commit()
    await bs.force_refresh_settings()

    status = "включена" if new_val else "выключена"
    await message.answer(f"✅ Авто-смена провайдера {status}")
    await show_blockchain_menu(message, session)


@router.message(F.text == "🔄 Обновить статус")
async def handle_refresh_status(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Refresh blockchain status."""
    await show_blockchain_menu(message, session)


@router.message(F.text == "◀️ Назад в админку")
async def handle_back_to_admin(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to admin panel."""
    await message.answer(
        "👑 **Панель администратора**\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard_from_data(data),
    )
