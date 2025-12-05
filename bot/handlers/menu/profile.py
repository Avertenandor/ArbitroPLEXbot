"""
Profile menu handlers.

This module contains handlers for displaying user profile and downloading reports.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import BufferedInputFile, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.user import User
from app.services.deposit_service import DepositService
from app.services.report_service import ReportService
from app.services.user_service import UserService
from bot.keyboards.reply import profile_keyboard
from bot.utils.formatters import format_usdt
from bot.utils.text_utils import escape_markdown
from bot.utils.user_loader import UserLoader

router = Router()


@router.message(StateFilter('*'), F.text == "👤 Мой профиль")
async def show_my_profile(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show detailed user profile."""
    telegram_id = message.from_user.id if message.from_user else None
    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    user_service = UserService(session)
    deposit_service = DepositService(session)

    # Get user stats
    stats = await user_service.get_user_stats(user.id)

    # Get user balance
    balance = await user_service.get_user_balance(user.id)

    # Get ROI progress for level 1
    roi_progress = await deposit_service.get_level1_roi_progress(user.id)

    # Get referral link
    bot_username = settings.telegram_bot_username
    referral_link = user_service.generate_referral_link(user, bot_username)

    # Build ROI section
    roi_section = ""
    if roi_progress.get("has_active_deposit") and not roi_progress.get(
        "is_completed"
    ):
        progress_percent = roi_progress.get("roi_percent", 0)
        filled = round((progress_percent / 100) * 10)
        empty = 10 - filled
        progress_bar = "█" * filled + "░" * empty

        deposit_amt = format_usdt(roi_progress.get('deposit_amount', 0))
        roi_paid = format_usdt(roi_progress.get('roi_paid', 0))
        roi_remaining = format_usdt(roi_progress.get('roi_remaining', 0))
        roi_cap = format_usdt(roi_progress.get('roi_cap', 0))

        roi_section = (
            f"\n*🎯 ROI Прогресс (Уровень 1):*\n"
            f"💵 Депозит: {deposit_amt} USDT\n"
            f"📊 Прогресс: {progress_bar} {progress_percent:.1f}%\n"
            f"✅ Получено: {roi_paid} USDT\n"
            f"⏳ Осталось: {roi_remaining} USDT\n"
            f"🎯 Цель: {roi_cap} USDT (500%)\n\n"
        )
    elif roi_progress.get("has_active_deposit") and roi_progress.get(
        "is_completed"
    ):
        roi_section = (
            f"\n*🎯 ROI Завершён (Уровень 1):*\n"
            f"✅ Достигнут максимум 500%!\n"
            f"💰 Получено: {format_usdt(roi_progress.get('roi_paid', 0))}"
                "USDT\n"
            f"📌 Создайте новый депозит чтобы продолжить\n\n"
        )

    # Format wallet address
    wallet_display = user.wallet_address
    if len(user.wallet_address) > 20:
        wallet_display = (
            f"{user.wallet_address[:10]}...{user.wallet_address[-8:]}"
        )

    # Prepare status strings
    verify_emoji = '✅' if user.is_verified else '❌'
    verify_status = 'Пройдена' if user.is_verified else 'Не пройдена'
    account_status = (
        '🚫 Аккаунт заблокирован' if user.is_banned else '✅ Аккаунт активен'
    )

    # Format balance values
    available = format_usdt(balance.get('available_balance', 0))
    total_earned = format_usdt(balance.get('total_earned', 0))
    pending = format_usdt(balance.get('pending_earnings', 0))

    # Escape username for Markdown
    safe_username = escape_markdown(user.username) if user.username else 'не указан'

    text = (
        f"👤 *Ваш профиль*\n\n"
        f"*Основная информация:*\n"
        f"🆔 ID: `{user.id}`\n"
        f"👤 Username: @{safe_username}\n"
        f"💳 Кошелек: `{wallet_display}`\n\n"
        f"*Статус:*\n"
        f"{verify_emoji} Верификация: {verify_status}\n"
    )

    # Add warning for unverified users
    if not user.is_verified:
        text += "⚠️ *Вывод недоступен* — нужен финпароль (кнопка '🔐 Получить финпароль')\n\n"

    text += (
        f"{account_status}\n\n"
        f"*Баланс:*\n"
        f"💰 Доступно для вывода: *{available} USDT*\n"
        f"💸 Всего заработано: {total_earned} USDT\n"
        f"⏳ В ожидании выплаты: {pending} USDT\n"
    )

    if balance.get("pending_withdrawals", 0) > 0:
        pending_withdrawals = format_usdt(
            balance.get('pending_withdrawals', 0)
        )
        text += f"🔒 Заблокировано в выводах: {pending_withdrawals} USDT\n"

    text += (
        f"✅ Уже выплачено: {format_usdt(balance.get('total_paid', 0))} USDT\n"
    )
    text += roi_section
    text += (
        f"*Депозиты и рефералы:*\n"
        f"💰 Всего депозитов: {format_usdt(stats.get('total_deposits', 0))}"
            "USDT\n"
        f"👥 Рефералов: {stats.get('referral_count', 0)}\n"
        f"📊 Активных уровней: {len(stats.get('activated_levels', []))}/5\n\n"
    )

    if user.phone or user.email:
        text += "*Контакты:*\n"
        if user.phone:
            text += f"📞 {user.phone}\n"
        if user.email:
            text += f"📧 {user.email}\n"
        text += "\n"

    text += (
        f"*Реферальная ссылка:*\n"
        f"`{referral_link}`\n\n"
        f"📅 Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}"
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=profile_keyboard())


@router.message(StateFilter('*'), F.text == "📂 Скачать отчет")
async def download_report(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Download user report."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    status_msg = await message.answer("⏳ Генерирую отчет...")

    try:
        report_service = ReportService(session)
        report_bytes = await report_service.generate_user_report(user.id)

        file = BufferedInputFile(report_bytes, filename=f"report_{user.id}.xlsx")

        await message.answer_document(
            document=file,
            caption="📊 Ваш полный отчет (профиль, транзакции, депозиты, рефералы)"
        )
        await status_msg.delete()
    except Exception as e:
        await status_msg.edit_text("❌ Ошибка генерации отчета")
        logger.error(f"Failed to generate report for user {user.id}: {e}", exc_info=True)
