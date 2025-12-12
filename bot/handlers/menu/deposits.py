"""
Deposits listing handlers.

This module contains handlers for displaying user's active deposits with ROI progress.
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus
from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from app.services.deposit import DepositService
from bot.keyboards.inline import deposit_status_keyboard
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.utils.formatters import format_deposit_status, format_usdt


router = Router()


@router.message(StateFilter('*'), F.text == "📦 Мои депозиты")
async def show_my_deposits(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Show user's active deposits.

    Args:
        message: Telegram message
        session: Database session
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    deposit_service = DepositService(session)

    # Get active deposits (CONFIRMED only)
    active_deposits = await deposit_service.get_active_deposits(user.id)

    # Get pending deposits
    from app.repositories.deposit_repository import DepositRepository
    deposit_repo = DepositRepository(session)
    pending_deposits = await deposit_repo.find_by(
        user_id=user.id,
        status=TransactionStatus.PENDING.value
    )

    # Check if no deposits at all
    if not active_deposits and not pending_deposits:
        is_admin = data.get("is_admin", False)
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        await message.answer(
            "📦 *Мои депозиты*\n\n"
            "У вас пока нет активных депозитов.\n\n"
            "Создайте депозит через меню '💰 Депозит'.",
            parse_mode="Markdown",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return

    # Build deposits list
    text = "📦 *Мои депозиты*\n\n"

    # Show pending deposits first
    if pending_deposits:
        text += "⏳ *ДЕПОЗИТЫ В ОБРАБОТКЕ*\n\n"

        for deposit in pending_deposits:
            # Get deposit status with confirmations
            status_info = await deposit_service.get_deposit_status_with_confirmations(
                deposit.id
            )

            if status_info.get("success"):
                confirmations = status_info.get("confirmations", 0)
                estimated_time = status_info.get("estimated_time", "2-5 минут")

                # Format progress bar
                deposit_status_text = format_deposit_status(
                    amount=deposit.amount,
                    level=deposit.level,
                    confirmations=confirmations,
                    required_confirmations=12,
                    estimated_time=estimated_time
                )

                # Send as separate message with inline keyboard
                await message.answer(
                    deposit_status_text,
                    parse_mode="Markdown",
                    reply_markup=deposit_status_keyboard(deposit.id)
                )

        text += "\n"

    # Show confirmed active deposits
    if active_deposits:
        text += "✅ *АКТИВНЫЕ ДЕПОЗИТЫ*\n\n"

        for deposit in active_deposits:
            # Calculate ROI progress
            roi_paid = float(getattr(deposit, "roi_paid_amount", 0) or 0)
            roi_cap = float(getattr(deposit, "roi_cap_amount", 0) or 0)

            if roi_cap > 0:
                roi_percent = (roi_paid / roi_cap) * 100
                roi_status = f"{roi_percent:.1f}%"
                # Progress bar (10 chars)
                filled = int(roi_percent / 10)
                empty = 10 - filled
                progress_bar = "█" * filled + "░" * empty
            else:
                roi_status = "0%"
                progress_bar = "░" * 10

            # Check if completed
            is_completed = getattr(deposit, "is_roi_completed", False)
            status_emoji = "✅" if is_completed else "🟢"
            status_text = "Закрыт (ROI 500%)" if is_completed else "Активен"

            created_date = deposit.created_at.strftime("%d.%m.%Y %H:%M")
            remaining = roi_cap - roi_paid

            text += (
                f"{status_emoji} *Уровень {deposit.level}*\n"
                f"💰 Сумма: {format_usdt(deposit.amount)} USDT\n"
                f"📊 ROI: `{progress_bar}` {roi_status}\n"
                f"✅ Получено: {format_usdt(roi_paid)} USDT\n"
                f"⏳ Осталось: {format_usdt(remaining)} USDT\n"
                f"📅 Создан: {created_date}\n"
                f"📋 Статус: {status_text}\n"
                f"─────────────────────────────\n\n"
            )

    is_admin = data.get("is_admin", False)
    blacklist_repo = BlacklistRepository(session)
    blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)

    # Send main message with active deposits (or header only if only pending)
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )


@router.callback_query(F.data.startswith("refresh_deposit_"))
async def handle_refresh_deposit(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Handle deposit status refresh callback.

    Args:
        callback: Callback query
        session: Database session
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
        return

    # Extract deposit_id from callback_data
    deposit_id_str = callback.data.replace("refresh_deposit_", "")
    try:
        deposit_id = int(deposit_id_str)
    except ValueError:
        await callback.answer("❌ Ошибка: неверный формат запроса", show_alert=True)
        return

    # Get deposit service
    deposit_service = DepositService(session)

    # Get deposit status with confirmations
    status_info = await deposit_service.get_deposit_status_with_confirmations(
        deposit_id
    )

    if not status_info.get("success"):
        await callback.answer(
            status_info.get("error", "Ошибка при получении статуса"),
            show_alert=True
        )
        return

    deposit = status_info.get("deposit")
    if not deposit:
        await callback.answer("❌ Депозит не найден", show_alert=True)
        return

    # Check if user owns this deposit
    if deposit.user_id != user.id:
        await callback.answer("❌ Доступ запрещён", show_alert=True)
        return

    # Check if deposit is confirmed
    if deposit.status == TransactionStatus.CONFIRMED.value:
        await callback.answer(
            "✅ Депозит подтверждён!\n\nОбновите список депозитов в меню '📦 Мои депозиты'",
            show_alert=True
        )

        # Update message to show confirmation
        try:
            await callback.message.edit_text(
                f"✅ **ДЕПОЗИТ ПОДТВЕРЖДЁН**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 Сумма: {format_usdt(deposit.amount)} USDT (Level {deposit.level})\n"
                f"📋 Статус: Подтверждён и активирован\n\n"
                f"🎉 Ваш депозит успешно активирован!\n"
                f"Начисления ROI начнутся в соответствии с графиком.\n"
                f"━━━━━━━━━━━━━━━━━━━━",
                parse_mode="Markdown",
                reply_markup=None
            )
        except Exception as e:
            logger.warning(f"Failed to edit message for confirmed deposit: {e}")

        return

    # Get confirmations
    confirmations = status_info.get("confirmations", 0)
    estimated_time = status_info.get("estimated_time", "2-5 минут")

    # Format status message
    status_text = format_deposit_status(
        amount=deposit.amount,
        level=deposit.level,
        confirmations=confirmations,
        required_confirmations=12,
        estimated_time=estimated_time
    )

    # Update message
    try:
        await callback.message.edit_text(
            status_text,
            parse_mode="Markdown",
            reply_markup=deposit_status_keyboard(deposit.id)
        )

        await callback.answer(
            f"🔄 Обновлено: {confirmations}/12 подтверждений"
        )

        logger.info(
            f"Deposit {deposit_id} status refreshed for user {user.id}: "
            f"{confirmations}/12 confirmations"
        )

    except Exception as e:
        logger.error(f"Failed to update deposit status message: {e}")
        await callback.answer("❌ Ошибка при обновлении статуса", show_alert=True)


@router.callback_query(F.data == "main_menu")
async def handle_main_menu_callback(
    callback: CallbackQuery,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Handle main menu callback from deposit status.

    Args:
        callback: Callback query
        session: Database session
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await callback.answer("❌ Ошибка: пользователь не найден", show_alert=True)
        return

    await callback.answer()

    # Get user info for keyboard
    is_admin = data.get("is_admin", False)
    blacklist_repo = BlacklistRepository(session)
    blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)

    # Send main menu message
    await callback.message.answer(
        "📊 Главное меню\n\nВыберите действие:",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        )
    )

    # Try to delete the callback message
    try:
        await callback.message.delete()
    except Exception as e:
        logger.debug(f"Failed to delete message: {e}")
