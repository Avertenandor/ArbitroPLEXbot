"""
Admin Panel Handler
Handles admin panel main menu and platform statistics
"""

from datetime import UTC, datetime
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import Admin
from app.models.user import User
from app.services.admin_service import AdminService
from app.services.deposit_service import DepositService
from app.services.referral_service import ReferralService
from app.services.user_service import UserService
from bot.handlers.admin.utils.admin_checks import (
    get_admin_or_deny,
)
from bot.keyboards.reply import (
    admin_keyboard,
    get_admin_keyboard_from_data,
)
from bot.states.admin_states import AdminStates
from bot.utils.formatters import format_usdt

router = Router(name="admin_panel")


async def get_admin_and_super_status(
    session: AsyncSession,
    telegram_id: int | None,
    data: dict[str, Any],
) -> tuple[Admin | None, bool]:
    """
    Get admin object and super_admin status.

    Args:
        session: Database session
        telegram_id: Telegram user ID
        data: Handler data dict

    Returns:
        Tuple of (Admin object or None, is_super_admin bool)
    """
    admin: Admin | None = data.get("admin")
    if not admin and telegram_id:
        # If admin not in data (e.g., before master key auth), fetch from DB
        from app.services.admin_service import AdminService
        admin_service = AdminService(session)
        admin = await admin_service.get_admin_by_telegram_id(telegram_id)

    is_super_admin = admin.is_super_admin if admin else False
    return admin, is_super_admin


async def _validate_master_key(message: Message) -> tuple[int | None, str | None]:
    """
    Validate master key input and extract telegram_id.

    Args:
        message: Telegram message with master key

    Returns:
        Tuple of (telegram_id, master_key) or (None, None) if validation failed
    """
    telegram_id = message.from_user.id if message.from_user else None
    if not telegram_id:
        await message.answer("❌ Не удалось определить пользователя")
        return None, None

    master_key = message.text.strip() if message.text else ""
    if not master_key:
        await message.answer("❌ Мастер-ключ не может быть пустым")
        return None, None

    return telegram_id, master_key


async def _handle_authentication_failure(message: Message, error: str | None) -> None:
    """
    Handle authentication failure case.

    Args:
        message: Telegram message
        error: Error message from authentication
    """
    await message.answer(
        f"❌ {error or 'Ошибка аутентификации'}\n\n"
        "Попробуйте ввести мастер-ключ еще раз:",
        parse_mode="Markdown",
    )


async def _restore_previous_state(
    message: Message,
    state: FSMContext,
    telegram_id: int,
    state_data: dict[str, Any],
) -> bool:
    """
    Restore previous state if it exists.

    Args:
        message: Telegram message
        state: FSM context
        telegram_id: Telegram user ID
        state_data: State data dictionary

    Returns:
        True if state was restored, False otherwise
    """
    previous_state = state_data.get("auth_previous_state")
    if not previous_state:
        return False

    await state.set_state(previous_state)
    await state.update_data(auth_previous_state=None, auth_redirect_message=None)

    logger.info(
        f"Admin {telegram_id} authenticated successfully, "
        f"restoring state {previous_state}"
    )

    await message.answer(
        "✅ **Аутентификация успешна!**\n\n"
        "Вы вернулись в предыдущее меню. Пожалуйста, повторите ваше действие.",
        parse_mode="Markdown",
    )
    return True


async def _redirect_to_support(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to support menu."""
    from bot.handlers.admin.support import handle_admin_support_menu
    await handle_admin_support_menu(message, state, **data)


async def _redirect_to_deposit_management(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to deposit management menu."""
    from bot.handlers.admin.deposit_management import show_deposit_management_menu
    await show_deposit_management_menu(message, session, **data)


async def _redirect_to_deposit_settings(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to deposit settings."""
    from bot.handlers.admin.deposit_settings import show_deposit_settings
    await show_deposit_settings(message, session, **data)


async def _redirect_to_admin_management(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to admin management."""
    from bot.handlers.admin.admins import show_admin_management
    await show_admin_management(message, session, **data)


async def _redirect_to_blacklist(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to blacklist management."""
    from bot.handlers.admin.blacklist import show_blacklist
    await show_blacklist(message, session, **data)


async def _redirect_to_wallet(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to wallet dashboard."""
    from bot.handlers.admin.wallet_management import show_wallet_dashboard
    await show_wallet_dashboard(message, session, state, **data)


async def _redirect_to_withdrawals(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to withdrawal requests."""
    await handle_admin_withdrawals(message, session, **data)


async def _redirect_to_broadcast(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to broadcast menu."""
    from bot.handlers.admin.broadcast import handle_broadcast_menu
    await handle_broadcast_menu(message, session, **data)


async def _redirect_to_users(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to user management."""
    await handle_admin_users_menu(message, session, **data)


async def _redirect_to_stats(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to statistics."""
    await handle_admin_stats(message, session, **data)


async def _redirect_to_finpass_recovery(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to finpass recovery."""
    from bot.handlers.admin.finpass_recovery import show_recovery_requests
    await show_recovery_requests(message, session, state, **data)


async def _redirect_to_financials(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Redirect to financial list."""
    from bot.handlers.admin.financials import show_financial_list
    await show_financial_list(message, session, state, **data)


def _get_redirect_handler(redirect_text: str):
    """
    Get redirect handler function based on redirect text.

    Args:
        redirect_text: Text indicating which handler to redirect to

    Returns:
        Handler function or None if no match found
    """
    handlers = {
        "🆘 Техподдержка": _redirect_to_support,
        "💰 Управление депозитами": _redirect_to_deposit_management,
        "⚙️ Настроить уровни депозитов": _redirect_to_deposit_settings,
        "👥 Управление админами": _redirect_to_admin_management,
        "🚫 Управление черным списком": _redirect_to_blacklist,
        "🔐 Управление кошельком": _redirect_to_wallet,
        "💸 Заявки на вывод": _redirect_to_withdrawals,
        "📢 Рассылка": _redirect_to_broadcast,
        "👥 Управление пользователями": _redirect_to_users,
        "📊 Статистика": _redirect_to_stats,
        "🔑 Восстановление пароля": _redirect_to_finpass_recovery,
    }

    # Direct match
    if redirect_text in handlers:
        return handlers[redirect_text]

    # Special case: check for "Финансовая" substring
    if "Финансовая" in redirect_text:
        return _redirect_to_financials

    # Admin panel doesn't need redirect
    if redirect_text == "👑 Админ-панель":
        return None

    return None


async def _redirect_to_handler(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    redirect_text: str,
    telegram_id: int,
    **data: Any,
) -> bool:
    """
    Redirect to appropriate handler based on redirect text.

    Args:
        message: Telegram message
        session: Database session
        state: FSM context
        redirect_text: Text indicating which handler to redirect to
        telegram_id: Telegram user ID
        **data: Handler data

    Returns:
        True if redirected, False if no redirect occurred
    """
    logger.info(f"Attempting to redirect admin {telegram_id} to '{redirect_text}'")

    handler = _get_redirect_handler(redirect_text)
    if handler is None:
        return False

    await handler(message, session, state, **data)
    return True


async def _show_admin_panel(
    message: Message,
    session: AsyncSession,
    telegram_id: int,
    data: dict[str, Any],
) -> None:
    """
    Show admin panel after successful authentication.

    Args:
        message: Telegram message
        session: Database session
        telegram_id: Telegram user ID
        data: Handler data
    """
    text = """
👑 **Панель администратора**

Добро пожаловать в панель управления ArbitroPLEXbot Bot.

Выберите действие:
    """.strip()

    admin, is_super_admin = await get_admin_and_super_status(
        session, telegram_id, data
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard(
            is_super_admin=is_super_admin,
            is_extended_admin=admin.is_extended_admin if admin else False
        ),
    )


@router.message(AdminStates.awaiting_master_key_input)
async def handle_master_key_input(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle master key input for admin authentication.

    Args:
        message: Telegram message with master key
        session: Database session
        state: FSM context
        **data: Handler data
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Validate master key input
    telegram_id, master_key = await _validate_master_key(message)
    if not telegram_id or not master_key:
        return

    # Authenticate admin
    redis_client = data.get("redis_client")
    admin_service = AdminService(session, redis_client=redis_client)
    session_obj, admin_obj, error = await admin_service.login(
        telegram_id=telegram_id,
        master_key=master_key,
        ip_address=None,  # Telegram doesn't provide IP
        user_agent=None,  # Telegram doesn't provide user agent
    )

    # Handle authentication failure
    if error or not session_obj or not admin_obj:
        await _handle_authentication_failure(message, error)
        return

    # Save session token in FSM state
    await state.update_data(admin_session_token=session_obj.session_token)

    # Get state data
    state_data = await state.get_data()

    # Try to restore previous state
    if await _restore_previous_state(message, state, telegram_id, state_data):
        return

    # Try to redirect based on button text
    redirect_message_text = state_data.get("auth_redirect_message")
    if redirect_message_text:
        await state.update_data(auth_redirect_message=None)
        if await _redirect_to_handler(
            message, session, state, redirect_message_text, telegram_id, **data
        ):
            return

    # Clear state and show admin panel
    await state.set_state(None)
    logger.info(
        f"Admin {telegram_id} authenticated successfully, "
        f"session_id={session_obj.id}"
    )

    await _show_admin_panel(message, session, telegram_id, data)


@router.message(Command("admin"))
async def cmd_admin_panel(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Вход в админ-панель по команде /admin.
    Работает только для админов (is_admin=True из middleware).
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    text = """
👑 **Панель администратора**

Добро пожаловать в панель управления ArbitroPLEXbot Bot.

Выберите действие:
    """.strip()

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard(
        is_super_admin=admin.is_super_admin,
        is_extended_admin=admin.is_extended_admin
    ),
    )


@router.message(F.text == "👑 Админ-панель")
async def handle_admin_panel_button(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Вход в админ-панель по кнопке в reply keyboard.
    Работает только для админов (is_admin=True из middleware).
    """
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[ADMIN] handle_admin_panel_button called for user {telegram_id}")

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        logger.warning(f"[ADMIN] User {telegram_id} tried to access admin panel but was denied")
        return

    text = """
👑 **Панель администратора**

Добро пожаловать в панель управления ArbitroPLEXbot Bot.

Выберите действие:
    """.strip()

    # AdminAuthMiddleware already populates is_extended_admin / is_super_admin in data
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard_from_data(data),
    )


@router.message(F.text == "◀️ Главное меню")
async def handle_back_to_main_menu(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Return to main menu from admin panel"""
    from bot.handlers.menu import show_main_menu

    state: FSMContext = data.get("state")
    user: User | None = data.get("user")

    if state:
        # Force clear state AND session token to require master key on next entry
        await state.clear()

    # Remove 'user' and 'state' from data to avoid duplicate arguments
    safe_data = {k: v for k, v in data.items() if k not in ('user', 'state')}
    await show_main_menu(message, session, user, state, **safe_data)


@router.message(Command("retention"))
async def cmd_retention(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Retention metrics (DAU/WAU/MAU) for admins.
    Usage: /retention
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from app.services.analytics_service import AnalyticsService

    analytics = AnalyticsService(session)
    metrics = await analytics.get_retention_metrics()
    cohorts = await analytics.get_cohort_stats(days=7)
    avg_deposit = await analytics.get_average_deposit()

    # Build text
    text = (
        f"📈 *Retention-метрики*\n\n"
        f"👥 *Активные пользователи:*\n"
        f"• DAU (24ч): *{metrics['dau']}* ({metrics['dau_rate']}%)\n"
        f"• WAU (7д): *{metrics['wau']}* ({metrics['wau_rate']}%)\n"
        f"• MAU (30д): *{metrics['mau']}* ({metrics['mau_rate']}%)\n"
        f"• Всего: *{metrics['total_users']}*\n\n"
        f"📊 *Stickiness (DAU/MAU):* `{metrics['stickiness']}%`\n\n"
        f"💰 *Депозиты:*\n"
        f"• Средний чек: *{avg_deposit['avg_deposit']:.2f} USDT*\n"
        f"• Конверсия в депозит: *{avg_deposit['deposit_rate']}%*\n\n"
        f"📅 *Когорты (последние 7 дней):*\n"
    )

    for cohort in cohorts:
        text += (
            f"• {cohort['date']}: {cohort['registered']} рег → "
            f"{cohort['deposited']} деп ({cohort['conversion_rate']}%)\n"
        )

    await message.answer(text, parse_mode="Markdown")


@router.message(Command("dashboard"))
async def cmd_dashboard(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Quick dashboard with 24h metrics for admins.
    Usage: /dashboard
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from datetime import UTC, datetime, timedelta

    from sqlalchemy import and_, func, select

    from app.models.deposit import Deposit
    from app.models.enums import TransactionStatus, TransactionType
    from app.models.transaction import Transaction
    from app.models.user import User

    cutoff_24h = datetime.now(UTC) - timedelta(hours=24)
    # Transaction model uses naive datetime (TIMESTAMP WITHOUT TIME ZONE)
    cutoff_24h_naive = cutoff_24h.replace(tzinfo=None)

    # New users in 24h (User model uses timezone-aware datetime)
    stmt = select(func.count(User.id)).where(User.created_at >= cutoff_24h)
    result = await session.execute(stmt)
    new_users_24h = result.scalar() or 0

    # New deposits in 24h
    stmt = select(func.count(Deposit.id), func.coalesce(func.sum(Deposit.amount), 0)).where(
        and_(
            Deposit.created_at >= cutoff_24h,
            Deposit.status == "ACTIVE",
        )
    )
    result = await session.execute(stmt)
    row = result.one()
    deposits_24h_count = row[0] or 0
    deposits_24h_amount = float(row[1] or 0)

    # Withdrawals in 24h (use naive datetime for Transaction model)
    stmt = select(func.count(Transaction.id), func.coalesce(func.sum(Transaction.amount), 0)).where(
        and_(
            Transaction.created_at >= cutoff_24h_naive,
            Transaction.transaction_type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.COMPLETED.value,
        )
    )
    result = await session.execute(stmt)
    row = result.one()
    withdrawals_24h_count = row[0] or 0
    withdrawals_24h_amount = float(row[1] or 0)

    # Pending withdrawals
    stmt = select(func.count(Transaction.id)).where(
        and_(
            Transaction.transaction_type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.PENDING.value,
        )
    )
    result = await session.execute(stmt)
    pending_withdrawals = result.scalar() or 0

    # Fraud alerts (users with risk_score > 50)
    # Simplified - count banned users as proxy
    stmt = select(func.count(User.id)).where(User.is_banned)
    result = await session.execute(stmt)
    fraud_alerts = result.scalar() or 0

    # 📊 Text-based charts
    def make_bar(value: float, max_val: float, length: int = 10) -> str:
        if max_val == 0:
            return "░" * length
        filled = int((value / max_val) * length)
        return "█" * filled + "░" * (length - filled)

    chart = ""
    # Example chart: Deposits vs Withdrawals
    max_vol = max(deposits_24h_amount, withdrawals_24h_amount)
    if max_vol > 0:
        dep_bar = make_bar(deposits_24h_amount, max_vol)
        wd_bar = make_bar(withdrawals_24h_amount, max_vol)
        chart = (
            f"\n📈 *Объем за 24ч:*\n"
            f"📥 Деп: `{dep_bar}` {int(deposits_24h_amount)}$\n"
            f"📤 Выв: `{wd_bar}` {int(withdrawals_24h_amount)}$\n"
        )

    text = (
        f"📊 *Дашборд (за 24ч)*\n\n"
        f"👥 Новых пользователей: *{new_users_24h}*\n"
        f"💰 Депозитов: *{deposits_24h_count}* ({deposits_24h_amount:.2f} USDT)\n"
        f"💸 Выводов: *{withdrawals_24h_count}* ({withdrawals_24h_amount:.2f} USDT)\n"
        f"⏳ Ожидают одобрения: *{pending_withdrawals}*\n"
        f"🚨 Заблокировано: *{fraud_alerts}*\n"
        f"{chart}\n"
        f"_Обновлено: {datetime.now(UTC).strftime('%H:%M UTC')}_"
    )

    await message.answer(text, parse_mode="Markdown")


@router.message(F.text == "📊 Статистика")
async def handle_admin_stats(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle platform statistics"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from app.services.withdrawal_service import WithdrawalService

    user_service = UserService(session)
    deposit_service = DepositService(session)
    referral_service = ReferralService(session)
    withdrawal_service = WithdrawalService(session)

    # Get statistics
    total_users = await user_service.get_total_users()
    verified_users = await user_service.get_verified_users()
    deposit_stats = await deposit_service.get_platform_stats()
    referral_stats = await referral_service.get_platform_referral_stats()
    withdrawal_stats = await withdrawal_service.get_platform_withdrawal_stats()

    # R4-X: Detailed deposit stats
    detailed_deposits = await deposit_service.get_detailed_stats()

    text = f"""
📊 **Статистика платформы**

**Пользователи:**
👥 Всего: {total_users}
✅ Верифицированы: {verified_users}
❌ Не верифицированы: {total_users - verified_users}

**Депозиты:**
💰 Всего депозитов: {deposit_stats["total_deposits"]}
💵 Общая сумма: {format_usdt(deposit_stats["total_amount"])} USDT
👤 Пользователей с депозитами: {deposit_stats["total_users"]}

**По уровням:**
• Уровень 1: {deposit_stats["deposits_by_level"].get(1, 0)} депозитов
• Уровень 2: {deposit_stats["deposits_by_level"].get(2, 0)} депозитов
• Уровень 3: {deposit_stats["deposits_by_level"].get(3, 0)} депозитов
• Уровень 4: {deposit_stats["deposits_by_level"].get(4, 0)} депозитов
• Уровень 5: {deposit_stats["deposits_by_level"].get(5, 0)} депозитов

**📋 Детализация активных депозитов:**
"""

    if not detailed_deposits:
        text += "Нет активных депозитов.\n"
    else:
        for d in detailed_deposits[:10]:  # Show top 10 recent
            if d["next_accrual_at"]:
                next_accrual = d["next_accrual_at"].strftime("%d.%m %H:%M")
            else:
                next_accrual = "Н/Д"

            # Escape username for Markdown
            username = str(d['username'])
            safe_username = (
                username.replace("_", "\\_").replace("*", "\\*")
                .replace("`", "\\`").replace("[", "\\[")
            )

            text += (
                f"👤 @{safe_username} (ID: {d['user_id']})\n"
                f"   💵 Деп: {format_usdt(d['amount'])} | Начислено: {format_usdt(d['roi_paid'])}\n"
                f"   ⏳ След. нач: {next_accrual}\n\n"
            )

        if len(detailed_deposits) > 10:
            text += f"... и еще {len(detailed_deposits) - 10} депозитов\n"

    text += f"""
**Рефералы:**
🤝 Всего связей: {referral_stats["total_referrals"]}
💰 Всего начислено: {format_usdt(referral_stats["total_earnings"])} USDT
✅ Выплачено: {format_usdt(referral_stats["paid_earnings"])} USDT
⏳ Ожидает выплаты: {format_usdt(referral_stats["pending_earnings"])} USDT

**По уровням:**
• Уровень 1: {referral_stats["by_level"].get(1, {}).get("count",
    0)} ({format_usdt(referral_stats["by_level"].get(1, {}).get("earnings",
        0))} USDT)
• Уровень 2: {referral_stats["by_level"].get(2, {}).get("count",
    0)} ({format_usdt(referral_stats["by_level"].get(2, {}).get(
        "earnings", 0))} USDT)
• Уровень 3: {referral_stats["by_level"].get(3, {}).get("count",
    0)} ({format_usdt(referral_stats["by_level"].get(3, {}).get(
        "earnings", 0))} USDT)

**💸 Выводы на кошельки:**
✅ Выведено: {format_usdt(withdrawal_stats["total_confirmed_amount"])} USDT \
({withdrawal_stats["total_confirmed"]} транз.)
❌ Неудачных: {withdrawal_stats["total_failed"]} \
({format_usdt(withdrawal_stats["total_failed_amount"])} USDT)
"""

    # Add per-user withdrawal summary
    if withdrawal_stats["by_user"]:
        text += "\n**По пользователям:**\n"
        for wu in withdrawal_stats["by_user"][:5]:
            wu_username = str(wu["username"] or "Без имени")
            safe_wu_username = (
                wu_username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
                .replace("[", "\\[")
            )
            text += f"• @{safe_wu_username}: {format_usdt(wu['total_withdrawn'])} USDT\n"

    # Add detailed withdrawals with tx_hash
    detailed_wd = await withdrawal_service.get_detailed_withdrawals(page=1, per_page=5)
    if detailed_wd["withdrawals"]:
        text += "\n**📋 Детализация (с хешами):**\n"
        for wd in detailed_wd["withdrawals"]:
            wd_username = str(wd["username"] or "Без имени")
            safe_wd_username = (
                wd_username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
                .replace("[", "\\[")
            )
            tx_short = wd["tx_hash"][:10] + "..." if wd["tx_hash"] else "N/A"
            text += f"• @{safe_wd_username}: {format_usdt(wd['amount'])} | `{tx_short}`\n"

        if detailed_wd["total_pages"] > 1:
            text += (
                f"\n_Стр. {detailed_wd['page']}/{detailed_wd['total_pages']}_ | "
                f"Нажми 📋 для навигации"
            )

    text = text.strip()

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard(
        is_super_admin=admin.is_super_admin,
        is_extended_admin=admin.is_extended_admin
    ),
    )


@router.message(F.text == "📋 История выводов")
async def handle_withdrawal_history(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle detailed withdrawal history with pagination."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Store page in FSM
    await state.update_data(wd_history_page=1)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(message, withdrawal_service, page=1)


async def show_withdrawal_page(
    message: Message,
    withdrawal_service,
    page: int = 1,
) -> None:
    """Show withdrawal history page."""
    from bot.keyboards.reply import (
        admin_withdrawal_history_pagination_keyboard,
    )

    detailed = await withdrawal_service.get_detailed_withdrawals(page=page, per_page=5)

    text = "📋 **История выводов на кошельки**\n\n"

    if not detailed["withdrawals"]:
        text += "_Нет подтверждённых выводов_"
    else:
        for wd in detailed["withdrawals"]:
            wd_username = str(wd["username"] or "Без имени")
            safe_wd_username = (
                wd_username.replace("_", "\\_")
                .replace("*", "\\*")
                .replace("`", "\\`")
                .replace("[", "\\[")
            )
            tx_hash = wd["tx_hash"] or "N/A"
            tx_short = tx_hash[:16] + "..." if len(tx_hash) > 16 else tx_hash
            created = wd["created_at"].strftime("%d.%m %H:%M") if wd["created_at"] else "N/A"

            text += (
                f"👤 @{safe_wd_username}\n"
                f"   💵 {format_usdt(wd['amount'])} USDT\n"
                f"   🔗 `{tx_short}`\n"
                f"   📅 {created}\n\n"
            )

        text += f"_Страница {detailed['page']} из {detailed['total_pages']}_"

    # Reply keyboard with pagination
    keyboard = admin_withdrawal_history_pagination_keyboard(
        page=page,
        total_pages=detailed["total_pages"]
    )

    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)


@router.message(F.text == "⬅️ Пред. страница выводов")
async def handle_wd_prev_page(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle previous page in withdrawal history."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    current_page = state_data.get("wd_history_page", 1)
    new_page = max(1, current_page - 1)
    await state.update_data(wd_history_page=new_page)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(message, withdrawal_service, page=new_page)


@router.message(F.text == "Вперёд страница выводов ➡️")
async def handle_wd_next_page(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle next page in withdrawal history."""
    from app.services.withdrawal_service import WithdrawalService

    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    state_data = await state.get_data()
    current_page = state_data.get("wd_history_page", 1)
    new_page = current_page + 1
    await state.update_data(wd_history_page=new_page)

    withdrawal_service = WithdrawalService(session)
    await show_withdrawal_page(message, withdrawal_service, page=new_page)


@router.message(F.text == "🔐 Управление кошельком")
async def handle_admin_wallet_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle wallet management menu from admin panel."""
    admin = await get_admin_or_deny(message, session, require_super=True, **data)
    if not admin:
        return

    # Redirect to wallet dashboard
    from bot.handlers.admin.wallet_management import show_wallet_dashboard

    await show_wallet_dashboard(message, session, state, **data)


@router.message(F.text == "🚫 Управление черным списком")
async def handle_admin_blacklist_menu(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to blacklist management."""
    from bot.handlers.admin.blacklist import show_blacklist

    await show_blacklist(message, session, **data)


@router.message(F.text == "👥 Управление пользователями")
async def handle_admin_users_menu(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show admin users management menu"""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from bot.keyboards.reply import admin_users_keyboard

    text = """👥 **Управление пользователями**

Выберите действие:"""

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_users_keyboard(),
    )


@router.message(F.text == "💸 Заявки на вывод")
async def handle_admin_withdrawals(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to withdrawals submenu with full functionality."""
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    # Redirect to the detailed withdrawals handler
    from bot.handlers.admin.withdrawals import handle_pending_withdrawals
    await handle_pending_withdrawals(message, session, **data)


# Broadcast handler is now in broadcast.py as @router.message(F.text == "📢 Рассылка")


@router.message(F.text == "⚙️ Настроить уровни депозитов")
async def handle_admin_deposit_settings(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to deposit settings management (legacy)."""
    from bot.handlers.admin.deposit_settings import show_deposit_settings

    await show_deposit_settings(message, session, **data)


@router.message(F.text == "💰 Управление депозитами")
async def handle_admin_deposit_management(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to deposit management."""
    from bot.handlers.admin.deposit_management import (
        show_deposit_management_menu,
    )

    await show_deposit_management_menu(message, session, **data)


@router.message(F.text == "👥 Управление админами")
async def handle_admin_management(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Redirect to admin management."""
    from bot.handlers.admin.admins import show_admin_management

    await show_admin_management(message, session, **data)


@router.message(Command("export"))
async def cmd_export_users(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Export all users to CSV file for admins.
    Usage: /export
    """
    admin = await get_admin_or_deny(message, session, **data)
    if not admin:
        return

    from aiogram.enums import ChatAction
    from aiogram.types import BufferedInputFile

    from app.services.financial_report_service import FinancialReportService

    # Send typing indicator
    await message.bot.send_chat_action(
        chat_id=message.chat.id,
        action=ChatAction.UPLOAD_DOCUMENT
    )

    try:
        report_service = FinancialReportService(session)
        csv_data = await report_service.export_all_users_csv()

        # Create file
        file_bytes = csv_data.encode('utf-8-sig')  # BOM for Excel compatibility
        file = BufferedInputFile(
            file_bytes,
            filename=f"users_export_{datetime.now(UTC).strftime('%Y%m%d_%H%M')}.csv"
        )

        await message.answer_document(
            file,
            caption="📊 *Экспорт пользователей*\n\nФайл содержит данные всех пользователей.",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error exporting users: {e}")
        await message.answer("❌ Ошибка при экспорте пользователей.")
