"""
Menu handler.

Handles main menu navigation - ТОЛЬКО REPLY KEYBOARDS!
"""

from typing import Any

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.blacklist_repository import BlacklistRepository
from app.services.report_service import ReportService
from app.services.user_service import UserService
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import (
    deposit_keyboard,
    main_menu_reply_keyboard,
    profile_keyboard,
    referral_keyboard,
    settings_keyboard,
    wallet_menu_keyboard,
    withdrawal_keyboard,
)
from bot.states.registration import RegistrationStates
from bot.utils.text_utils import escape_markdown
from bot.utils.user_loader import UserLoader

router = Router()


async def show_main_menu(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show main menu.

    Args:
        message: Message object
        session: Database session
        user: Current user
        state: FSM state
        **data: Handler data (includes is_admin from AuthMiddleware)
    """
    logger.info(f"[MENU] show_main_menu called for user {user.telegram_id} (@{user.username})")

    # Clear any active FSM state
    await state.clear()

    # Get blacklist status
    blacklist_repo = BlacklistRepository(session)
    blacklist_entry = await blacklist_repo.find_by_telegram_id(
        user.telegram_id
    )
    logger.info(
        f"[MENU] Blacklist entry for user {user.telegram_id}: "
        f"exists={blacklist_entry is not None}, "
        f"active={blacklist_entry.is_active if blacklist_entry else False}"
    )

    # Get is_admin from middleware data (set by AuthMiddleware)
    is_admin = data.get("is_admin", False)
    logger.info(
        f"[MENU] is_admin from data for user {user.telegram_id}: {is_admin}, "
        f"data keys: {list(data.keys())}"
    )

    # R13-3: Get user language for i18n
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    # Escape username for Markdown
    safe_username = escape_markdown(user.username) if user.username else _('common.user')

    # Get balance for quick view
    user_service = UserService(session)
    balance = await user_service.get_user_balance(user.id)
    available = balance.get('available_balance', 0) if balance else 0

    text = (
        f"{_('menu.main')}\n\n"
        f"{_('common.welcome_user', username=safe_username)}\n"
        f"💰 Баланс: `{available:.2f} USDT`\n\n"
        f"{_('common.choose_action')}\n\n"
        f"🐰 Партнер: [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)"
    )

    logger.info(
        f"[MENU] Creating keyboard for user {user.telegram_id} with "
        f"is_admin={is_admin}, blacklist_entry={blacklist_entry is not None}"
    )
    keyboard = main_menu_reply_keyboard(
        user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
    )
    logger.info(f"[MENU] Sending main menu to user {user.telegram_id}")

    await message.answer(
        text,
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    logger.info(f"[MENU] Main menu sent successfully to user {user.telegram_id}")


@router.message(F.text.in_({
    "📊 Главное меню",
    "⬅ Назад",
    "⏭ Пропустить",  # Registration skip (leftover keyboard)
    "⏭️ Пропустить",  # Same with FE0F
    "✅ Да, оставить контакты",  # Registration contacts (leftover keyboard)
}))
async def handle_main_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle main menu button."""
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[MENU] handle_main_menu called for user {telegram_id}, text: {message.text}")

    user: User | None = data.get("user")
    is_admin = data.get("is_admin")
    logger.info(f"[MENU] User from data: {user.id if user else None}, is_admin={is_admin}, data keys: {list(data.keys())}")

    if not user:
        # Если по какой-то причине DI не предоставил user, просто очистим
        # состояние и покажем базовое меню без учёта статусов.
        logger.warning(f"[MENU] No user in data for telegram_id {telegram_id}, using fallback")
        await state.clear()
        is_admin = data.get("is_admin", False)
        logger.info(f"[MENU] Fallback menu with is_admin={is_admin}")
        await message.answer(
            "📊 *Главное меню*\n\nВыберите действие:",
            reply_markup=main_menu_reply_keyboard(
                user=None, blacklist_entry=None, is_admin=is_admin
            ),
            parse_mode="Markdown",
        )
        return
    logger.info(f"[MENU] Calling show_main_menu for user {user.telegram_id}")

    # Create safe data copy and remove arguments that are passed positionally
    safe_data = data.copy()
    safe_data.pop('user', None)
    safe_data.pop('state', None)
    safe_data.pop('session', None)  # session is also passed positionally

    await show_main_menu(message, session, user, state, **safe_data)


@router.message(StateFilter('*'), F.text == "📊 Баланс")
async def show_balance(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show user balance."""
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[MENU] show_balance called for user {telegram_id}")
    user: User | None = data.get("user")
    logger.info(f"[MENU] User from data: {user.id if user else None}, data keys: {list(data.keys())}")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return
    await state.clear()

    user_service = UserService(session)
    balance = await user_service.get_user_balance(user.id)

    if not balance:
        await message.answer("❌ Ошибка получения баланса")
        return

    text = (
        f"💰 *Ваш баланс:*\n\n"
        f"Общий: `{balance['total_balance']:.2f} USDT`\n"
        f"Доступно: `{balance['available_balance']:.2f} USDT`\n"
        f"В ожидании: `{balance['pending_earnings']:.2f} USDT`\n\n"
        f"📊 *Статистика:*\n"
        f"Депозиты: `{balance['total_deposits']:.2f} USDT`\n"
        f"Выводы: `{balance['total_withdrawals']:.2f} USDT`\n"
        f"Заработано: `{balance['total_earnings']:.2f} USDT`"
    )

    await message.answer(text, parse_mode="Markdown")


@router.message(StateFilter('*'), F.text == "💰 Депозит")
async def show_deposit_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show deposit menu."""
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[MENU] show_deposit_menu called for user {telegram_id}")
    user: User | None = data.get("user")
    logger.info(f"[MENU] User from data: {user.id if user else None}, data keys: {list(data.keys())}")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()

    # Get level statuses using DepositValidationService
    from app.services.deposit_validation_service import (
        DepositValidationService,
    )

    validation_service = DepositValidationService(session)
    levels_status = await validation_service.get_available_levels(user.id)

    # Build text with statuses
    from app.config.settings import settings

    text = "💰 *Выберите уровень депозита:*\n\n"
    for level in [1, 2, 3, 4, 5]:
        if level in levels_status:
            level_info = levels_status[level]
            amount = level_info["amount"]
            status = level_info["status"]
            status_text = level_info.get("status_text", "")

            if status == "active":
                text += f"✅ Level {level}: `{amount} USDT` - Активен\n"
            elif status == "available":
                text += f"💰 Level {level}: `{amount} USDT` - Доступен\n"
            else:
                # Show reason for unavailability
                error = level_info.get("error", "")
                if "необходимо сначала купить" in error:
                    text += f"🔒 Level {level}: `{amount} USDT` - Недоступен (нет предыдущего уровня)\n"
                elif "необходимо минимум" in error:
                    text += f"🔒 Level {level}: `{amount} USDT` - Недоступен (не хватает партнёров)\n"
                else:
                    text += f"🔒 Level {level}: `{amount} USDT` - Недоступен\n"
        else:
            # Fallback
            amounts = {
                1: settings.deposit_level_1,
                2: settings.deposit_level_2,
                3: settings.deposit_level_3,
                4: settings.deposit_level_4,
                5: settings.deposit_level_5,
            }
            text += f"💰 Level {level}: `{amounts[level]:.0f} USDT`\n"

    logger.info(f"[MENU] Sending deposit menu response to user {telegram_id}")
    try:
        await message.answer(
            text, reply_markup=deposit_keyboard(levels_status=levels_status), parse_mode="Markdown"
        )
        logger.info(f"[MENU] Deposit menu response sent successfully to user {telegram_id}")
    except Exception as e:
        logger.error(f"[MENU] Failed to send deposit menu response: {e}", exc_info=True)
        raise


@router.message(StateFilter('*'), F.text == "💸 Вывод")
async def show_withdrawal_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show withdrawal menu."""
    telegram_id = message.from_user.id if message.from_user else None
    logger.info(f"[MENU] show_withdrawal_menu called for user {telegram_id}")
    user: User | None = data.get("user")
    logger.info(f"[MENU] User from data: {user.id if user else None}, data keys: {list(data.keys())}")
    if not user and telegram_id:
        user = await UserLoader.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "⚠️ Ошибка: не удалось загрузить данные пользователя. "
            "Попробуйте отправить /start"
        )
        return

    await state.clear()
    # Set context flag for smart number input handling in withdrawal menu
    await state.update_data(in_withdrawal_menu=True)

    user_service = UserService(session)
    balance = await user_service.get_user_balance(user.id)

    # Get min withdrawal amount
    from app.services.withdrawal_service import WithdrawalService
    withdrawal_service = WithdrawalService(session)
    min_amount = await withdrawal_service.get_min_withdrawal_amount()

    text = (
        f"💸 *Вывод средств*\n\n"
        f"Доступно для вывода: `{balance['available_balance']:.2f} USDT`\n"
        f"💰 *Минимальная сумма:* `{min_amount} USDT`\n\n"
        f"ℹ️ _Вывод возможен по накоплению {min_amount} USDT прибыли, "
        f"чтобы не нагружать выплатную систему и не переплачивать комиссии._\n\n"
        f"Выберите действие:"
    )

    logger.info(f"[MENU] Sending withdrawal menu response to user {telegram_id}")
    try:
        await message.answer(
            text, reply_markup=withdrawal_keyboard(), parse_mode="Markdown"
        )
        logger.info(f"[MENU] Withdrawal menu response sent successfully to user {telegram_id}")
    except Exception as e:
        logger.error(f"[MENU] Failed to send withdrawal menu response: {e}", exc_info=True)
        raise


@router.message(StateFilter('*'), F.text == "👥 Рефералы")
async def show_referral_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show referral menu."""
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

    await state.clear()

    from app.config.settings import settings
    from app.services.user_service import UserService

    user_service = UserService(session)
    bot_username = settings.telegram_bot_username
    referral_link = user_service.generate_referral_link(user, bot_username)

    text = (
        f"👥 *Реферальная программа*\n\n"
        f"Ваша реферальная ссылка:\n"
        f"`{referral_link}`\n\n"
        f"Приглашайте друзей и получайте вознаграждение!"
    )

    await message.answer(
        text, reply_markup=referral_keyboard(), parse_mode="Markdown"
    )


# Support menu handler moved to bot/handlers/support.py
# Removed to avoid handler conflicts


@router.message(StateFilter('*'), F.text == "⚙️ Настройки")
async def show_settings_menu(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show settings menu."""
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

    await state.clear()

    text = "⚙️ *Настройки*\n\nВыберите раздел:"

    await message.answer(
        text, reply_markup=settings_keyboard(), parse_mode="Markdown"
    )


@router.message(StateFilter('*'), F.text == "🐰 Купить кролика")
async def show_rabbit_partner(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show partner rabbit farm info."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)

    await state.clear()

    text = (
        "🐰 **Токенизированная ферма кроликов**\n\n"
        "Для работы в ArbitroPLEXbot каждый пользователь должен быть "
        "владельцем **минимум одного кролика** на ферме наших партнеров.\n\n"
        "**DEXRabbit** — это:\n"
        "• Покупка и удалённое содержание кроликов на ферме\n"
        "• Работа с USDT\n"
        "• Маркетплейс перепродаж\n"
        "• Реферальная программа 3×5%\n\n"
        "⚠️ **Это обязательное условие для работы в нашей экосистеме!**"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🐰 Перейти к покупке кролика",
            url="https://t.me/dexrabbit_bot?start=ref_9"
        )],
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

    # Get blacklist info for back button
    blacklist_entry = None
    try:
        blacklist_repo = BlacklistRepository(session)
        if message.from_user:
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                message.from_user.id
            )
    except Exception as e:
        logger.warning(f"Failed to get blacklist entry: {e}")

    # Send back button
    await message.answer(
        "⬅️ Для возврата в меню нажмите кнопку ниже:",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )


@router.message(StateFilter('*'), F.text == "📋 Правила")
async def show_rules(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show platform rules."""
    from bot.constants.rules import RULES_FULL_TEXT

    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)

    await state.clear()

    await message.answer(
        RULES_FULL_TEXT,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

    # Get blacklist info for back button
    blacklist_entry = None
    try:
        blacklist_repo = BlacklistRepository(session)
        if message.from_user:
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                message.from_user.id
            )
    except Exception as e:
        logger.warning(f"Failed to get blacklist entry: {e}")

    # Send back button with reply keyboard
    await message.answer(
        "⬅️ Для возврата в главное меню:",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )


@router.message(StateFilter('*'), F.text == "🌐 Инструменты нашей экосистемы")
async def show_ecosystem_tools(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Show ecosystem tools menu."""
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)

    await state.clear()

    text = (
        "🌐 **Инструменты нашей экосистемы**\n\n"
        "Все проекты и сервисы нашей крипто-фиатной экосистемы "
        "на базе монеты **PLEX**:\n\n"
        "Нажмите на интересующий вас проект для перехода:"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🤖 ArbitroPLEXbot — Торговый бот",
            url="https://arbitrage-bot.com/"
        )],
        [InlineKeyboardButton(
            text="🐰 DEXRabbit — Ферма кроликов",
            url="https://xn--80apagbbfxgmuj4j.site/"
        )],
        [InlineKeyboardButton(
            text="👑 RoyalKeta — Premium сервис",
            url="https://royalketa.com/"
        )],
        [InlineKeyboardButton(
            text="🎬 FreeTube — Видео платформа",
            url="https://freetube.online/"
        )],
        [InlineKeyboardButton(
            text="🛒 BestTrade Store — Магазин ботов",
            url="https://best-trade.store/bots/"
        )],
        [InlineKeyboardButton(
            text="📊 DataPLEX — Аналитика",
            url="https://data-plex.net/"
        )],
    ])

    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

    # Get blacklist info for back button
    blacklist_entry = None
    try:
        blacklist_repo = BlacklistRepository(session)
        if message.from_user:
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                message.from_user.id
            )
    except Exception as e:
        logger.warning(f"Failed to get blacklist entry: {e}")

    # Send back button with reply keyboard
    await message.answer(
        "⬅️ Для возврата в главное меню:",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )


@router.message(StateFilter('*'), F.text == "🔄 Обновить депозит")
async def handle_update_deposit(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle deposit scan request from user."""
    from app.services.deposit_scan_service import DepositScanService

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
            from app.config.settings import settings
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


# Handlers для submenu кнопок


# Referral handlers are implemented in referral.py
# These handlers are removed to avoid duplication


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

    from app.services.deposit_service import DepositService
    from bot.utils.formatters import format_usdt

    user_service = UserService(session)
    deposit_service = DepositService(session)

    # Get user stats
    stats = await user_service.get_user_stats(user.id)

    # Get user balance
    balance = await user_service.get_user_balance(user.id)

    # Get ROI progress for level 1
    roi_progress = await deposit_service.get_level1_roi_progress(user.id)

    # Get referral link
    from app.config.settings import settings

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


@router.message(StateFilter('*'), F.text == "💳 Мой кошелек")
async def show_my_wallet(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Show user wallet."""
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

    # Get wallet history
    from sqlalchemy import desc, select

    from app.models.user_wallet_history import UserWalletHistory

    stmt = select(UserWalletHistory).where(
        UserWalletHistory.user_id == user.id
    ).order_by(desc(UserWalletHistory.changed_at)).limit(5)
    result = await session.execute(stmt)
    history = result.scalars().all()

    text = (
        f"💳 *Мой кошелек*\n\n"
        f"📍 Текущий адрес:\n`{user.wallet_address}`\n\n"
    )

    if history:
        text += "📜 *История изменений:*\n"
        for h in history:
            old_short = f"{h.old_wallet_address[:8]}...{h.old_wallet_address[-6:]}"
            new_short = f"{h.new_wallet_address[:8]}...{h.new_wallet_address[-6:]}"
            date_str = h.changed_at.strftime("%d.%m.%Y %H:%M")
            text += f"• {date_str}\n  `{old_short}` → `{new_short}`\n"
        text += "\n"

    text += "⚠️ Сохраните приватный ключ в безопасном месте!"

    await message.answer(text, parse_mode="Markdown", reply_markup=wallet_menu_keyboard())


@router.message(StateFilter('*'), F.text == "📝 Регистрация")
async def start_registration(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Start registration process from menu button.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    user: User | None = data.get("user")

    # If user already registered, show main menu
    if user:
        logger.info(
            f"start_registration: User {user.telegram_id} already registered, "
            "showing main menu"
        )
        is_admin = data.get("is_admin", False)
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        await message.answer(
            "✅ Вы уже зарегистрированы!",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        await state.clear()
        return

    # Clear any active FSM state
    await state.clear()

    # Show registration welcome message
    welcome_text = (
        "👋 **Добро пожаловать в ArbitroPLEXbot!**\n\n"
        "ArbitroPLEXbot — это платформа для инвестиций в USDT на сети "
        "Binance Smart Chain (BEP-20).\n\n"
        "**Важно:**\n"
        "• Работа ведется только с сетью **BSC (BEP-20)**\n"
        "• Базовая валюта депозитов — **USDT BEP-20**\n"
        "• **Требование:** Для доступа нужен активный кролик от [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)\n\n"
        "🌐 **Официальный сайт:**\n"
        "[arbitrage-bot.com](https://arbitrage-bot.com/)\n\n"
        "Для начала работы необходимо пройти регистрацию.\n\n"
        "📝 **Шаг 1:** Введите ваш BSC (BEP-20) адрес кошелька\n"
        "Формат: `0x...` (42 символа)\n\n"
        "⚠️ **КРИТИЧНО:** Указывайте только **ЛИЧНЫЙ** кошелек (Trust Wallet, MetaMask, SafePal или любой холодный кошелек).\n"
        "🚫 **НЕ указывайте** адрес биржи (Binance, Bybit), иначе выплаты могут быть утеряны!"
    )

    from aiogram.types import ReplyKeyboardRemove

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        disable_web_page_preview=False,
        reply_markup=ReplyKeyboardRemove(),
    )

    # Start registration FSM
    await state.set_state(RegistrationStates.waiting_for_wallet)


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

    from app.services.deposit_service import DepositService
    from bot.keyboards.reply import main_menu_reply_keyboard
    from bot.utils.formatters import format_usdt

    deposit_service = DepositService(session)

    # Get active deposits
    active_deposits = await deposit_service.get_active_deposits(user.id)

    if not active_deposits:
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

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )


@router.message(StateFilter('*'), F.text == "🔔 Настройки уведомлений")
async def show_notification_settings(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show notification settings menu.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    from app.services.user_notification_service import UserNotificationService
    from bot.keyboards.reply import notification_settings_reply_keyboard

    notification_service = UserNotificationService(session)
    settings = await notification_service.get_settings(user.id)
    await session.commit()

    # Build status text
    deposit_status = "✅ Включены" if settings.deposit_notifications else "❌ Выключены"
    withdrawal_status = "✅ Включены" if settings.withdrawal_notifications else "❌ Выключены"
    roi_status = "✅ Включены" if getattr(settings, 'roi_notifications', True) else "❌ Выключены"
    marketing_status = "✅ Включены" if settings.marketing_notifications else "❌ Выключены"

    text = (
        f"🔔 *Настройки уведомлений*\n\n"
        f"Управляйте уведомлениями, которые вы хотите получать:\n\n"
        f"💰 Уведомления о депозитах: {deposit_status}\n"
        f"💸 Уведомления о выводах: {withdrawal_status}\n"
        f"📊 Уведомления о ROI: {roi_status}\n"
        f"📢 Маркетинговые уведомления: {marketing_status}\n\n"
        f"Используйте кнопки ниже для изменения настроек."
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=notification_settings_reply_keyboard(
            deposit_enabled=settings.deposit_notifications,
            withdrawal_enabled=settings.withdrawal_notifications,
            roi_enabled=getattr(settings, 'roi_notifications', True),
            marketing_enabled=settings.marketing_notifications,
        ),
    )


async def _toggle_notification_setting(
    message: Message,
    session: AsyncSession,
    user: User,
    field_name: str,
) -> None:
    """
    Generic notification toggle handler.

    Args:
        message: Telegram message
        session: Database session
        user: User object
        field_name: Name of the notification field to toggle
                   (e.g., 'deposit_notifications', 'withdrawal_notifications')
    """
    from app.services.user_notification_service import UserNotificationService
    from bot.keyboards.reply import notification_settings_reply_keyboard

    notification_service = UserNotificationService(session)
    settings = await notification_service.get_settings(user.id)

    # Get current value and toggle it
    current_value = getattr(settings, field_name, True)
    new_value = not current_value

    # Update the specific field
    await notification_service.update_settings(
        user.id, **{field_name: new_value}
    )
    await session.commit()

    # Refresh settings
    settings = await notification_service.get_settings(user.id)

    # Build status text
    deposit_status = "✅ Включены" if settings.deposit_notifications else "❌ Выключены"
    withdrawal_status = "✅ Включены" if settings.withdrawal_notifications else "❌ Выключены"
    roi_status = "✅ Включены" if getattr(settings, 'roi_notifications', True) else "❌ Выключены"
    marketing_status = "✅ Включены" if settings.marketing_notifications else "❌ Выключены"

    text = (
        f"🔔 *Настройки уведомлений*\n\n"
        f"Управляйте уведомлениями, которые вы хотите получать:\n\n"
        f"💰 Уведомления о депозитах: {deposit_status}\n"
        f"💸 Уведомления о выводах: {withdrawal_status}\n"
        f"📊 Уведомления о ROI: {roi_status}\n"
        f"📢 Маркетинговые уведомления: {marketing_status}\n\n"
        f"Используйте кнопки ниже для изменения настроек."
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=notification_settings_reply_keyboard(
            deposit_enabled=settings.deposit_notifications,
            withdrawal_enabled=settings.withdrawal_notifications,
            roi_enabled=getattr(settings, 'roi_notifications', True),
            marketing_enabled=settings.marketing_notifications,
        ),
    )


@router.message(F.text.in_({
    "✅ Уведомления о депозитах",
    "❌ Уведомления о депозитах",
}))
async def toggle_deposit_notification(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle deposit notifications."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    await _toggle_notification_setting(message, session, user, "deposit_notifications")


@router.message(F.text.in_({
    "✅ Уведомления о выводах",
    "❌ Уведомления о выводах",
}))
async def toggle_withdrawal_notification(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle withdrawal notifications."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    await _toggle_notification_setting(message, session, user, "withdrawal_notifications")


@router.message(F.text.in_({
    "✅ Уведомления о ROI",
    "❌ Уведомления о ROI",
}))
async def toggle_roi_notification(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle ROI notifications."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    await _toggle_notification_setting(message, session, user, "roi_notifications")


@router.message(F.text.in_({
    "✅ Маркетинговые уведомления",
    "❌ Маркетинговые уведомления",
}))
async def toggle_marketing_notification(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Toggle marketing notifications."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return
    await _toggle_notification_setting(message, session, user, "marketing_notifications")


@router.message(StateFilter('*'), F.text == "🌐 Изменить язык")
async def show_language_settings(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Show language selection menu.
    
    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    await state.clear()

    # Get current language
    current_language = await get_user_language(session, user.id)

    text = (
        f"🌐 *Настройка языка*\n\n"
        f"Текущий язык: **{current_language.upper()}**\n\n"
        f"Выберите язык интерфейса:"
    )

    from aiogram.types import KeyboardButton
    from aiogram.utils.keyboard import ReplyKeyboardBuilder

    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="🇷🇺 Русский"))
    builder.row(KeyboardButton(text="🇬🇧 English"))
    builder.row(KeyboardButton(text="◀️ Назад"))

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup(resize_keyboard=True),
    )


@router.message(F.text.in_({"🇷🇺 Русский", "🇬🇧 English"}))
async def process_language_selection(
    message: Message,
    session: AsyncSession,
    **data: Any,
) -> None:
    """
    Process language selection.
    
    Args:
        message: Telegram message
        session: Database session
        **data: Handler data
    """
    user: User | None = data.get("user")
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    # Determine selected language
    language = "ru" if message.text == "🇷🇺 Русский" else "en"

    # Update user language
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(session)
    await user_repo.update(user.id, language=language)
    await session.commit()

    # Show confirmation
    if language == "ru":
        text = "✅ Язык интерфейса изменен на **Русский**"
    else:
        text = "✅ Interface language changed to **English**"

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=settings_keyboard(language),
    )


@router.message(StateFilter('*'), F.text == "◀️ Назад")
async def back_to_settings_from_language(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle back button from language menu.
    
    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        **data: Handler data
    """
    # If we are in a specific state that handles "◀️ Назад" differently,
    # this handler might not be reached if registered after.
    # But here we use it as a catch-all for this button in menu router.

    # Clear state just in case
    await state.clear()

    # Redirect to settings menu
    await show_settings_menu(message, session, state, **data)


# Contact update handlers moved to bot/handlers/contact_update.py
