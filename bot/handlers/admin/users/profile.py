"""
Admin User Profile Handler
Handles user profile display with detailed information
"""

import re
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import get_admin_or_deny
from bot.keyboards.reply import admin_user_profile_keyboard
from bot.utils.admin_utils import clear_state_preserve_admin_token
from bot.utils.formatters import escape_md

router = Router(name="admin_users_profile")


@router.message(F.text.regexp(r"^профиль\s+(\d+)$", flags=re.IGNORECASE | re.UNICODE))
async def handle_profile_by_id_command(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Open user profile card by explicit command: 'профиль <User ID>'.
    Удобно вызывать из других админских разделов (например, заявок на вывод).
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    match = re.match(r"^профиль\s+(\d+)$", message.text.strip(), re.IGNORECASE | re.UNICODE)
    if not match:
        await message.answer(
            "❌ Неверный формат. Используйте: `профиль <User ID>`",
        )
        return

    user_id = int(match.group(1))

    user_service = UserService(session)
    user = await user_service.get_by_id(user_id)
    if not user:
        await message.answer(f"❌ Пользователь с ID `{user_id}` не найден.")
        return

    await show_user_profile(message, user, state, session)


async def show_user_profile(
    message: Message,
    user: Any,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Show user profile and actions"""
    await clear_state_preserve_admin_token(state)
    await state.update_data(selected_user_id=user.id)

    user_service = UserService(session)
    balance_data = await user_service.get_user_balance(user.id)

    status_emoji = "🚫" if user.is_banned else "✅"
    status_text = "Заблокирован" if user.is_banned else "Активен"

    # Get additional info
    referrer_info = "Не приглашен"
    if user.referrer_id:
        referrer = await user_service.get_by_id(user.referrer_id)
        if referrer:
            r_username = escape_md(referrer.username) if referrer.username else None
            referrer_info = f"@{r_username}" if r_username else f"ID {referrer.telegram_id}"

    fin_pass_status = "🔑 Установлен (Hash)" if user.financial_password else "❌ Не установлен"
    fin_pass_hash = f"`{user.financial_password[:15]}...`" if user.financial_password else ""

    verification_status = "✅ Да" if user.is_verified else "❌ Нет"

    phone = escape_md(user.phone) if user.phone else "Не указан"
    email = escape_md(user.email) if user.email else "Не указан"
    wallet = f"`{user.wallet_address}`" if user.wallet_address else "Не указан"

    last_active = user.last_active.strftime('%d.%m.%Y %H:%M') if user.last_active else "Неизвестно"

    # Flags
    flags = []
    if user.is_admin:
        flags.append("👑 Админ")
    if user.earnings_blocked:
        flags.append("⛔️ Начисления заблокированы")
    if user.withdrawal_blocked:
        flags.append("⛔️ Вывод заблокирован")
    if user.suspicious:
        flags.append("⚠️ Подозрительный")
    flags_text = ", ".join(flags) if flags else "Нет особых отметок"

    username_display = escape_md(user.username) if user.username else "Не указан"

    text = (
        f"👤 **Личное дело пользователя**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: `{user.id}`\n"
        f"📱 Telegram ID: `{user.telegram_id}`\n"
        f"👤 Username: @{username_display}\n"
        f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"🕒 Активность: {last_active}\n"
        f"📊 Статус: {status_emoji} **{status_text}**\n"
        f"✅ Верификация: {verification_status}\n"
        f"🏷 Язык: {user.language or 'ru'}\n"
        f"👥 Пригласил: {referrer_info}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔐 **Безопасность:**\n"
        f"• Фин. пароль: {fin_pass_status} {fin_pass_hash}\n"
        f"• Особые отметки: {flags_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📞 **Контакты:**\n"
        f"• Телефон: {phone}\n"
        f"• Email: {email}\n"
        f"• Кошелек: {wallet}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Финансы:**\n"
        f"• Баланс: `{balance_data['total_balance']:.2f} USDT`\n"
        f"• Депозиты: `{balance_data['total_deposits']:.2f} USDT`\n"
        f"• Выводы: `{balance_data['total_withdrawals']:.2f} USDT`\n"
        f"• Заработано: `{balance_data['total_earnings']:.2f} USDT`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💎 **Депозит (из блокчейна):**\n"
        f"• Всего внесено: `{user.total_deposited_usdt:.2f} USDT`\n"
        f"• Статус: {user.deposit_status_text}\n"
        f"• PLEX в сутки: `{int(user.required_daily_plex):,}`\n"
        f"• Транзакций: `{user.deposit_tx_count}`\n"
    )

    # Add last scan date
    if user.last_deposit_scan_at:
        last_scan = user.last_deposit_scan_at.strftime('%d.%m.%Y %H:%M')
    else:
        last_scan = 'Не сканировался'

    text += (
        f"• Последнее сканирование: {last_scan}\n\n"
        f"Выберите действие:"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_user_profile_keyboard(user.is_banned),
    )
