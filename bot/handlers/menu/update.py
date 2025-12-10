"""
Update deposit handlers.

This module contains handlers for scanning and updating user deposit status.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from app.services.deposit_scan_service import DepositScanService
from bot.keyboards.reply import main_menu_reply_keyboard


router = Router()


@router.message(StateFilter('*'), F.text == "🔄 Обновить депозит")
async def handle_update_deposit(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle deposit scan request from user."""
    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)

    if not user:
        await message.answer(
            "❌ Пользователь не найден. Пожалуйста, введите /start для регистрации."
        )
        return

    await state.clear()
    await message.answer("⏳ Сканируем ваши депозиты на блокчейне...")

    try:
        deposit_service = DepositScanService(session)
        scan_result = await deposit_service.scan_and_validate(user.id)

        if not scan_result.get("success"):
            await message.answer(
                f"⚠️ Ошибка сканирования: {scan_result.get('error', 'Неизвестная ошибка')}\n\n"
                "Попробуйте позже."
            )
            return

        total_deposit = scan_result.get("total_amount", 0)
        tx_count = scan_result.get("tx_count", 0)
        is_active = scan_result.get("is_valid", False)
        required_plex = scan_result.get("required_plex", 0)

        await session.commit()

        status_emoji = "✅" if is_active else "❌"
        status_text = "Активен" if is_active else "Неактивен (< 30 USDT)"

        text = (
            f"💳 **Статус вашего депозита**\n\n"
            f"{status_emoji} **Статус:** {status_text}\n"
            f"💰 **Общий депозит:** {total_deposit:.2f} USDT\n"
            f"📊 **Транзакций:** {tx_count}\n"
            f"💎 **Требуется PLEX в сутки:** {int(required_plex):,} PLEX\n\n"
        )

        if not is_active:
            text += (
                f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⚠️ **Для активации депозита необходимо минимум 30 USDT.**\n\n"
                f"💳 **Кошелек для пополнения:**\n"
                f"`{settings.system_wallet_address}`\n\n"
                f"⚠️ Отправляйте только **USDT (BEP-20)** на сети BSC!"
            )
        else:
            text += (
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "✅ Ваш депозит активен.\n"
                "Не забывайте ежедневно пополнять PLEX для работы депозита!"
            )

        await message.answer(text, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Deposit scan error: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

    # Get blacklist info for menu
    blacklist_entry = None
    try:
        blacklist_repo = BlacklistRepository(session)
        if message.from_user:
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                message.from_user.id
            )
    except Exception:
        pass

    await message.answer(
        "⬅️ Главное меню:",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )
