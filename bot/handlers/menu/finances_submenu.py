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
from app.repositories.bonus_credit_repository import BonusCreditRepository
from app.services.daily_payment_check_service import DailyPaymentCheckService
from app.services.deposit import DepositService
from app.services.user_service import UserService
from bot.keyboards.user import finances_submenu_keyboard
from bot.utils.formatters import format_usdt, format_wallet_short
from bot.utils.user_context import get_user_from_context


router = Router()


@router.message(StateFilter("*"), F.text == "💰 Финансы")
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

    user = await get_user_from_context(message, session, data)
    if not user:
        await message.answer("⚠️ Ошибка: не удалось загрузить данные пользователя. Попробуйте отправить /start")
        return

    await state.clear()

    # Use cached user data to avoid transaction errors
    available = float(user.balance or 0)
    total_deposited = float(user.total_deposited_usdt or 0)
    bonus_deposited = float(user.bonus_balance or 0)
    deposited_total = total_deposited + bonus_deposited

    # Try to get ROI details from DB, but fallback to simple display
    deposit_roi_paid = 0.0
    deposit_roi_cap = 0.0
    bonus_roi_paid = 0.0
    bonus_roi_cap = 0.0
    
    try:
        deposit_service = DepositService(session)
        active_deposits = await deposit_service.get_active_deposits(user.id)
        deposit_roi_paid = sum(float(d.roi_paid_amount or 0) for d in (active_deposits or []))
        deposit_roi_cap = sum(float(d.roi_cap_amount or 0) for d in (active_deposits or []))

        bonus_repo = BonusCreditRepository(session)
        active_bonus = await bonus_repo.get_active_by_user(user.id)
        bonus_roi_paid = sum(float(b.roi_paid_amount or 0) for b in (active_bonus or []))
        bonus_roi_cap = sum(float(b.roi_cap_amount or 0) for b in (active_bonus or []))
    except Exception as e:
        logger.warning(f"Failed to get ROI details: {e}")

    roi_paid_total = deposit_roi_paid + bonus_roi_paid
    roi_cap_total = deposit_roi_cap + bonus_roi_cap

    # Build deposits section with TOTAL in work
    if deposited_total > 0:
        deposits_section = f"💼 В работе: `{format_usdt(deposited_total)} USDT`\n"
        if total_deposited > 0:
            deposits_section += f"  ├ 📦 Депозит: `{format_usdt(total_deposited)} USDT`\n"
        if bonus_deposited > 0:
            deposits_section += f"  └ 🎁 Бонус: `{format_usdt(bonus_deposited)} USDT`\n"

        if roi_cap_total > 0 and roi_paid_total > 0:
            overall_progress = (roi_paid_total / roi_cap_total) * 100
            deposits_section += (
                f"📈 ROI прогресс: `{overall_progress:.1f}%`\n"
                f"✅ Заработано (ROI): `{format_usdt(roi_paid_total)} USDT`\n"
            )
        total = available + deposited_total
    else:
        deposits_section = "💼 В работе: `0.00 USDT`\n"
        total = available

    # Get PLEX payment status
    plex_status_section = ""
    try:
        plex_service = DailyPaymentCheckService(session)
        plex_status = await plex_service.check_daily_payment_status(user.id)
        if not plex_status.get("error") and not plex_status.get("no_deposits"):
            required_plex = int(plex_status.get("required_plex", 0))
            is_paid = plex_status.get("is_paid", False)
            if is_paid:
                plex_status_section = f"⚡ PLEX: ✅ оплачено ({required_plex:,}/день)\n"
            else:
                wallet = plex_status.get("wallet_address", "")
                if wallet and len(wallet) > 16:
                    plex_status_section = (
                        f"⚡ PLEX: ❌ НЕ оплачено ({required_plex:,}/день)\n"
                        f"  └ Кошелёк: `{format_wallet_short(wallet)}`\n"
                    )
                else:
                    plex_status_section = f"⚡ PLEX: ❌ НЕ оплачено ({required_plex:,}/день)\n"
    except Exception as e:
        logger.warning(f"Failed to get PLEX status: {e}")

    text = f"💰 *Финансы*\n\n💵 Доступно: `{available:.2f} USDT`\n"
    text += f"{deposits_section}"
    if plex_status_section:
        text += plex_status_section
    text += f"💎 Всего активов: `{total:.2f} USDT`\n\nВыберите действие:"

    await message.answer(text, reply_markup=finances_submenu_keyboard(), parse_mode="Markdown")
    logger.info(f"[SUBMENU] Finances submenu shown to user {telegram_id}")


@router.message(StateFilter("*"), F.text == "📊 Мои средства")
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

    user = await get_user_from_context(message, session, data)
    if not user:
        await message.answer("⚠️ Ошибка: не удалось загрузить данные пользователя. Попробуйте отправить /start")
        return

    await state.clear()

    # Get comprehensive balance information
    user_service = UserService(session)
    balance_info = await user_service.get_user_balance(user.id)

    if not balance_info:
        await message.answer("⚠️ Не удалось загрузить информацию о балансе.", reply_markup=finances_submenu_keyboard())
        return

    # Extract balance components
    available = balance_info.get("available_balance", 0)
    locked = balance_info.get("locked_balance", 0)
    wallet = balance_info.get("wallet_balance", 0)
    pending_withdrawals = balance_info.get("pending_withdrawals", 0)

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

        level_names = {
            0: "🎯 Тестовый",
            1: "💰 Уровень 1",
            2: "💎 Уровень 2",
            3: "🏆 Уровень 3",
            4: "👑 Уровень 4",
            5: "🚀 Уровень 5",
        }

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

    await message.answer(text, reply_markup=funds_overview_keyboard(), parse_mode="Markdown")
    logger.info(f"[FUNDS] Funds overview shown to user {telegram_id}")


@router.message(StateFilter("*"), F.text == "◀️ Назад")
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

    user = await get_user_from_context(message, session, data)
    if not user:
        await message.answer("⚠️ Ошибка: не удалось загрузить данные пользователя. Попробуйте отправить /start")
        return

    # Create safe data copy and remove arguments that are passed positionally
    safe_data = data.copy()
    safe_data.pop("user", None)
    safe_data.pop("state", None)
    safe_data.pop("session", None)

    # Redirect to main menu
    await show_main_menu(message, session, user, state, **safe_data)
