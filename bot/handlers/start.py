"""
Start handler.

Handles /start command and user registration.
"""

from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
    ReplyKeyboardRemove,
)
from loguru import logger
from sqlalchemy.exc import DatabaseError, InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.user import User
from app.services.blockchain_service import get_blockchain_service
from app.services.user_service import UserService
from app.services.wallet_verification_service import WalletVerificationService
from app.utils.security import mask_address
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import (
    auth_continue_keyboard,
    auth_payment_keyboard,
    auth_rescan_keyboard,
    auth_retry_keyboard,
    auth_wallet_input_keyboard,
    main_menu_reply_keyboard,
    show_password_keyboard,
)
from bot.middlewares.session_middleware import SESSION_KEY_PREFIX, SESSION_TTL
from bot.states.auth import AuthStates
from bot.states.registration import RegistrationStates

router = Router()


async def _handle_pay_to_use_auth(
    message: Message,
    state: FSMContext,
    redis_client: Any,
) -> bool:
    """
    Handle pay-to-use authorization check.

    Returns:
        True if user needs to authenticate (no session), False otherwise
    """
    if not redis_client:
        return False

    session_key = f"{SESSION_KEY_PREFIX}{message.from_user.id}"
    if await redis_client.exists(session_key):
        return False

    # Session expired or new user
    # Save referrer if present
    if message.text and len(message.text.split()) > 1:
        ref_arg = message.text.split()[1].strip()
        await state.update_data(pending_referrer_arg=ref_arg)

    from bot.constants.rules import LEVELS_TABLE, RULES_SHORT_TEXT

    # Get translator for unregistered user (default language)
    _ = get_translator("ru")

    # Step 1: Ask for wallet first
    await message.answer(
        _('auth.welcome_unregistered',
          levels_table=f"```\n{LEVELS_TABLE}```",
          rules_short=RULES_SHORT_TEXT),
        reply_markup=auth_wallet_input_keyboard(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await state.set_state(AuthStates.waiting_for_wallet)
    return True


async def _parse_referral_code(
    ref_arg: str,
    session: AsyncSession,
) -> int | None:
    """
    Parse referral code and return referrer telegram_id.

    Returns:
        Referrer telegram_id if valid, None otherwise
    """
    if not ref_arg.startswith("ref"):
        return None

    try:
        clean_arg = ref_arg[3:]  # Remove 'ref'
        if clean_arg.startswith("_") or clean_arg.startswith("-"):
            clean_arg = clean_arg[1:]

        if clean_arg.isdigit():
            # Legacy ID
            referrer_telegram_id = int(clean_arg)
            logger.info(
                "Legacy referral ID detected",
                extra={
                    "ref_arg": ref_arg,
                    "referrer_telegram_id": referrer_telegram_id,
                },
            )
            return referrer_telegram_id
        else:
            # New Referral Code
            user_service = UserService(session)
            referrer = await user_service.get_by_referral_code(clean_arg)

            if referrer:
                logger.info(
                    "Referral code detected",
                    extra={
                        "ref_code": clean_arg,
                        "referrer_telegram_id": referrer.telegram_id,
                    },
                )
                return referrer.telegram_id
            else:
                logger.warning(
                    "Referral code not found",
                    extra={"ref_code": clean_arg},
                )
                return None
    except (ValueError, AttributeError) as e:
        logger.warning(
            f"Invalid referral code format: {e}",
            extra={"ref_code": ref_arg},
        )
        return None


async def _reset_bot_blocked_flag(user: User, session: AsyncSession) -> None:
    """Reset bot_blocked flag if user unblocked the bot."""
    if not (hasattr(user, 'bot_blocked') and user.bot_blocked):
        return

    try:
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(session)
        await user_repo.update(user.id, bot_blocked=False)
        await session.commit()
        logger.info(
            f"User {user.telegram_id} unblocked bot, flag reset in /start"
        )
    except Exception as reset_error:
        logger.warning(f"Failed to reset bot_blocked flag: {reset_error}")


async def _get_blacklist_entry(
    telegram_id: int,
    session: AsyncSession,
    blacklist_entry: Any = None,
) -> Any:
    """Get blacklist entry for user."""
    if blacklist_entry is not None:
        return blacklist_entry

    from app.repositories.blacklist_repository import BlacklistRepository
    blacklist_repo = BlacklistRepository(session)
    return await blacklist_repo.find_by_telegram_id(telegram_id)


async def _handle_registered_user(
    message: Message,
    state: FSMContext,
    user: User,
    session: AsyncSession,
    data: dict[str, Any],
) -> None:
    """Handle flow for registered user."""
    logger.info(
        f"cmd_start: registered user {user.telegram_id}, clearing FSM state"
    )
    await state.clear()

    # Reset bot_blocked flag if user successfully sent /start
    await _reset_bot_blocked_flag(user, session)

    # Get user language for i18n
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    # Format balance properly
    balance_str = f"{user.balance:.8f}".rstrip('0').rstrip('.')
    if balance_str == '':
        balance_str = '0'

    # Escape username for Markdown
    raw_username = user.username or _('common.user')
    safe_username = (
        raw_username.replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
        .replace("[", "\\[")
    )

    welcome_text = (
        f"{_('common.welcome_back', username=safe_username)}\n\n"
        f"{_('common.your_balance', balance=balance_str)}\n"
        f"{_('common.use_menu')}"
    )
    logger.debug("cmd_start: sending welcome with ReplyKeyboardRemove")

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        disable_web_page_preview=False,
        reply_markup=ReplyKeyboardRemove(),
    )
    logger.debug("cmd_start: sending main menu keyboard")

    is_admin = data.get("is_admin", False)
    logger.info(
        f"[START] cmd_start for registered user {user.telegram_id}: "
        f"is_admin={is_admin}, data keys: {list(data.keys())}"
    )

    # Get blacklist status
    blacklist_entry = data.get("blacklist_entry")
    try:
        blacklist_entry = await _get_blacklist_entry(
            user.telegram_id, session, blacklist_entry
        )
    except (OperationalError, InterfaceError, DatabaseError):
        await message.answer(
            "⚠️ Системная ошибка. Попробуйте позже"
            "или обратитесь в поддержку."
        )
        return

    logger.info(
        f"[START] Creating keyboard for user {user.telegram_id} with "
        f"is_admin={is_admin}, blacklist_entry={blacklist_entry is not None}"
    )

    await message.answer(
        _("common.choose_action"),
        reply_markup=main_menu_reply_keyboard(
            user=user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin,
        ),
    )
    logger.info(
        f"[START] Main menu keyboard sent successfully to user {user.telegram_id}"
    )


async def _check_blacklist_registration_denied(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    blacklist_entry: Any = None,
) -> bool:
    """
    Check if user is blacklisted for registration.

    Returns:
        True if user is denied, False otherwise
    """
    try:
        blacklist_entry = await _get_blacklist_entry(
            message.from_user.id, session, blacklist_entry
        )

        if not (blacklist_entry and blacklist_entry.is_active):
            return False

        from app.models.blacklist import BlacklistActionType

        action = BlacklistActionType.REGISTRATION_DENIED
        if blacklist_entry.action_type != action:
            return False

        logger.info(
            f"[START] Registration denied for telegram_id {message.from_user.id}"
        )
        await message.answer(
            "❌ Регистрация недоступна.\n\n"
            "Обратитесь в поддержку для получения"
            "дополнительной информации."
        )
        await state.clear()
        return True

    except (OperationalError, InterfaceError, DatabaseError):
        await message.answer(
            "⚠️ Системная ошибка. Попробуйте позже"
            "или обратитесь в поддержку."
        )
        return True


async def _show_welcome_to_unregistered(
    message: Message,
    state: FSMContext,
    user: User | None,
    session: AsyncSession,
    referrer_telegram_id: int | None,
    is_admin: bool,
) -> None:
    """Show welcome message to unregistered user and start registration."""
    welcome_text = (
        "🚀 **Добро пожаловать в ArbitroPLEXbot!**\n\n"
        "Мы строим **крипто-фиатную экосистему** на"
        "базе монеты "
        "**PLEX** и высокодоходных торговых роботов.\n\n"
        "📊 **Доход:** от **30% до 70%** в день!\n\n"
        "⚠️ **ОБЯЗАТЕЛЬНЫЕ УСЛОВИЯ:**\n"
        "1️⃣ Каждый доллар депозита = **10 PLEX**\n"
        "2️⃣ Владение минимум **1 кроликом** на"
        "[DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "**Важно:**\n"
        "• Работа ведется только с сетью **BSC (BEP-20)**\n"
        "• Базовая валюта депозитов – **USDT BEP-20**\n\n"
        "🌐 **Официальный сайт:**\n"
        "[arbitrage-bot.com](https://arbitrage-bot.com/)\n\n"
        "🐰 **Наш партнер DEXRabbit:**\n"
        "Для работы в ArbitroPLEXbot необходимо купить"
        "минимум одного кролика "
        "на сайте нашего партнера:"
        "[dexrabbit.site](https://xn--80apagbbfxgmuj4j.site/)\n\n"
        "Для начала работы необходимо пройти"
        "регистрацию.\n\n"
        "📝 **Шаг 1:** Введите ваш BSC (BEP-20) адрес кошелька\n"
        "Формат: `0x...` (42 символа)\n\n"
        "⚠️ **КРИТИЧНО:** Указывайте только **ЛИЧНЫЙ**"
        "кошелек (Trust Wallet, MetaMask, SafePal или "
        "любой холодный кошелек).\n"
        "🚫 **НЕ указывайте** адрес биржи (Binance, Bybit),"
        "иначе выплаты могут быть утеряны!"
    )

    if referrer_telegram_id:
        await state.update_data(referrer_telegram_id=referrer_telegram_id)
        welcome_text += (
            "\n\n✅ Реферальный код принят! "
            "После регистрации вы будете привязаны к"
            "пригласившему."
        )

    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        disable_web_page_preview=False,
        reply_markup=ReplyKeyboardRemove(),
    )

    # Get user language for i18n
    user_language = "ru"
    if user:
        try:
            user_language = await get_user_language(session, user.id)
        except Exception as e:
            logger.warning(f"Failed to get user language, using default: {e}")
    _ = get_translator(user_language)

    await message.answer(
        _("common.choose_action"),
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=None, is_admin=is_admin
        ),
    )

    await state.set_state(RegistrationStates.waiting_for_wallet)





@router.message(CommandStart())
async def cmd_start(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Handle /start command with referral code support.

    Args:
        message: Telegram message
        session: Database session
        state: FSM state
        data: Additional data from middlewares
    """
    logger.info(
        f"=== CMD_START CALLED === user "
        f"{message.from_user.id if message.from_user else 'Unknown'}"
    )
    logger.info(f"Message text: {message.text}")

    # Always clear FSM state at start
    current_state = await state.get_state()
    if current_state:
        logger.info(f"Clearing FSM state: {current_state}")
    await state.clear()

    # --- PAY-TO-USE AUTHORIZATION ---
    redis_client = data.get("redis_client")
    if await _handle_pay_to_use_auth(message, state, redis_client):
        return
    # --------------------------------

    user: User | None = data.get("user")

    # Extract referral code from command args
    referrer_telegram_id = None
    if message.text and len(message.text.split()) > 1:
        ref_arg = message.text.split()[1].strip()
        referrer_telegram_id = await _parse_referral_code(ref_arg, session)

    # Check if already registered
    if user:
        await _handle_registered_user(message, state, user, session, data)
        return

    # Check blacklist for non-registered users (REGISTRATION_DENIED)
    blacklist_entry = data.get("blacklist_entry")
    if await _check_blacklist_registration_denied(
        message, state, session, blacklist_entry
    ):
        return

    # Show welcome to unregistered user
    is_admin = data.get("is_admin", False)
    await _show_welcome_to_unregistered(
        message, state, user, session, referrer_telegram_id, is_admin
    )




async def _handle_start_in_registration(
    message: Message,
    state: FSMContext,
    data: dict[str, Any],
) -> bool:
    """
    Handle /start command during registration.

    Returns:
        True if /start was handled, False otherwise
    """
    if not (message.text and message.text.startswith("/start")):
        return False

    logger.info(
        "process_wallet: /start caught, clearing state, showing main menu"
    )
    await state.clear()

    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)
    session = data.get("session")
    blacklist_entry = data.get("blacklist_entry")

    if blacklist_entry is None and user and session:
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                user.telegram_id
            )
        except Exception as e:
            logger.warning(
                f"Failed to get blacklist entry for user {user.telegram_id}: {e}"
            )
            blacklist_entry = None

    # Get user language for i18n
    user_language = "ru"
    if user and session:
        try:
            user_language = await get_user_language(session, user.id)
        except Exception as e:
            logger.warning(f"Failed to get user language, using default: {e}")
    _ = get_translator(user_language)

    await message.answer(
        _("common.welcome"),
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        _("common.choose_action"),
        reply_markup=main_menu_reply_keyboard(
            user=user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin,
        ),
    )
    return True


async def _handle_registration_button(message: Message) -> bool:
    """
    Handle "Registration" button during wallet input.

    Returns:
        True if registration button was handled, False otherwise
    """
    if message.text != "📝 Регистрация":
        return False

    await message.answer(
        "📝 **Регистрация**\n\n"
        "Введите ваш BSC (BEP-20) адрес кошелька:\n"
        "Формат: `0x...` (42 символа)\n\n"
        "⚠️ Указывайте только **ЛИЧНЫЙ** кошелек"
        "(Trust Wallet, MetaMask, SafePal или холодный кошелек).\n"
        "🚫 **НЕ указывайте** адрес биржи!",
        parse_mode="Markdown",
    )
    return True


async def _handle_menu_button_in_registration(
    message: Message,
    state: FSMContext,
    data: dict[str, Any],
) -> bool:
    """
    Handle menu button during registration.

    Returns:
        True if menu button was handled, False otherwise
    """
    from bot.utils.menu_buttons import is_menu_button

    if not is_menu_button(message.text):
        return False

    logger.debug(
        f"process_wallet: menu button {message.text}, showing main menu"
    )
    await state.clear()

    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)
    session = data.get("session")
    blacklist_entry = None

    if user and session:
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                user.telegram_id
            )
        except Exception as e:
            logger.warning(
                f"Failed to get blacklist entry for user {user.telegram_id}: {e}"
            )
            blacklist_entry = None

    await message.answer(
        "📊 Главное меню",
        reply_markup=main_menu_reply_keyboard(
            user=user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin,
        ),
    )
    return True


async def _check_wallet_rate_limit(
    message: Message,
    data: dict[str, Any],
) -> bool:
    """
    Check registration rate limit.

    Returns:
        True if rate limit exceeded, False otherwise
    """
    telegram_id = message.from_user.id if message.from_user else None
    if not telegram_id:
        return False

    from bot.utils.operation_rate_limit import OperationRateLimiter

    redis_client = data.get("redis_client")
    rate_limiter = OperationRateLimiter(redis_client=redis_client)
    allowed, error_msg = await rate_limiter.check_registration_limit(
        telegram_id
    )

    if not allowed:
        await message.answer(
            error_msg or "Слишком много попыток регистрации"
        )
        return True

    return False


async def _validate_wallet_format(message: Message, wallet_address: str) -> bool:
    """
    Validate wallet format.

    Returns:
        True if valid, False otherwise
    """
    from app.utils.validation import validate_bsc_address

    if validate_bsc_address(wallet_address, checksum=False):
        return True

    await message.answer(
        "❌ Неверный формат адреса!\n\n"
        "BSC адрес должен начинаться с '0x' и"
        "содержать 42 символа "
        "(0x + 40 hex символов).\n"
        "Попробуйте еще раз:"
    )
    return False


async def _check_wallet_blacklist(
    message: Message,
    state: FSMContext,
    wallet_address: str,
    session_factory: Any,
) -> bool:
    """
    Check if wallet is blacklisted.

    Returns:
        True if blacklisted, False otherwise
    """
    if not session_factory:
        return False

    try:
        async with session_factory() as session:
            async with session.begin():
                from app.services.blacklist_service import BlacklistService
                blacklist_service = BlacklistService(session)
                if await blacklist_service.is_blacklisted(
                    wallet_address=wallet_address.lower()
                ):
                    await message.answer(
                        "❌ Регистрация запрещена."
                        "Обращайтесь в поддержку."
                    )
                    await state.clear()
                    return True
    except (OperationalError, InterfaceError, DatabaseError) as e:
        logger.error(
            f"Database error checking wallet blacklist: {e}", exc_info=True
        )
        await message.answer(
            "⚠️ Системная ошибка. Попробуйте позже"
            "или обратитесь в поддержку."
        )
        return True

    return False


async def _check_existing_wallet(
    message: Message,
    state: FSMContext,
    wallet_address: str,
    session_factory: Any,
    session: Any,
) -> bool:
    """
    Check if wallet is already registered.

    Returns:
        True if wallet already exists (error shown), False otherwise
    """
    if not session_factory:
        # Fallback to old session
        if not session:
            await message.answer(
                "❌ Системная ошибка. Отправьте /start или "
                "обратитесь в поддержку."
            )
            return True

        user_service = UserService(session)
        existing = await user_service.get_by_wallet(wallet_address)
    else:
        # NEW pattern: short transaction
        async with session_factory() as session:
            async with session.begin():
                user_service = UserService(session)
                existing = await user_service.get_by_wallet(wallet_address)

    if not existing:
        return False

    telegram_id = message.from_user.id if message.from_user else None

    if telegram_id and existing.telegram_id == telegram_id:
        await message.answer(
            "ℹ️ Этот кошелек уже привязан к вашему"
            "аккаунту.\n\n"
            "Используйте команду /start для входа в систему."
        )
        await state.clear()
        return True
    else:
        await message.answer(
            "❌ Этот кошелек уже зарегистрирован"
            "другим пользователем!\n\n"
            "Используйте другой адрес:"
        )
        return True




@router.message(RegistrationStates.waiting_for_wallet)
async def process_wallet(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process wallet address.

    Uses session_factory to ensure transaction is closed before FSM state change.

    Args:
        message: Telegram message
        state: FSM state
        data: Additional data including session_factory
    """
    # Handle /start command
    if await _handle_start_in_registration(message, state, data):
        return

    # Handle "Registration" button
    if await _handle_registration_button(message):
        return

    # Handle menu button
    if await _handle_menu_button_in_registration(message, state, data):
        return

    wallet_address = message.text.strip()

    # Check registration rate limit
    if await _check_wallet_rate_limit(message, data):
        return

    # Validate wallet format
    if not await _validate_wallet_format(message, wallet_address):
        return

    session_factory = data.get("session_factory")

    # Check wallet blacklist
    if await _check_wallet_blacklist(message, state, wallet_address, session_factory):
        return

    # Check if wallet is already used by another user
    session = data.get("session")
    if await _check_existing_wallet(
        message, state, wallet_address, session_factory, session
    ):
        return

    # Save wallet to state
    await state.update_data(wallet_address=wallet_address)

    # Ask for financial password
    await message.answer(
        "✅ Адрес кошелька принят!\n\n"
        "📝 Шаг 2: Создайте финансовый пароль\n"
        "Этот пароль будет использоваться для"
        "подтверждения выводов.\n\n"
        "Требования:\n"
        "• Минимум 6 символов\n"
        "• Не используйте простые пароли\n\n"
        "Введите пароль:"
    )

    await state.set_state(RegistrationStates.waiting_for_financial_password)


@router.message(RegistrationStates.waiting_for_financial_password)
async def process_financial_password(
    message: Message,
    state: FSMContext,
    session: AsyncSession | None = None,
    **data: Any,
) -> None:
    """
    Process financial password.

    Args:
        message: Telegram message
        state: FSM state
        session: Database session (optional, can be from data)
        data: Additional data from middlewares
    """
    # РљР РРўРР§РќРћ: РїСЂРѕРїСѓСЃРєР°РµРј /start Рє РѕСЃРЅРѕРІРЅРѕРјСѓ Рѕ...
    if message.text and message.text.startswith("/start"):
        await state.clear()
        return  # РџРѕР·РІРѕР»СЏРµРј CommandStart() РѕР±СЂР°Р±РѕС‚Р°С‚СЊ СЌС‚Рѕ

    # Check if message is a menu button - if so, clear state and ignore
    from bot.utils.menu_buttons import is_menu_button

    if is_menu_button(message.text):
        await state.clear()
        # Get session from data if not provided
        if session is None:
            session = data.get("session")
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        from app.repositories.blacklist_repository import BlacklistRepository
        if session:
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = None
            if user:
                blacklist_entry = await blacklist_repo.find_by_telegram_id(
                    user.telegram_id
                )
            await message.answer(
                "рџ“Љ Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ",
                reply_markup=main_menu_reply_keyboard(
                    user=user,
                    blacklist_entry=blacklist_entry,
                    is_admin=is_admin
                ),
            )
        else:
            # Fallback if no session
            await message.answer(
                "рџ“Љ Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ",
                reply_markup=main_menu_reply_keyboard(
                    user=user, blacklist_entry=None, is_admin=is_admin
                ),
            )
        return

    password = message.text.strip()

    # Validate password
    if len(password) < 6:
        await message.answer(
            "вќЊ РџР°СЂРѕР»СЊ СЃР»РёС€РєРѕРј РєРѕСЂРѕС‚РєРёР№!\n\n"
            "РњРёРЅРёРјР°Р»СЊРЅР°СЏ РґР»РёРЅР°: 6 СЃРёРјРІРѕР»РѕРІ.\n"
            "РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰Рµ СЂР°Р·:"
        )
        return

    # Delete message with password (safe delete)
    try:
        await message.delete()
    except TelegramAPIError as e:
        logger.debug(f"Could not delete message: {e}")

    # Save password to state
    await state.update_data(financial_password=password)

    # Ask for confirmation
    await message.answer(
        "вњ… РџР°СЂРѕР»СЊ РїСЂРёРЅСЏС‚!\n\n"
        "рџ“ќ РЁР°Рі 3: РџРѕРґС‚РІРµСЂРґРёС‚Рµ РїР°СЂРѕР»СЊ\n"
        "Р’РІРµРґРёС‚Рµ РїР°СЂРѕР»СЊ РµС‰Рµ СЂР°Р·:"
    )

    await state.set_state(RegistrationStates.waiting_for_password_confirmation)




async def _handle_menu_button_in_password_confirmation(
    message: Message,
    state: FSMContext,
    data: dict[str, Any],
) -> bool:
    """
    Handle menu button during password confirmation.

    Returns:
        True if menu button was handled, False otherwise
    """
    from bot.utils.menu_buttons import is_menu_button

    if not is_menu_button(message.text):
        return False

    await state.clear()
    user: User | None = data.get("user")
    is_admin = data.get("is_admin", False)
    session = data.get("session")
    blacklist_entry = None

    if user and session:
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                user.telegram_id
            )
        except Exception as e:
            logger.warning(
                f"Failed to get blacklist entry for user {user.telegram_id}: {e}"
            )
            blacklist_entry = None

    await message.answer(
        "📊 Главное меню",
        reply_markup=main_menu_reply_keyboard(
            user=user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin,
        ),
    )
    return True


async def _handle_blacklist_error(
    message: Message,
    state: FSMContext,
    error_msg: str,
) -> None:
    """Handle blacklist error during registration."""
    action_type = error_msg.split(":")[1]
    from app.models.blacklist import BlacklistActionType

    if action_type == BlacklistActionType.REGISTRATION_DENIED:
        await message.answer(
            "Здравствуйте, по решению"
            "участников нашего "
            "сообщества вам отказано в"
            "регистрации в нашем "
            "боте и других инструментах нашего"
            "сообщества."
        )
    else:
        await message.answer(
            "❌ Ошибка регистрации. Обратитесь в"
            "поддержку."
        )
    await state.clear()


async def _register_user_old_pattern(
    message: Message,
    state: FSMContext,
    session: Any,
    wallet_address: str,
    password: str,
    referrer_telegram_id: int | None,
) -> User | None:
    """Register user using old pattern (direct session)."""
    try:
        user_service = UserService(session)
        user = await user_service.register_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            wallet_address=wallet_address,
            financial_password=password,
            referrer_telegram_id=referrer_telegram_id,
        )
        return user
    except ValueError as e:
        error_msg = str(e)
        if error_msg.startswith("BLACKLISTED:"):
            await _handle_blacklist_error(message, state, error_msg)
        else:
            await message.answer(
                f"❌ Ошибка регистрации:\\n{error_msg}\\n\\n"
                "Попробуйте начать заново: /start"
            )
        await state.clear()
        return None


async def _register_user_new_pattern(
    message: Message,
    state: FSMContext,
    session_factory: Any,
    wallet_address: str,
    password: str,
    referrer_telegram_id: int | None,
) -> User | None:
    """Register user using new pattern (session factory)."""
    user = None
    try:
        async with session_factory() as session:
            async with session.begin():
                user_service = UserService(session)
                user = await user_service.register_user(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    wallet_address=wallet_address,
                    financial_password=password,
                    referrer_telegram_id=referrer_telegram_id,
                )
        return user
    except ValueError as e:
        error_msg = str(e)

        # Handle "User already registered" as success (Double Submit issue)
        if error_msg == "User already registered":
            logger.info(
                f"Double registration attempt caught for user {message.from_user.id}"
            )
            async with session_factory() as session:
                user_service = UserService(session)
                user = await user_service.get_by_telegram_id(message.from_user.id)

            if user:
                logger.info(
                    f"User {user.id} found, treating double registration as success"
                )
                return user
            else:
                await message.answer(
                    "❌ Ошибка: Пользователь уже"
                    "зарегистрирован, но данные не найдены. "
                    "Обратитесь в поддержку."
                )
                await state.clear()
                return None

        # Check if it's a blacklist error
        elif error_msg.startswith("BLACKLISTED:"):
            await _handle_blacklist_error(message, state, error_msg)
            return None
        else:
            await message.answer(
                f"❌ Ошибка регистрации:\\n{error_msg}\\n\\n"
                "Попробуйте начать заново: /start"
            )
            await state.clear()
            return None


async def _store_password_in_redis(
    user: User,
    password: str,
    redis_client: Any,
) -> None:
    """Store encrypted password in Redis for 1 hour."""
    if not (redis_client and password):
        return

    try:
        password_key = f"password:plain:{user.id}"
        from bot.utils.secure_storage import SecureRedisStorage

        secure_storage = SecureRedisStorage(redis_client)
        success = await secure_storage.set_secret(password_key, password, ttl=3600)
        if success:
            logger.info(
                f"Encrypted password stored in Redis for user {user.id} (1 hour TTL)"
            )
        else:
            logger.warning(
                f"Failed to encrypt and store password in Redis for user {user.id}"
            )
    except Exception as e:
        logger.warning(
            f"Failed to store encrypted password in Redis for user {user.id}: {e}"
        )


async def _send_registration_success_messages(
    message: Message,
    state: FSMContext,
    user: User,
    session: Any,
    is_admin: bool,
    blacklist_entry: Any,
) -> None:
    """Send registration success messages and set up user."""
    # Save user.id in FSM for "Show password again" button
    await state.update_data(show_password_user_id=user.id)

    await message.answer(
        "🎉 Регистрация завершена!\\n\\n"
        f"Ваш ID: {user.id}\\n"
        f"Кошелек: {user.masked_wallet}\\n\\n"
        "Добро пожаловать в ArbitroPLEXbot! 🚀\\n\\n"
        "⚠️ **Важно:** Сохраните ваш финансовый"
        "пароль в безопасном месте!\\n"
        "Он понадобится для подтверждения финансовых операций.",
        reply_markup=show_password_keyboard(),
    )

    # Get user language for i18n
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    # Send main menu
    await message.answer(
        _("common.choose_action"),
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )

    # Ask if user wants to provide contacts (optional but recommended)
    from bot.keyboards.reply import contacts_choice_keyboard

    await message.answer(
        "📝 **Рекомендуем оставить контакты!**\\n\\n"
        "🔒 **Зачем это нужно?**\\n"
        "Если ваш Telegram-аккаунт будет угнан или"
        "заблокирован, "
        "мы сможем связаться с вами и помочь"
        "восстановить доступ к средствам.\\n\\n"
        "⚠️ **Важно:** Указывайте *реальные* данные!\\n"
        "• Телефон: ваш действующий номер\\n"
        "• Email: почта, к которой у вас есть доступ\\n\\n"
        "Хотите оставить контакты?",
        parse_mode="Markdown",
        reply_markup=contacts_choice_keyboard(),
    )

    await state.set_state(RegistrationStates.waiting_for_contacts_choice)


async def _notify_referrer_async(
    referrer_telegram_id: int,
    new_user_username: str,
    new_user_telegram_id: int,
    bot: Any,
) -> None:
    """Notify referrer about new referral (non-blocking)."""
    try:
        from app.services.referral.referral_notifications import notify_new_referral

        await notify_new_referral(
            bot=bot,
            referrer_telegram_id=referrer_telegram_id,
            new_user_username=new_user_username,
            new_user_telegram_id=new_user_telegram_id,
        )
    except Exception as e:
        logger.warning(f"Failed to notify referrer: {e}")




@router.message(RegistrationStates.waiting_for_password_confirmation)
async def process_password_confirmation(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process password confirmation and complete registration.

    Uses session_factory for short transaction during user registration.

    Args:
        message: Telegram message
        state: FSM state
        data: Additional data including session_factory
    """
    # Handle /start command
    if message.text and message.text.startswith("/start"):
        await state.clear()
        return  # Let CommandStart() handle it

    # Handle menu button
    if await _handle_menu_button_in_password_confirmation(message, state, data):
        return

    confirmation = message.text.strip()

    # Delete message with password (safe delete)
    try:
        await message.delete()
    except TelegramAPIError as e:
        logger.debug(f"Could not delete message: {e}")

    # Get data from state
    state_data = await state.get_data()
    password = state_data.get("financial_password")

    # Check if passwords match
    if confirmation != password:
        await message.answer(
            "❌ Пароли не совпадают!\n\nВведите пароль"
            "еще раз:"
        )
        await state.set_state(RegistrationStates.waiting_for_financial_password)
        return

    # Normalize wallet address to checksum format
    wallet_address = state_data.get("wallet_address")
    referrer_telegram_id = state_data.get("referrer_telegram_id")

    from app.utils.validation import normalize_bsc_address
    try:
        wallet_address = normalize_bsc_address(wallet_address)
    except ValueError as e:
        await message.answer(
            f"❌ Ошибка валидации адреса кошелька:\n{str(e)}\n\n"
            "Попробуйте начать заново: /start"
        )
        await state.clear()
        return

    # Register user (short transaction)
    session_factory = data.get("session_factory")
    session = data.get("session")

    if not session_factory:
        # Fallback to old session
        if not session:
            await message.answer(
                "❌ Системная ошибка. Отправьте /start или "
                "обратитесь в поддержку."
            )
            await state.clear()
            return
        user = await _register_user_old_pattern(
            message, state, session, wallet_address, password, referrer_telegram_id
        )
    else:
        # NEW pattern: short transaction
        user = await _register_user_new_pattern(
            message, state, session_factory,
            wallet_address, password, referrer_telegram_id
        )

    # Check if registration was successful
    if not user:
        # Error was already handled in helper functions
        return

    logger.info(
        "User registered successfully",
        extra={
            "user_id": user.id,
            "telegram_id": message.from_user.id,
        },
    )

    # Store plain password in Redis for 1 hour
    redis_client = data.get("redis_client")
    await _store_password_in_redis(user, password, redis_client)

    # Get blacklist entry for user
    is_admin = data.get("is_admin", False)
    blacklist_entry = None
    if session:
        from app.repositories.blacklist_repository import BlacklistRepository
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)

    # Send registration success messages
    await _send_registration_success_messages(
        message, state, user, session, is_admin, blacklist_entry
    )

    # Notify referrer about new referral (non-blocking)
    if referrer_telegram_id:
        bot = data.get("bot")
        if bot:
            await _notify_referrer_async(
                referrer_telegram_id,
                message.from_user.username,
                message.from_user.id,
                bot,
            )


@router.message(RegistrationStates.waiting_for_contacts_choice)
async def handle_contacts_choice(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle contacts choice during registration."""
    # РљР РРўРР§РќРћ: РѕР±СЂР°Р±Р°С‚С‹РІР°РµРј /start РїСЂСЏРјРѕ Р·РґРµСЃСЊ
    if message.text and message.text.startswith("/start"):
        logger.info(
            "handle_contacts_choice: /start caught, clearing state"
        )
        await state.clear()
        return  # РџРѕР·РІРѕР»СЏРµРј CommandStart() РѕР±СЂР°Р±РѕС‚Р°С‚СЊ СЌС‚Рѕ

    if message.text == "вњ… Р”Р°, РѕСЃС‚Р°РІРёС‚СЊ РєРѕРЅС‚Р°РєС‚С‹":
        await message.answer(
            "рџ“ћ **Р’РІРµРґРёС‚Рµ РЅРѕРјРµСЂ С‚РµР»РµС„РѕРЅР°**\n\n"
            "Р¤РѕСЂРјР°С‚: `+7XXXXXXXXXX` РёР»Рё `+380XXXXXXXXX`\n"
            "(РјРµР¶РґСѓРЅР°СЂРѕРґРЅС‹Р№ С„РѕСЂРјР°С‚ СЃ РєРѕРґРѕРј СЃС‚СЂР°РЅС‹)\n\n"
            "РР»Рё РѕС‚РїСЂР°РІСЊС‚Рµ /skip С‡С‚РѕР±С‹ РїСЂРѕРїСѓСЃС‚РёС‚СЊ:",
            parse_mode="Markdown",
        )
        await state.set_state(RegistrationStates.waiting_for_phone)
    # РќРѕСЂРјР°Р»РёР·СѓРµРј С‚РµРєСЃС‚: СѓРґР°Р»СЏРµРј FE0F (emoji variatio...
    elif message.text and message.text.replace("\ufe0f", "") in (
        "вЏ­ РџСЂРѕРїСѓСЃС‚РёС‚СЊ", "вЏ­пёЏ РџСЂРѕРїСѓСЃС‚РёС‚СЊ"
    ):
        await message.answer(
            "вњ… РљРѕРЅС‚Р°РєС‚С‹ РїСЂРѕРїСѓС‰РµРЅС‹.\n\n"
            "вљ пёЏ Р РµРєРѕРјРµРЅРґСѓРµРј РґРѕР±Р°РІРёС‚СЊ РёС… РїРѕР·Р¶Рµ РІ"
            "РЅР°СЃС‚СЂРѕР№РєР°С… РїСЂРѕС„РёР»СЏ "
            "РґР»СЏ Р·Р°С‰РёС‚С‹ РІР°С€РµРіРѕ Р°РєРєР°СѓРЅС‚Р°.",
        )
        await state.clear()
    else:
        # If user sent something else, show menu again
        from bot.keyboards.reply import contacts_choice_keyboard
        await message.answer(
            "рџ“ќ **Р РµРєРѕРјРµРЅРґСѓРµРј РѕСЃС‚Р°РІРёС‚СЊ РєРѕРЅС‚Р°РєС‚С‹!**\n\n"
            "рџ”’ Р•СЃР»Рё РІР°С€ Telegram Р±СѓРґРµС‚ СѓРіРЅР°РЅ, РјС‹ СЃРјРѕР¶РµРј РїРѕРјРѕС‡СЊ "
            "РІРѕСЃСЃС‚Р°РЅРѕРІРёС‚СЊ РґРѕСЃС‚СѓРї Рє СЃСЂРµРґСЃС‚РІР°Рј.\n\n"
            "РҐРѕС‚РёС‚Рµ РѕСЃС‚Р°РІРёС‚СЊ РєРѕРЅС‚Р°РєС‚С‹?",
            parse_mode="Markdown",
            reply_markup=contacts_choice_keyboard(),
        )


@router.message(RegistrationStates.waiting_for_phone)
async def process_phone(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process phone number."""
    # Check if message is a menu button - if so, clear state and ignore
    from bot.utils.menu_buttons import is_menu_button

    if is_menu_button(message.text):
        await state.clear()
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        from app.repositories.blacklist_repository import BlacklistRepository
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = None
        if user:
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                user.telegram_id
            )
        await message.answer(
            "рџ“Љ Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ",
            reply_markup=main_menu_reply_keyboard(
                user=user,
                blacklist_entry=blacklist_entry,
                is_admin=is_admin,
            ),
        )
        return

    skip_commands = ["/skip", "РїСЂРѕРїСѓСЃС‚РёС‚СЊ", "skip"]
    if message.text and message.text.strip().lower() in skip_commands:
        await state.update_data(phone=None)
        await state.set_state(RegistrationStates.waiting_for_email)
        await message.answer(
            "📧 Введите email "
            "(или отправьте /skip чтобы пропустить):"
        )
        return

    phone = message.text.strip() if message.text else ""

    # Strict phone validation
    import re
    # Remove spaces, dashes, parentheses
    phone_clean = re.sub(r'[\s\-\(\)]', '', phone)

    # Must start with + and contain only digits after
    phone_pattern = r'^\+\d{10,15}$'
    if phone and not re.match(phone_pattern, phone_clean):
        await message.answer(
            "вќЊ **РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ С‚РµР»РµС„РѕРЅР°!**\n\n"
            "Р’РІРµРґРёС‚Рµ РЅРѕРјРµСЂ РІ РјРµР¶РґСѓРЅР°СЂРѕРґРЅРѕРј С„РѕСЂРјР°С‚Рµ:\n"
            "вЂў `+7XXXXXXXXXX` (Р РѕСЃСЃРёСЏ)\n"
            "вЂў `+380XXXXXXXXX` (РЈРєСЂР°РёРЅР°)\n"
            "вЂў `+375XXXXXXXXX` (Р‘РµР»Р°СЂСѓСЃСЊ)\n\n"
            "РР»Рё РѕС‚РїСЂР°РІСЊС‚Рµ /skip С‡С‚РѕР±С‹ РїСЂРѕРїСѓСЃС‚РёС‚СЊ:",
            parse_mode="Markdown",
        )
        return

    # Normalize phone
    phone = phone_clean if phone else ""

    await state.update_data(phone=phone if phone else None)
    await state.set_state(RegistrationStates.waiting_for_email)

    if phone:
        await message.answer(
            "вњ… РўРµР»РµС„РѕРЅ СЃРѕС…СЂР°РЅС‘РЅ!\n\n"
            "рџ“§ **Р’РІРµРґРёС‚Рµ email**\n\n"
            "Р¤РѕСЂРјР°С‚: `example@mail.com`\n"
            "(СЂРµР°Р»СЊРЅС‹Р№ Р°РґСЂРµСЃ, Рє РєРѕС‚РѕСЂРѕРјСѓ Сѓ РІР°СЃ РµСЃС‚СЊ РґРѕСЃС‚СѓРї)\n\n"
            "РР»Рё РѕС‚РїСЂР°РІСЊС‚Рµ /skip С‡С‚РѕР±С‹ РїСЂРѕРїСѓСЃС‚РёС‚СЊ:",
            parse_mode="Markdown",
        )
    else:
        await message.answer(
            "рџ“§ **Р’РІРµРґРёС‚Рµ email**\n\n"
            "Р¤РѕСЂРјР°С‚: `example@mail.com`\n"
            "(СЂРµР°Р»СЊРЅС‹Р№ Р°РґСЂРµСЃ, Рє РєРѕС‚РѕСЂРѕРјСѓ Сѓ РІР°СЃ РµСЃС‚СЊ РґРѕСЃС‚СѓРї)\n\n"
            "РР»Рё РѕС‚РїСЂР°РІСЊС‚Рµ /skip С‡С‚РѕР±С‹ РїСЂРѕРїСѓСЃС‚РёС‚СЊ:",
            parse_mode="Markdown",
        )


@router.message(RegistrationStates.waiting_for_email)
async def process_email(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process email and save contacts."""
    # Check if message is a menu button - if so, clear state and ignore
    from bot.utils.menu_buttons import is_menu_button

    if is_menu_button(message.text):
        await state.clear()
        contacts_text = (
            "вњ… Р РµРіРёСЃС‚СЂР°С†РёСЏ Р·Р°РІРµСЂС€РµРЅР° "
            "Р±РµР· РєРѕРЅС‚Р°РєС‚РѕРІ.\n\n"
        )
        user = data.get("user")
        is_admin = data.get("is_admin", False)
        from app.repositories.blacklist_repository import BlacklistRepository
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = None
        if user:
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                user.telegram_id
            )
        await message.answer(
            "📊 Главное меню",
            reply_markup=main_menu_reply_keyboard(
                user=user,
                blacklist_entry=blacklist_entry,
                is_admin=is_admin,
            ),
        )
        return

    skip_commands = ["/skip", "РїСЂРѕРїСѓСЃС‚РёС‚СЊ", "skip"]
    if message.text and message.text.strip().lower() in skip_commands:
        email = None
    else:
        email = message.text.strip().lower() if message.text else None

        # Strict email validation
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if email and not re.match(email_pattern, email):
            await message.answer(
                "вќЊ **РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ email!**\n\n"
                "Р’РІРµРґРёС‚Рµ РєРѕСЂСЂРµРєС‚РЅС‹Р№ Р°РґСЂРµСЃ, РЅР°РїСЂРёРјРµСЂ:\n"
                "вЂў `user@gmail.com`\n"
                "вЂў `name@mail.ru`\n"
                "вЂў `example@yandex.ru`\n\n"
                "РР»Рё РѕС‚РїСЂР°РІСЊС‚Рµ /skip С‡С‚РѕР±С‹ РїСЂРѕРїСѓСЃС‚РёС‚СЊ:",
                parse_mode="Markdown",
            )
            return

    # Get phone from state (don't override data parameter)
    state_data = await state.get_data()
    phone = state_data.get("phone")

    # Update user with contacts
    # Get user from middleware data (parameter), not from state
    user_service = UserService(session)
    current_user: User | None = data.get("user")
    if not current_user:
        logger.error("process_email: user missing in middleware data")
        await message.answer(
            "вќЊ РћС€РёР±РєР° РєРѕРЅС‚РµРєСЃС‚Р° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ."
            "РџРѕРІС‚РѕСЂРёС‚Рµ /start"
        )
        return
    await user_service.update_profile(
        current_user.id,
        phone=phone,
        email=email,
    )

    contacts_text = "вњ… РљРѕРЅС‚Р°РєС‚С‹ СЃРѕС…СЂР°РЅРµРЅС‹!\n\n"
    if phone:
        contacts_text += f"рџ“ћ РўРµР»РµС„РѕРЅ: {phone}\n"
    if email:
        contacts_text += f"рџ“§ Email: {email}\n"

    if not phone and not email:
        contacts_text = (
            "вњ… Р РµРіРёСЃС‚СЂР°С†РёСЏ Р·Р°РІРµСЂС€РµРЅР° "
            "Р±РµР· РєРѕРЅС‚Р°РєС‚РѕРІ.\n\n"
        )
        contacts_text += (
            "Р'С‹ РјРѕР¶РµС‚Рµ РґРѕР±Р°РІРёС‚СЊ РёС… РїРѕР·Р¶Рµ "
            "РІ РЅР°СЃС‚СЂРѕР№РєР°С… РїСЂРѕС„РёР»СЏ."
        )
    else:
        contacts_text += (
            "\nР'С‹ РјРѕР¶РµС‚Рµ РёР·РјРµРЅРёС‚СЊ РёС… РїРѕР·Р¶Рµ "
            "РІ РЅР°СЃС‚СЂРѕР№РєР°С… РїСЂРѕС„РёР»СЏ."
        )

    # Get is_admin from middleware data
    is_admin = data.get("is_admin", False)
    from app.repositories.blacklist_repository import BlacklistRepository
    blacklist_repo = BlacklistRepository(session)
    blacklist_entry = None
    if current_user:
        blacklist_entry = await blacklist_repo.find_by_telegram_id(
            current_user.telegram_id
        )
    await message.answer(
        contacts_text,
        reply_markup=main_menu_reply_keyboard(
            user=current_user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin,
        ),
    )
    await state.clear()


@router.callback_query(F.data.startswith("show_password_"))
async def handle_show_password_again(
    callback: CallbackQuery,
    **data: Any,
) -> None:
    """
    R1-19: РџРѕРєР°Р·Р°С‚СЊ С„РёРЅР°РЅСЃРѕРІС‹Р№ РїР°СЂРѕР»СЊ РµС‰С' СЂР°Р·
    (РІ С‚РµС‡РµРЅРёРµ С‡Р°СЃР° РїРѕСЃР»Рµ СЂРµРіРёСЃС‚СЂР°С†РёРё).

    Args:
        callback: Callback query
        data: Handler data
    """
    # РР·РІР»РµРєР°РµРј user_id РёР· callback_data
    user_id_str = callback.data.replace("show_password_", "")
    try:
        user_id = int(user_id_str)
    except ValueError:
        await callback.answer(
            "вќЊ РћС€РёР±РєР°: РЅРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ Р·Р°РїСЂРѕСЃР°", show_alert=True
        )

    # РџСЂРѕРІРµСЂСЏРµРј, С‡С‚Рѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ СЃСѓС‰РµСЃС‚РІСѓРµ...
    user: User | None = data.get("user")
    if not user or user.id != user_id:
        await callback.answer(
            "вќЊ РћС€РёР±РєР°: РґРѕСЃС‚СѓРї Р·Р°РїСЂРµС‰РµРЅ",
            show_alert=True
        )
        return

    # РџРѕР»СѓС‡Р°РµРј РїР°СЂРѕР»СЊ РёР· Redis
    redis_client = data.get("redis_client")
    if not redis_client:
        await callback.answer(
            "вљ пёЏ РџР°СЂРѕР»СЊ Р±РѕР»СЊС€Рµ РЅРµРґРѕСЃС‚СѓРїРµРЅ (РїСЂРѕС€Р»Рѕ"
            "Р±РѕР»РµРµ 1 С‡Р°СЃР° СЃ РјРѕРјРµРЅС‚Р° СЂРµРіРёСЃС‚СЂР°С†РёРё).\n\n"
            "РСЃРїРѕР»СЊР·СѓР№С‚Рµ С„СѓРЅРєС†РёСЋ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ РїР°СЂРѕР»СЏ "
            "РІ РЅР°СЃС‚СЂРѕР№РєР°С….",
            show_alert=True
        )
        return

    try:
        from bot.utils.secure_storage import SecureRedisStorage

        secure_storage = SecureRedisStorage(redis_client)
        password_key = f"password:plain:{user.id}"
        plain_password = await secure_storage.get_secret(password_key)

        if not plain_password:
            await callback.answer(
                "вљ пёЏ РџР°СЂРѕР»СЊ Р±РѕР»СЊС€Рµ РЅРµРґРѕСЃС‚СѓРїРµРЅ (РїСЂРѕС€Р»Рѕ"
                "Р±РѕР»РµРµ 1 С‡Р°СЃР° СЃ РјРѕРјРµРЅС‚Р° СЂРµРіРёСЃС‚СЂР°С†РёРё).\n\n"
                "РСЃРїРѕР»СЊР·СѓР№С‚Рµ С„СѓРЅРєС†РёСЋ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ РїР°СЂРѕР»СЏ "
                "РІ РЅР°СЃС‚СЂРѕР№РєР°С….",
                show_alert=True
            )
            return

        # РџРѕРєР°Р·С‹РІР°РµРј РїР°СЂРѕР»СЊ РІ alert
        await callback.answer(
            (
                f"рџ”‘ Р’Р°С€ С„РёРЅР°РЅСЃРѕРІС‹Р№ РїР°СЂРѕР»СЊ:\n\n{plain_password}\n\n"
                "вљ пёЏ РЎРѕС…СЂР°РЅРёС‚Рµ РµРіРѕ СЃРµР№С‡Р°СЃ! "
                "РћРЅ Р±РѕР»СЊС€Рµ РЅРµ Р±СѓРґРµС‚ РїРѕРєР°Р·Р°РЅ."
            ),
            show_alert=True
        )

        logger.info(
            f"User {user.id} requested to show password again (within 1 hour window)"
        )
    except Exception as e:
        logger.error(
            f"Error retrieving encrypted password from Redis for user {user.id}: {e}",
            exc_info=True
        )
        await callback.answer(
            (
                "вќЊ РћС€РёР±РєР° РїСЂРё РїРѕР»СѓС‡РµРЅРёРё РїР°СЂРѕР»СЏ. "
                "РћР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
            ),
            show_alert=True
        )


# --- AUTH PAYMENT HANDLERS ---

from bot.constants.rules import (
    LEVELS_TABLE,
    MINIMUM_PLEX_BALANCE,
    RULES_SHORT_TEXT,
)

ECOSYSTEM_INFO = (
    "рџљЂ **Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ РІ ArbitroPLEXbot!**\n\n"
    "РњС‹ СЃС‚СЂРѕРёРј **РєСЂРёРїС‚Рѕ-С„РёР°С‚РЅСѓСЋ СЌРєРѕСЃРёСЃС‚РµРјСѓ** РЅР° Р±Р°Р·Рµ"
    "РјРѕРЅРµС‚С‹ "
    "**PLEX** Рё РІС‹СЃРѕРєРѕРґРѕС…РѕРґРЅС‹С… С‚РѕСЂРіРѕРІС‹С… СЂРѕР±РѕС‚РѕРІ.\n\n"
    "рџ“Љ **Р’Р°С€ РїРѕС‚РµРЅС†РёР°Р»СЊРЅС‹Р№ РґРѕС…РѕРґ:** РѕС‚ **30% РґРѕ 70%** РІ РґРµРЅСЊ!\n\n"
    f"рџ“‹ **РЈР РћР’РќР Р”РћРЎРўРЈРџРђ:**\n"
    f"```\n{LEVELS_TABLE}```\n"
    f"{RULES_SHORT_TEXT}\n\n"
    "в”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓ\n"
    "**Р’СЃРµ СѓСЃР»РѕРІРёСЏ СЏРІР»СЏСЋС‚СЃСЏ РћР‘РЇР—РђРўР•Р›Р¬РќР«РњР РґР»СЏ"
    "РєР°Р¶РґРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ!**"
)


@router.callback_query(F.data == "check_payment")
async def handle_check_payment(
    callback: CallbackQuery,
    state: FSMContext,
    **data: Any,
) -> None:
    """Check payment status."""
    user: User | None = data.get("user")

    if user and user.wallet_address:
        # User known, check directly
        await _check_payment_logic(callback, state, user.wallet_address, data)
    else:
        # User unknown, ask for wallet
        await callback.message.answer(
            "рџ“ќ Р’РІРµРґРёС‚Рµ Р°РґСЂРµСЃ РєРѕС€РµР»СЊРєР°, СЃ РєРѕС‚РѕСЂРѕРіРѕ Р±С‹Р»"
            "СЃРѕРІРµСЂС€РµРЅ РїРµСЂРµРІРѕРґ:\n"
            "Р¤РѕСЂРјР°С‚: `0x...`",
            parse_mode="Markdown"
        )
        await state.set_state(AuthStates.waiting_for_payment_wallet)
        await callback.answer()


@router.message(AuthStates.waiting_for_payment_wallet)
async def process_payment_wallet(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process wallet address for payment verification."""
    wallet = message.text.strip()

    # Simple validation
    if not wallet.startswith("0x") or len(wallet) != 42:
        await message.answer(
            "вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ Р°РґСЂРµСЃР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰Рµ СЂР°Р·:"
        )
        return

    # Check payment
    await _check_payment_logic(message, state, wallet, data)


async def _check_payment_logic(
    event: Message | CallbackQuery,
    state: FSMContext,
    wallet_address: str,
    data: dict[str, Any]
) -> None:
    """Core payment check logic."""
    from app.services.deposit_scan_service import DepositScanService

    # Helper to send message
    async def send(text: str, **kwargs: Any) -> None:
        if isinstance(event, Message):
            await event.answer(text, **kwargs)
        elif isinstance(event, CallbackQuery):
            await event.message.answer(text, **kwargs)

    if isinstance(event, CallbackQuery):
        await event.answer("вЏі РџСЂРѕРІРµСЂСЏРµРј...", show_alert=False)
    else:
        await event.answer("вЏі РџСЂРѕРІРµСЂСЏРµРј С‚СЂР°РЅР·Р°РєС†РёРё...")

    try:
        bs = get_blockchain_service()
        # Scan blocks: 2000 blocks lookback (~1.5 hours) to catch slightly o...
        logger.info(f"Verifying PLEX payment for {mask_address(wallet_address)} with lookback=2000")
        result = await bs.verify_plex_payment(
            sender_address=wallet_address,
            amount_plex=settings.auth_price_plex,
            lookback_blocks=2000
        )

        logger.info(f"Payment verification result: {result}")

        if result["success"]:
            # Payment found!
            redis_client = data.get("redis_client")
            db_session = data.get("session")
            user_id = event.from_user.id

            # Set session
            session_key = f"{SESSION_KEY_PREFIX}{user_id}"
            await redis_client.setex(session_key, SESSION_TTL, "1")

            # Get translator for user
            _ = get_translator("ru")
            tx_hash_short = f"{result['tx_hash'][:10]}..."
            await send(
                _('payment.confirmed_scanning', tx_hash_short=tx_hash_short),
                parse_mode="Markdown",
            )

            # Scan user deposits from blockchain
            db_user = data.get("user")
            if db_user and db_session:
                deposit_service = DepositScanService(db_session)
                scan_result = await deposit_service.scan_and_validate(db_user.id)

                if scan_result.get("success"):
                    total_deposit = scan_result.get("total_amount", 0)
                    is_valid = scan_result.get("is_valid", False)
                    required_plex = scan_result.get("required_plex", 0)

                    if is_valid:
                        # Deposit is sufficient (>= 30 USDT)
                        await send(
                            f"💰 **Ваш депозит:** {total_deposit:.2f} USDT\n"
                            f"📊 **Требуется PLEX в сутки:** "
                            f"{int(required_plex):,} PLEX\n\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"{ECOSYSTEM_INFO}",
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )

                        await state.clear()

                        await send(
                            "РќР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ РґР»СЏ РЅР°С‡Р°Р»Р° СЂР°Р±РѕС‚С‹:",
                            reply_markup=auth_continue_keyboard()
                        )
                    else:
                        # Deposit insufficient (< 30 USDT)
                        message = scan_result.get("validation_message")
                        if message:
                            await send(message, parse_mode="Markdown")

                        await send(
                            (
                                "РџРѕСЃР»Рµ РїРѕРїРѕР»РЅРµРЅРёСЏ РЅР°Р¶РјРёС‚Рµ "
                                "В«РћР±РЅРѕРІРёС‚СЊ РґРµРїРѕР·РёС‚В»:"
                            ),
                            reply_markup=auth_rescan_keyboard()
                        )
                else:
                    # Scan failed, but let user continue
                    logger.warning(f"Deposit scan failed: {scan_result.get('error')}")
                    await send(
                        "вљ пёЏ РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕСЃРєР°РЅРёСЂРѕРІР°С‚СЊ РґРµРїРѕР·РёС‚С‹. "
                        "Р’С‹ РјРѕР¶РµС‚Рµ РїСЂРѕРґРѕР»Р¶РёС‚СЊ СЂР°Р±РѕС‚Сѓ.",
                        parse_mode="Markdown"
                    )
                    await state.clear()
                    await send(
                        "РќР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ:",
                        reply_markup=auth_continue_keyboard()
                    )

                await db_session.commit()
            else:
                # No DB user context, just let them in
                await send(
                    f"{ECOSYSTEM_INFO}",
                    parse_mode="Markdown",
                    disable_web_page_preview=True
                )
                await state.clear()
                await send(
                    "РќР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ РґР»СЏ РЅР°С‡Р°Р»Р° СЂР°Р±РѕС‚С‹:",
                    reply_markup=auth_continue_keyboard()
                )

        else:
            await send(
                "вќЊ **РћРїР»Р°С‚Р° РЅРµ РЅР°Р№РґРµРЅР°**\n\n"
                "РњС‹ РїСЂРѕРІРµСЂРёР»Рё РїРѕСЃР»РµРґРЅРёРµ С‚СЂР°РЅР·Р°РєС†РёРё, РЅРѕ"
                "РЅРµ РЅР°С€Р»Рё РїРѕСЃС‚СѓРїР»РµРЅРёСЏ.\n"
                "вЂў РЈР±РµРґРёС‚РµСЃСЊ, С‡С‚Рѕ РѕС‚РїСЂР°РІРёР»Рё 10 PLEX\n"
                "вЂў РџРѕРґРѕР¶РґРёС‚Рµ 1-2 РјРёРЅСѓС‚С‹, РµСЃР»Рё С‚СЂР°РЅР·Р°РєС†РёСЏ"
                "РµС‰Рµ РІ РїСѓС‚Рё\n\n"
                "РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰Рµ СЂР°Р·:",
                reply_markup=auth_retry_keyboard(),
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Auth check failed: {e}")
        await send("вљ пёЏ РћС€РёР±РєР° РїСЂРѕРІРµСЂРєРё. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ.")


@router.callback_query(F.data == "rescan_deposits")
async def handle_rescan_deposits(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: Any,
    **data: Any,
) -> None:
    """Handle manual deposit rescan request."""
    from app.services.deposit_scan_service import DepositScanService

    # Get translator for user
    user_language = await get_user_language(session, user.id) if user else "ru"
    _ = get_translator(user_language)

    await callback.answer(_('deposit.scanning'), show_alert=False)

    if not user:
        await callback.message.answer(_('deposit.user_not_found'))
        return

    deposit_service = DepositScanService(session)
    scan_result = await deposit_service.scan_and_validate(user.id)

    if not scan_result.get("success"):
        error_msg = scan_result.get('error', 'РќРµРёР·РІРµСЃС‚РЅР°СЏ РѕС€РёР±РєР°')
        await callback.message.answer(
            f"вљ пёЏ РћС€РёР±РєР° СЃРєР°РЅРёСЂРѕРІР°РЅРёСЏ: {error_msg}"
        )
        return

    total_deposit = scan_result.get("total_amount", 0)
    is_valid = scan_result.get("is_valid", False)
    required_plex = scan_result.get("required_plex", 0)

    if is_valid:
        # Deposit now sufficient
        await session.commit()

        await callback.message.answer(
            f"вњ… **Р”РµРїРѕР·РёС‚ РїРѕРґС‚РІРµСЂР¶РґС‘РЅ!**\n\n"
            f"рџ’° **Р’Р°С€ РґРµРїРѕР·РёС‚:** {total_deposit:.2f} USDT\n"
            f"рџ“Љ **РўСЂРµР±СѓРµС‚СЃСЏ PLEX РІ СЃСѓС‚РєРё:** {int(required_plex):,} PLEX\n\n"
            f"РўРµРїРµСЂСЊ РІС‹ РјРѕР¶РµС‚Рµ РЅР°С‡Р°С‚СЊ СЂР°Р±РѕС‚Сѓ!",
            parse_mode="Markdown"
        )

        await callback.message.answer(
            "РќР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ:",
            reply_markup=auth_continue_keyboard()
        )
    else:
        # Still insufficient
        message = scan_result.get("validation_message")
        if message:
            await callback.message.answer(message, parse_mode="Markdown")

        await callback.message.answer(
            "РџРѕСЃР»Рµ РїРѕРїРѕР»РЅРµРЅРёСЏ РЅР°Р¶РјРёС‚Рµ В«РћР±РЅРѕРІРёС‚СЊ РґРµРїРѕР·РёС‚В»:",
            reply_markup=auth_rescan_keyboard()
        )


@router.callback_query(F.data == "start_after_auth")
async def handle_start_after_auth(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle start after successful auth (callback version - backward compat)."""
    await callback.answer()

    # Mimic /start command
    msg = callback.message
    msg.text = "/start"
    msg.from_user = callback.from_user

    # Call cmd_start
    await cmd_start(msg, session, state, **data)


# ============================================================================
# MESSAGE HANDLERS FOR REPLY KEYBOARDS (РђР’РўРћР РР—РђР¦РРЇ)
# ============================================================================

@router.message(AuthStates.waiting_for_wallet)
async def handle_wallet_input(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle wallet address input during authorization (Step 1)."""
    # Handle cancel (normalize emoji variation selector)
    normalized_text = (message.text or "").replace("\ufe0f", "")
    if normalized_text == "❌ Отмена":
        await state.clear()
        # Get translator for unregistered user
        _ = get_translator("ru")
        await message.answer(
            _('auth.auth_cancelled'),
            reply_markup=main_menu_reply_keyboard(),
        )
        return

    wallet = message.text.strip() if message.text else ""

    # Basic format validation
    if not wallet.startswith("0x") or len(wallet) != 42:
        # Get translator for unregistered user
        _ = get_translator("ru")
        await message.answer(
            _('auth.invalid_address'),
            parse_mode="Markdown",
            reply_markup=auth_wallet_input_keyboard(),
        )
        return

    # Optional on-chain verification (PLEX/USDT balances)
    verifier = WalletVerificationService()
    verification = await verifier.verify_wallet(wallet)

    if verification.is_onchain_ok and not verification.has_required_plex:
        # Get translator for unregistered user
        _ = get_translator("ru")
        await message.answer(
            _('auth.insufficient_plex',
              plex_balance=verification.plex_balance or 0,
              minimum_plex=MINIMUM_PLEX_BALANCE),
            parse_mode="Markdown",
        )

    # Save wallet to FSM
    await state.update_data(auth_wallet=wallet)

    # Step 2: Show invoice with QR code
    price = settings.auth_price_plex
    system_wallet = settings.auth_system_wallet_address
    token_addr = settings.auth_plex_token_address

    # Get translator for unregistered user (default language)
    _ = get_translator("ru")

    # Send text message first
    wallet_short = f"{wallet[:6]}...{wallet[-4:]}"
    await message.answer(
        _('auth.wallet_accepted',
          wallet_short=wallet_short,
          price=price,
          system_wallet=system_wallet,
          token_addr=token_addr),
        reply_markup=auth_payment_keyboard(),
        parse_mode="Markdown"
    )

    # Send QR code as photo
    from aiogram.types import BufferedInputFile

    from bot.utils.qr_generator import generate_payment_qr

    qr_bytes = generate_payment_qr(system_wallet)
    if qr_bytes:
        qr_file = BufferedInputFile(qr_bytes, filename="payment_qr.png")
        await message.answer_photo(
            photo=qr_file,
            caption=_('auth.qr_caption', system_wallet=system_wallet),
            parse_mode="Markdown"
        )

    await state.set_state(AuthStates.waiting_for_payment)


@router.message(F.text == "✅ Я оплатил")
async def handle_payment_confirmed_reply(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle payment confirmation via Reply keyboard."""
    logger.info(f"=== PAYMENT CHECK START === user {message.from_user.id}")

    # Get wallet from FSM (set in waiting_for_wallet step)
    state_data = await state.get_data()
    current_state = await state.get_state()
    logger.info(f"FSM state: {current_state}, data keys: {list(state_data.keys())}")

    wallet = state_data.get("auth_wallet")
    logger.info(f"Wallet from FSM: {mask_address(wallet)}")

    if not wallet:
        # Fallback: check if user has wallet in DB
        user: User | None = data.get("user")
        if user and user.wallet_address:
            wallet = user.wallet_address
            logger.info(f"Wallet from DB user: {mask_address(wallet)}")
        else:
            # No wallet known - ask for it
            logger.warning("No wallet found - asking user")
            await message.answer(
                "рџ“ќ Р’РІРµРґРёС‚Рµ Р°РґСЂРµСЃ РєРѕС€РµР»СЊРєР°, СЃ РєРѕС‚РѕСЂРѕРіРѕ"
                "Р±С‹Р» СЃРѕРІРµСЂС€РµРЅ РїРµСЂРµРІРѕРґ:\n"
                "Р¤РѕСЂРјР°С‚: `0x...`",
                parse_mode="Markdown"
            )
            await state.set_state(AuthStates.waiting_for_payment_wallet)
            return

    # Check payment with known wallet
    logger.info(f"Checking payment for wallet: {mask_address(wallet)}")
    await _check_payment_logic(message, state, wallet, data)


@router.message(F.text == "🚀 Начать работу")
async def handle_start_work_reply(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle start work via Reply keyboard."""
    # Mimic /start command
    # message.text = "/start"
    await cmd_start(message, session, state, **data)


@router.message(F.text == "🔄 Обновить депозит")
async def handle_rescan_deposits_reply(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: Any,
    **data: Any,
) -> None:
    """Handle deposit rescan via Reply keyboard."""
    from app.services.deposit_scan_service import DepositScanService

    # Get translator for user
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    await message.answer(_('deposit.scanning'))

    scan_service = DepositScanService(session)
    scan_result = await scan_service.scan_and_update_user_deposits(user.id)

    is_valid = scan_result.get("is_valid", False)
    total_deposit = scan_result.get("total_deposit", 0)
    required_plex = scan_result.get("required_plex", 0)

    if is_valid:
        await session.commit()

        await message.answer(
            f"вњ… **Р”РµРїРѕР·РёС‚ РїРѕРґС‚РІРµСЂР¶РґС‘РЅ!**\n\n"
            f"рџ’° **Р’Р°С€ РґРµРїРѕР·РёС‚:** {total_deposit:.2f} USDT\n"
            f"рџ“Љ **РўСЂРµР±СѓРµС‚СЃСЏ PLEX РІ СЃСѓС‚РєРё:** {int(required_plex):,} PLEX\n\n"
            f"РўРµРїРµСЂСЊ РІС‹ РјРѕР¶РµС‚Рµ РЅР°С‡Р°С‚СЊ СЂР°Р±РѕС‚Сѓ!",
            parse_mode="Markdown"
        )

        await message.answer(
            "РќР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ:",
            reply_markup=auth_continue_keyboard()
        )
    else:
        msg = scan_result.get("validation_message")
        if msg:
            await message.answer(msg, parse_mode="Markdown")

        await message.answer(
            "РџРѕСЃР»Рµ РїРѕРїРѕР»РЅРµРЅРёСЏ РЅР°Р¶РјРёС‚Рµ В«РћР±РЅРѕРІРёС‚СЊ РґРµРїРѕР·РёС‚В»:",
            reply_markup=auth_rescan_keyboard()
        )


@router.message(F.text == "🚀 Продолжить (без депозита)")
async def handle_continue_without_deposit_reply(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    **data: Any,
) -> None:
    """Handle continue without deposit via Reply keyboard."""
    # Mimic /start command
    # message.text = "/start"
    await cmd_start(message, session, state, **data)


@router.message(F.text == "🔄 Проверить снова")
async def handle_retry_payment_reply(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle payment retry via Reply keyboard."""
    # Get wallet from FSM
    state_data = await state.get_data()
    wallet = state_data.get("auth_wallet")

    if not wallet:
        # Fallback: check if user has wallet in DB
        user: User | None = data.get("user")
        if user and user.wallet_address:
            wallet = user.wallet_address
        else:
            await message.answer(
                "рџ“ќ Р’РІРµРґРёС‚Рµ Р°РґСЂРµСЃ РєРѕС€РµР»СЊРєР°, СЃ РєРѕС‚РѕСЂРѕРіРѕ"
                "Р±С‹Р» СЃРѕРІРµСЂС€РµРЅ РїРµСЂРµРІРѕРґ:\n"
                "Р¤РѕСЂРјР°С‚: `0x...`",
                parse_mode="Markdown"
            )
            await state.set_state(AuthStates.waiting_for_payment_wallet)
            return

    await _check_payment_logic(message, state, wallet, data)


@router.message(F.text == "🔑 Показать пароль ещё раз")
async def handle_show_password_reply(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle show password via Reply keyboard."""
    user: User | None = data.get("user")
    if not user:
        await message.answer("вќЊ РћС€РёР±РєР°: РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ РЅРµ РЅР°Р№РґРµРЅ")
        return

    # Get password from Redis
    redis_client = data.get("redis_client")
    if not redis_client:
        await message.answer(
            "вљ пёЏ РџР°СЂРѕР»СЊ Р±РѕР»СЊС€Рµ РЅРµРґРѕСЃС‚СѓРїРµРЅ (РїСЂРѕС€Р»Рѕ"
            "Р±РѕР»РµРµ 1 С‡Р°СЃР° СЃ РјРѕРјРµРЅС‚Р° СЂРµРіРёСЃС‚СЂР°С†РёРё).\n\n"
            "РСЃРїРѕР»СЊР·СѓР№С‚Рµ С„СѓРЅРєС†РёСЋ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ"
            "РїР°СЂРѕР»СЏ РІ РЅР°СЃС‚СЂРѕР№РєР°С…."
        )
        return

    try:
        from bot.utils.secure_storage import SecureRedisStorage

        secure_storage = SecureRedisStorage(redis_client)
        password_key = f"password:plain:{user.id}"
        plain_password = await secure_storage.get_secret(password_key)

        if not plain_password:
            await message.answer(
                "вљ пёЏ РџР°СЂРѕР»СЊ Р±РѕР»СЊС€Рµ РЅРµРґРѕСЃС‚СѓРїРµРЅ (РїСЂРѕС€Р»Рѕ"
                "Р±РѕР»РµРµ 1 С‡Р°СЃР° СЃ РјРѕРјРµРЅС‚Р° СЂРµРіРёСЃС‚СЂР°С†РёРё).\n\n"
                "РСЃРїРѕР»СЊР·СѓР№С‚Рµ С„СѓРЅРєС†РёСЋ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ"
                "РїР°СЂРѕР»СЏ РІ РЅР°СЃС‚СЂРѕР№РєР°С…."
            )
            return

        # Show password
        await message.answer(
            (
            f"рџ”‘ **Р’Р°С€ С„РёРЅР°РЅСЃРѕРІС‹Р№ РїР°СЂРѕР»СЊ:**\n\n"
            f"`{plain_password}`\n\n"
                f"вљ пёЏ РЎРѕС…СЂР°РЅРёС‚Рµ РµРіРѕ СЃРµР№С‡Р°СЃ! "
                f"РћРЅ Р±РѕР»СЊС€Рµ РЅРµ Р±СѓРґРµС‚ РїРѕРєР°Р·Р°РЅ."
            ),
            parse_mode="Markdown"
        )

        logger.info(
            f"User {user.id} requested to show password again via Reply keyboard"
        )
    except Exception as e:
        logger.error(
            f"Error retrieving encrypted password from Redis for user {user.id}: {e}",
            exc_info=True
        )
        await message.answer(
            (
                "вќЌ РћС€РёР±РєР° РїСЂРё РїРѕР»СѓС‡РµРЅРёРё РїР°СЂРѕР»СЏ. "
                "РћР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
            )
        )
