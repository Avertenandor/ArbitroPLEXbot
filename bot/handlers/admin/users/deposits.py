"""
Admin User Deposit Scanning Handler
Handles admin-initiated deposit scanning from blockchain
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deposit_scan_service import DepositScanService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny

router = Router(name="admin_users_deposits")


@router.message(F.text == "🔄 Сканировать депозит")
async def handle_admin_scan_deposit(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Admin: Force scan user deposits from blockchain."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    user_id = state_data.get("selected_user_id")
    if not user_id:
        await message.answer("❌ Пользователь не выбран")
        return

    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    if not user:
        await message.answer("❌ Пользователь не найден")
        return

    await message.answer("⏳ Сканируем депозиты пользователя...")

    try:
        deposit_service = DepositScanService(session)
        scan_result = await deposit_service.scan_user_deposits(user_id)

        if not scan_result.get("success"):
            await message.answer(
                f"⚠️ Ошибка сканирования: {scan_result.get('error', 'Неизвестная ошибка')}"
            )
            return

        await session.commit()

        total = scan_result.get("total_amount", 0)
        tx_count = scan_result.get("tx_count", 0)
        is_active = scan_result.get("is_active", False)
        required_plex = scan_result.get("required_plex", 0)

        status_emoji = "✅" if is_active else "❌"

        await message.answer(
            f"🔄 **Результаты сканирования:**\n\n"
            f"👤 Пользователь: `{user.username or user.telegram_id}`\n"
            f"💰 Всего депозитов: `{total:.2f} USDT`\n"
            f"📊 Транзакций: `{tx_count}`\n"
            f"{status_emoji} Статус: {'Активен' if is_active else 'Неактивен (< 30 USDT)'}\n"
            f"💎 PLEX в сутки: `{int(required_plex):,}`",
            parse_mode="Markdown"
        )

        # Refresh user and show profile
        user = await user_service.get_by_id(user_id)
        # Import here to avoid circular dependency
        from bot.handlers.admin.users.profile import show_user_profile
        await show_user_profile(message, user, state, session)

    except Exception as e:
        logger.error(f"Admin deposit scan error: {e}")
        await message.answer("⚠️ Произошла ошибка при сканировании.")
