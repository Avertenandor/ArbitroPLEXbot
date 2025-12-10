"""
Finances submenu handlers.

This module contains handlers for the finances submenu, which includes:
- Deposit
- Withdrawal
- Balance overview (combined view)
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.deposit import DepositService
from app.services.user_service import UserService
from bot.keyboards.user import finances_submenu_keyboard
from bot.utils.formatters import format_usdt
from bot.utils.user_loader import UserLoader

router = Router()


@router.message(StateFilter('*'), F.text == "💰 Финансы")
async def show_finances_submenu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show finances submenu.

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[SUBMENU] Finances submenu requested by user {telegram_id}")

    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()

    # Get user balance for quick overview
    user_service = UserService(session)
    balance_info = await user_service.get_user_balance(user.id)

    available = balance_info.get('available_balance', 0) if balance_info else 0

    # Get deposits info from user model (primary source)
    from decimal import Decimal
    total_deposited = float(user.total_deposited_usdt or Decimal("0"))

    # Calculate deposits totals
    if total_deposited > 0:
        # Check for ROI data from deposits table
        deposit_service = DepositService(session)
        active_deposits = await deposit_service.get_active_deposits(user.id)

        if active_deposits:
            total_roi_paid = sum(float(d.roi_paid_amount or 0) for d in active_deposits)
            total_roi_cap = sum(float(d.roi_cap_amount or 0) for d in active_deposits)

            if total_roi_cap > 0:
                overall_progress = (total_roi_paid / total_roi_cap) * 100
                deposits_section = (
                    f"📦 В депозитах: `{format_usdt(total_deposited)} USDT`\n"
                    f"📈 ROI прогресс: `{overall_progress:.1f}%`\n"
                    f"✅ Заработано: `{format_usdt(total_roi_paid)} USDT`\n"
                )
            else:
                deposits_section = f"📦 В депозитах: `{format_usdt(total_deposited)} USDT`\n"
        else:
            deposits_section = f"📦 В депозитах: `{format_usdt(total_deposited)} USDT`\n"
        total = float(available) + total_deposited
    else:
        deposits_section = "📦 В депозитах: `0.00 USDT`\n"
        total = float(available)

    text = (
        "💰 *Финансы*\n\n"
        f"💵 Доступно: `{available:.2f} USDT`\n"
    )

    # Add bonus section if user has bonuses
    bonus_balance = balance_info.get('bonus_balance', 0) if balance_info else 0
    if bonus_balance and bonus_balance > 0:
        text += f"🎁 Бонусный баланс: `{float(bonus_balance):.2f} USDT`\n"

    text += (
        f"{deposits_section}"
        f"💎 Всего активов: `{total:.2f} USDT`\n\n"
        "Выберите действие:"
    )

    await message.answer(
        text,
        reply_markup=finances_submenu_keyboard(),
        parse_mode="Markdown"
    )
    logger.info(f"[SUBMENU] Finances submenu shown to user {telegram_id}")


@router.message(StateFilter('*'), F.text == "📊 Мои средства")
async def show_funds_overview(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show comprehensive funds overview (balance + wallet balance + deposits).

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[FUNDS] Funds overview requested by user {telegram_id}")

    user: User | None = data.get("user")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()

    # Get comprehensive balance information
    user_service = UserService(session)
    balance_info = await user_service.get_user_balance(user.id)

    if not balance_info:
        await message.answer(
            "⚠️ Не удалось загрузить информацию о балансе.",
            reply_markup=finances_submenu_keyboard()
        )
        return

    # Extract balance components
    available = balance_info.get('available_balance', 0)
    locked = balance_info.get('locked_balance', 0)
    wallet = balance_info.get('wallet_balance', 0)
    pending_withdrawals = balance_info.get('pending_withdrawals', 0)

    total_balance = available + locked
    total_with_wallet = total_balance + wallet

    # Get active deposits info
    deposit_service = DepositService(session)
    active_deposits = await deposit_service.get_active_deposits(user.id)

    text = (
        "📊 *Мои средства*\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "*Торговый баланс:*\n"
        f"💵 Доступно: `{available:.2f} USDT`\n"
        f"🔒 В депозитах: `{locked:.2f} USDT`\n"
        f"📊 Итого: `{total_balance:.2f} USDT`\n\n"
        "*Реферальный кошелек:*\n"
        f"💰 Баланс кошелька: `{wallet:.2f} USDT`\n"
    )

    if pending_withdrawals > 0:
        text += f"⏳ В обработке (вывод): `{pending_withdrawals:.2f} USDT`\n"

    # Add deposits section
    if active_deposits:
        text += "\n━━━━━━━━━━━━━━━━━\n"
        text += "*📦 Активные депозиты:*\n\n"

        level_names = {0: "🎯 Тестовый", 1: "💰 Уровень 1", 2: "💎 Уровень 2",
                       3: "🏆 Уровень 3", 4: "👑 Уровень 4", 5: "🚀 Уровень 5"}

        total_deposited = 0
        total_roi_paid = 0

        for dep in active_deposits:
            level_name = level_names.get(dep.level, f"Level {dep.level}")
            amount = float(dep.amount or 0)
            roi_paid = float(dep.roi_paid_amount or 0)
            roi_cap = float(dep.roi_cap_amount or 0)

            total_deposited += amount
            total_roi_paid += roi_paid

            # Calculate progress
            if roi_cap > 0:
                progress = (roi_paid / roi_cap) * 100
                text += (
                    f"{level_name}: `{amount:.0f} USDT`\n"
                    f"   📈 ROI: `{roi_paid:.2f}` / `{roi_cap:.2f}` ({progress:.0f}%)\n"
                )
            else:
                text += f"{level_name}: `{amount:.0f} USDT`\n"

        text += f"\n💎 Всего в депозитах: `{total_deposited:.0f} USDT`\n"
        text += f"✅ Заработано ROI: `{total_roi_paid:.2f} USDT`\n"
    else:
        text += "\n━━━━━━━━━━━━━━━━━\n"
        text += "*📦 Активные депозиты:*\n"
        text += "_У вас пока нет активных депозитов_\n"

    text += (
        "\n━━━━━━━━━━━━━━━━━\n"
        f"💎 *Всего средств: `{total_with_wallet:.2f} USDT`*\n\n"
        "💡 «👛 Мой кошелек» — балансы PLEX/USDT/BNB\n"
        "💡 «💰 Депозит» — открыть новый депозит"
    )

    # Use funds overview keyboard with wallet button
    from bot.keyboards.user.menus.financial_menu import funds_overview_keyboard

    await message.answer(
        text,
        reply_markup=funds_overview_keyboard(),
        parse_mode="Markdown"
    )
    logger.info(f"[FUNDS] Funds overview shown to user {telegram_id}")


@router.message(StateFilter('*'), F.text == "◀️ Назад")
async def back_to_main_from_finances(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle back button from finances submenu.

    Args:
        message: Message object
        session: Database session
        state: FSM state
        **data: Handler data (includes user from AuthMiddleware)
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[SUBMENU] Back to main menu from finances submenu for user {telegram_id}")

    # Clear state
    await state.clear()

    # Import to avoid circular dependency
    from bot.handlers.menu.core import show_main_menu

    user: User | None = data.get("user")

    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)

    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    # Create safe data copy and remove arguments that are passed positionally
    safe_data = data.copy()
    safe_data.pop('user', None)
    safe_data.pop('state', None)
    safe_data.pop('session', None)

    # Redirect to main menu
    await show_main_menu(message, session, user, state, **safe_data)
