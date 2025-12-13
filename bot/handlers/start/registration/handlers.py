"""
Main registration flow handlers.

Contains all handler functions for the registration process:
- /start command handler
- Wallet input handler
- Password creation and confirmation handlers
- Contact information handlers (phone, email)
"""

from typing import Any

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.daily_payment_check_service import (
    DailyPaymentCheckService,
    format_daily_payment_message,
)
from app.services.user_service import UserService
from app.utils.validation import normalize_bsc_address, validate_bsc_address
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import main_menu_reply_keyboard, show_password_keyboard
from bot.middlewares.session_middleware import SESSION_KEY_PREFIX
from bot.states.registration import RegistrationStates
from bot.utils.menu_buttons import is_menu_button

from . import messages
from .blacklist_checks import (
    check_registration_blacklist,
    check_wallet_blacklist,
    get_blacklist_entry,
)
from .helpers import (
    escape_markdown,
    format_balance,
    is_skip_command,
    normalize_button_text,
    reset_bot_blocked_flag,
)
from .referral import parse_referral_code
from .validators import normalize_phone, validate_email, validate_password, validate_phone


router = Router()


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

    # CRITICAL: Always clear state on /start
    current_state = await state.get_state()
    if current_state:
        logger.info(f"Clearing FSM state: {current_state}")
    await state.clear()

    # --- PAY-TO-USE AUTHORIZATION ---
    redis_client = data.get("redis_client")
    if redis_client:
        session_key = f"{SESSION_KEY_PREFIX}{message.from_user.id}"
        if not await redis_client.exists(session_key):
            # Session expired or new user

            # Save referrer if present
            if message.text and len(message.text.split()) > 1:
                ref_arg = message.text.split()[1].strip()
                await state.update_data(pending_referrer_arg=ref_arg)

            from bot.constants.rules import LEVELS_TABLE, RULES_SHORT_TEXT
            from bot.keyboards.reply import auth_wallet_input_keyboard
            from bot.states.auth import AuthStates

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
            return
    # --------------------------------

    user: User | None = data.get("user")
    # Extract referral code from command args
    referrer_telegram_id = None
    if message.text and len(message.text.split()) > 1:
        ref_arg = message.text.split()[1].strip()
        if ref_arg.startswith("ref"):
            referrer_telegram_id = await parse_referral_code(ref_arg, session)

    # Check if already registered
    if user:
        logger.info(
            f"cmd_start: registered user {user.telegram_id}, clearing FSM state"
        )
        # CRITICAL: clear FSM state for /start to work
        await state.clear()

        # R8-2: Reset bot_blocked flag if user successfully sent /start
        await reset_bot_blocked_flag(user, session)

        # R13-3: Get user language for i18n
        user_language = await get_user_language(session, user.id)
        _ = get_translator(user_language)

        # Format balance properly
        balance_str = format_balance(user.balance)

        # Escape username for Markdown
        raw_username = user.username or _('common.user')
        safe_username = escape_markdown(raw_username)

        welcome_text = (
            f"{_('common.welcome_back', username=safe_username)}\n\n"
            f"{_('common.your_balance', balance=balance_str)}\n"
            f"{_('common.use_menu')}"
        )
        logger.debug("cmd_start: sending welcome with ReplyKeyboardRemove")
        # 1) Clear old keyboard
        await message.answer(
            welcome_text,
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=ReplyKeyboardRemove(),
        )
        logger.debug("cmd_start: sending main menu keyboard")
        # 2) Send main menu as separate message
        is_admin = data.get("is_admin", False)
        logger.info(
            f"[START] cmd_start for registered user {user.telegram_id}: "
            f"is_admin={is_admin}, data keys: {list(data.keys())}"
        )
        # Get blacklist status
        blacklist_entry = await get_blacklist_entry(user.telegram_id, session)
        logger.info(
            f"[START] Creating keyboard for user {user.telegram_id} with "
            f"is_admin={is_admin}, "
            f"blacklist_entry={blacklist_entry is not None}"
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

        # --- CHECK DAILY PAYMENT STATUS ---
        # Show payment status message after login
        try:
            payment_check_service = DailyPaymentCheckService(session)
            payment_status = await payment_check_service.check_daily_payment_status(
                user.id
            )

            # Only show message if user has deposits
            if not payment_status.get("no_deposits") and not payment_status.get("error"):
                payment_message = format_daily_payment_message(
                    payment_status, user_language
                )
                if payment_message:
                    # Send payment status message
                    await message.answer(
                        payment_message,
                        parse_mode="Markdown",
                    )

                    # If not paid, send QR code for payment
                    if not payment_status.get("is_paid"):
                        from aiogram.types import BufferedInputFile

                        from bot.utils.qr_generator import generate_payment_qr

                        wallet_address = payment_status.get("wallet_address", "")
                        required_plex = payment_status.get("required_plex", 0)

                        qr_bytes = generate_payment_qr(wallet_address)
                        if qr_bytes:
                            qr_file = BufferedInputFile(
                                qr_bytes, filename="payment_qr.png"
                            )
                            await message.answer_photo(
                                photo=qr_file,
                                caption=(
                                    f"📱 **QR-код для оплаты**\n\n"
                                    f"Кошелёк:\n`{wallet_address}`\n\n"
                                    f"Сумма: **{int(required_plex):,}** PLEX"
                                ),
                                parse_mode="Markdown",
                            )
                        logger.info(
                            f"[START] Sent daily payment reminder to user "
                            f"{user.telegram_id}, required: {required_plex} PLEX"
                        )
        except Exception as e:
            logger.error(
                f"[START] Failed to check daily payment for user {user.telegram_id}: {e}"
            )
        # ----------------------------------

        return

    # R1-3: Check blacklist for non-registered users (REGISTRATION_DENIED)
    is_blocked, error_msg = await check_registration_blacklist(
        message.from_user.id, session
    )
    if is_blocked:
        await message.answer(error_msg)
        await state.clear()
        return

    # Not registered: show welcome and menu
    welcome_text = messages.WELCOME_MESSAGE

    if referrer_telegram_id:
        # Save referrer to state for later use
        await state.update_data(referrer_telegram_id=referrer_telegram_id)
        welcome_text += messages.REFERRAL_ACCEPTED

    # 1) Clear keyboard in welcome
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        disable_web_page_preview=False,
        reply_markup=ReplyKeyboardRemove(),
    )
    # 2) Send main menu separately
    user_language = "ru"  # Default
    if user:
        try:
            user_language = await get_user_language(session, user.id)
        except Exception as e:
            logger.warning(f"Failed to get user language, using default: {e}")

    _ = get_translator(user_language)

    is_admin = data.get("is_admin", False)
    await message.answer(
        _("common.choose_action"),
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=None, is_admin=is_admin
        ),
    )

    await state.set_state(RegistrationStates.waiting_for_wallet)


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
    # CRITICAL: handle /start here, not dispatcher
    if message.text and message.text.startswith("/start"):
        logger.info(
            "process_wallet: /start caught, clearing state, showing main menu"
        )
        await state.clear()
        # Show main menu immediately
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        session = data.get("session")
        blacklist_entry = await get_blacklist_entry(
            user.telegram_id if user else None, session
        )
        # R13-3: Get user language for i18n
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
        return

    # Handle Registration button in waiting_for_wallet
    if message.text == "📝 Регистрация":
        await message.answer(
            messages.REGISTRATION_PROMPT,
            parse_mode="Markdown",
        )
        return

    if is_menu_button(message.text):
        logger.debug(
            f"process_wallet: menu button {message.text}, showing main menu"
        )
        await state.clear()
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        session = data.get("session")
        blacklist_entry = await get_blacklist_entry(
            user.telegram_id if user else None, session
        )
        await message.answer(
            messages.MAIN_MENU_TEXT,
            reply_markup=main_menu_reply_keyboard(
                user=user,
                blacklist_entry=blacklist_entry,
                is_admin=is_admin,
            ),
        )
        return

    wallet_address = message.text.strip()

    # Check registration rate limit
    telegram_id = message.from_user.id if message.from_user else None
    if telegram_id:
        from bot.utils.operation_rate_limit import OperationRateLimiter

        redis_client = data.get("redis_client")
        rate_limiter = OperationRateLimiter(redis_client=redis_client)
        allowed, error_msg = await rate_limiter.check_registration_limit(telegram_id)
        if not allowed:
            await message.answer(error_msg or "Много попыток")
            return

    # Validate wallet format
    if not validate_bsc_address(wallet_address, checksum=False):
        await message.answer(messages.INVALID_WALLET_FORMAT)
        return

    # R1-13: Check wallet blacklist
    session_factory = data.get("session_factory")
    if session_factory:
        async with session_factory() as session:
            async with session.begin():
                # Check wallet blacklist
                is_blocked, error_msg = await check_wallet_blacklist(
                    wallet_address, session
                )
                if is_blocked:
                    await message.answer(error_msg)
                    await state.clear()
                    return

                # Check if wallet is already used by another user
                user_service = UserService(session)
                existing_user = await user_service.get_by_wallet(wallet_address)
                if existing_user:
                    tg_id = message.from_user.id if message.from_user else None
                    if existing_user.telegram_id != tg_id:
                        await message.answer(
                            "❌ Этот кошелек уже привязан к другому пользователю!\n"
                            "Пожалуйста, используйте другой кошелек."
                        )
                        return
                    else:
                        await message.answer(messages.WALLET_ALREADY_LINKED)
                        await state.clear()
                        return

    # SHORT transaction scope - check wallet and close BEFORE FSM state change
    if not session_factory:
        # Fallback to old session for backward compatibility
        session = data.get("session")
        if not session:
            await message.answer(
                "❌ Системная ошибка. Отправьте /start или обратитесь в поддержку."
            )
            return

        user_service = UserService(session)
        existing = await user_service.get_by_wallet(wallet_address)
    else:
        # NEW pattern: short transaction
        async with session_factory() as session:
            async with session.begin():
                user_service = UserService(session)
                existing = await user_service.get_by_wallet(wallet_address)
        # Transaction closed here, before FSM state change

    # R1-12: Wallet already linked to existing user
    if existing:
        telegram_id = message.from_user.id if message.from_user else None
        # If same telegram_id - suggest /start
        if telegram_id and existing.telegram_id == telegram_id:
            await message.answer(messages.WALLET_ALREADY_LINKED)
            await state.clear()
            return
        # If different telegram_id - wallet taken
        else:
            await message.answer(messages.WALLET_ALREADY_REGISTERED)
            return

    # Save wallet to state
    await state.update_data(wallet_address=wallet_address)

    # Ask for financial password
    await message.answer(messages.WALLET_ACCEPTED)

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
    # CRITICAL: pass /start to main handler
    if message.text and message.text.startswith("/start"):
        await state.clear()
        return  # Let CommandStart() handle this

    # Check if message is a menu button
    if is_menu_button(message.text):
        await state.clear()
        # Get session from data if not provided
        if session is None:
            session = data.get("session")
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        blacklist_entry = await get_blacklist_entry(
            user.telegram_id if user else None, session
        )
        await message.answer(
            messages.MAIN_MENU_TEXT,
            reply_markup=main_menu_reply_keyboard(
                user=user,
                blacklist_entry=blacklist_entry,
                is_admin=is_admin,
            ),
        )
        return

    password = message.text.strip()

    # Validate password
    is_valid, error_msg = validate_password(password)
    if not is_valid:
        await message.answer(error_msg)
        return

    # Delete message with password (safe delete)
    try:
        await message.delete()
    except TelegramAPIError as e:
        logger.debug(f"Could not delete message: {e}")

    # Save password to state
    await state.update_data(financial_password=password)

    # Ask for confirmation
    await message.answer(messages.PASSWORD_ACCEPTED)

    await state.set_state(RegistrationStates.waiting_for_password_confirmation)


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
    # CRITICAL: pass /start to main handler
    if message.text and message.text.startswith("/start"):
        await state.clear()
        return  # Let CommandStart() handle this

    # Check if message is a menu button
    if is_menu_button(message.text):
        await state.clear()
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        session = data.get("session")
        blacklist_entry = await get_blacklist_entry(
            user.telegram_id if user else None, session
        )
        await message.answer(
            messages.MAIN_MENU_TEXT,
            reply_markup=main_menu_reply_keyboard(
                user=user,
                blacklist_entry=blacklist_entry,
                is_admin=is_admin,
            ),
        )
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
        await message.answer(messages.PASSWORDS_MISMATCH)
        await state.set_state(RegistrationStates.waiting_for_financial_password)
        return

    # SHORT transaction for user registration
    wallet_address = state_data.get("wallet_address")
    referrer_telegram_id = state_data.get("referrer_telegram_id")

    # Normalize wallet address to checksum format
    try:
        wallet_address = normalize_bsc_address(wallet_address)
    except ValueError as e:
        await message.answer(
            f"❌ Ошибка валидации адреса кошелька:\n{str(e)}\n\n"
            "Попробуйте начать заново: /start"
        )
        await state.clear()
        return

    session_factory = data.get("session_factory")
    if not session_factory:
        # Fallback to old session for backward compatibility
        session = data.get("session")
        if not session:
            await message.answer(
                "❌ Системная ошибка. Отправьте /start или обратитесь в поддержку."
            )
            await state.clear()
            return
        user_service = UserService(session)
        try:
            user = await user_service.register_user(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                wallet_address=wallet_address,
                financial_password=password,
                referrer_telegram_id=referrer_telegram_id,
            )
        except ValueError as e:
            error_msg = str(e)
            # Check if it's a blacklist error
            if error_msg.startswith("BLACKLISTED:"):
                action_type = error_msg.split(":")[1]
                from app.models.blacklist import BlacklistActionType

                if action_type == BlacklistActionType.REGISTRATION_DENIED:
                    await message.answer(messages.BLACKLIST_REGISTRATION_DENIED)
                else:
                    await message.answer(messages.BLACKLIST_GENERAL_ERROR)
            else:
                await message.answer(
                    f"❌ Ошибка регистрации:\n{error_msg}\n\n"
                    "Попробуйте начать заново: /start"
                )
            await state.clear()
            return
    else:
        # NEW pattern: short transaction for registration
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
            # Transaction closed here
        except ValueError as e:
            error_msg = str(e)

            # FIX: Handle "User already registered" as success (Double Submit)
            if error_msg == "User already registered":
                logger.info(
                    f"Double registration attempt caught for user {message.from_user.id} - checking existing user"
                )
                # Try to fetch existing user to confirm it's really them
                async with session_factory() as session:
                    user_service = UserService(session)
                    user = await user_service.get_by_telegram_id(message.from_user.id)

                if user:
                    logger.info(
                        f"User {user.id} found, treating double registration error as success"
                    )
                    # Proceed to success flow below
                else:
                    # User not found but error says registered? Weird race condition
                    await message.answer(messages.USER_ALREADY_REGISTERED_ERROR)
                    await state.clear()
                    return

            # Check if it's a blacklist error
            elif error_msg.startswith("BLACKLISTED:"):
                action_type = error_msg.split(":")[1]
                from app.models.blacklist import BlacklistActionType

                if action_type == BlacklistActionType.REGISTRATION_DENIED:
                    await message.answer(messages.BLACKLIST_REGISTRATION_DENIED)
                else:
                    await message.answer(messages.BLACKLIST_GENERAL_ERROR)
                await state.clear()
                return
            else:
                await message.answer(
                    f"❌ Ошибка регистрации:\n{error_msg}\n\n"
                    "Попробуйте начать заново: /start"
                )
                await state.clear()
                return

    # Registration successful
    if not user:
        # Should not happen if logic above is correct
        await message.answer("❌ Неизвестная ошибка регистрации.")
        await state.clear()
        return

    logger.info(
        "User registered successfully",
        extra={
            "user_id": user.id,
            "telegram_id": message.from_user.id,
        },
    )

    # Index user's wallet for instant transaction history
    try:
        # Run indexing in background (don't block registration)
        import asyncio

        from jobs.tasks.blockchain_indexer_task import index_user_on_registration
        asyncio.create_task(
            index_user_on_registration(
                wallet_address=wallet_address,
                user_id=user.id,
            )
        )
        logger.info(f"Started wallet indexing for user {user.id}")
    except Exception as index_error:
        logger.warning(f"Failed to start wallet indexing: {index_error}")

    # R1-19: Save plain password in Redis for 1 hour
    redis_client = data.get("redis_client")
    if redis_client and password:
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

    # Get is_admin from middleware data
    is_admin = data.get("is_admin", False)
    # Get session for blacklist_entry
    session = data.get("session")
    blacklist_entry = await get_blacklist_entry(user.telegram_id, session)

    # R1-19: Button for showing password again
    # Save user.id in FSM for "Show password again" handler
    await state.update_data(show_password_user_id=user.id)

    await message.answer(
        messages.REGISTRATION_COMPLETE.format(
            user_id=user.id,
            masked_wallet=user.masked_wallet,
        ),
        reply_markup=show_password_keyboard(),
    )

    # R13-3: Get user language for i18n
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    # Send main menu as separate message
    await message.answer(
        _("common.choose_action"),
        reply_markup=main_menu_reply_keyboard(
            user=user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin,
        ),
    )

    await state.clear()


@router.message(RegistrationStates.waiting_for_contacts_choice)
async def handle_contacts_choice(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle contacts choice during registration."""
    # CRITICAL: handle /start here
    if message.text and message.text.startswith("/start"):
        logger.info("handle_contacts_choice: /start caught, clearing state")
        await state.clear()
        return  # Let CommandStart() handle this

    if message.text == "✅ Да, оставить контакты":
        await message.answer(
            messages.PHONE_PROMPT,
            parse_mode="Markdown",
        )
        await state.set_state(RegistrationStates.waiting_for_phone)
    # Normalize text: remove FE0F (emoji variation selector)
    elif message.text and normalize_button_text(message.text) in (
        "⏭ Пропустить", "⏭️ Пропустить"
    ):
        await message.answer(messages.CONTACTS_CHOICE_SKIP)
        await state.clear()
    else:
        # If user sent something else, show menu again
        from bot.keyboards.reply import contacts_choice_keyboard
        await message.answer(
            messages.CONTACTS_CHOICE_PROMPT,
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
    # Check if message is a menu button
    if is_menu_button(message.text):
        await state.clear()
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        blacklist_entry = await get_blacklist_entry(user.telegram_id if user else None, session)
        await message.answer(
            messages.MAIN_MENU_TEXT,
            reply_markup=main_menu_reply_keyboard(
                user=user,
                blacklist_entry=blacklist_entry,
                is_admin=is_admin,
            ),
        )
        return

    if is_skip_command(message.text):
        await state.update_data(phone=None)
        await state.set_state(RegistrationStates.waiting_for_email)
        await message.answer(messages.EMAIL_PROMPT)
        return

    phone = message.text.strip() if message.text else ""

    # Validate phone
    is_valid, error_msg = validate_phone(phone)
    if not is_valid:
        await message.answer(error_msg, parse_mode="Markdown")
        return

    # Normalize phone
    phone = normalize_phone(phone) if phone else ""

    await state.update_data(phone=phone if phone else None)
    await state.set_state(RegistrationStates.waiting_for_email)

    if phone:
        await message.answer(messages.PHONE_ACCEPTED, parse_mode="Markdown")
    else:
        await message.answer(messages.EMAIL_PROMPT, parse_mode="Markdown")


@router.message(RegistrationStates.waiting_for_email)
async def process_email(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process email and save contacts."""
    # Check if message is a menu button
    if is_menu_button(message.text):
        await state.clear()
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        blacklist_entry = await get_blacklist_entry(user.telegram_id if user else None, session)
        await message.answer(
            messages.MAIN_MENU_TEXT,
            reply_markup=main_menu_reply_keyboard(
                user=user,
                blacklist_entry=blacklist_entry,
                is_admin=is_admin,
            ),
        )
        return

    if is_skip_command(message.text):
        email = None
    else:
        email = message.text.strip().lower() if message.text else None

        # Validate email
        is_valid, error_msg = validate_email(email)
        if not is_valid:
            await message.answer(error_msg, parse_mode="Markdown")
            return

    # Get phone from state
    state_data = await state.get_data()
    phone = state_data.get("phone")

    # Update user with contacts
    user_service = UserService(session)
    current_user: User | None = data.get("user")
    if not current_user:
        logger.error("process_email: user missing in middleware data")
        await message.answer(
            "❌ Ошибка контекста пользователя. Повторите /start"
        )
        return
    await user_service.update_profile(
        current_user.id,
        phone=phone,
        email=email,
    )

    contacts_text = "✅ Контакты сохранены!\n\n"
    if phone:
        contacts_text += f"📞 Телефон: {phone}\n"
    if email:
        contacts_text += f"📧 Email: {email}\n"

    if not phone and not email:
        contacts_text = messages.CONTACTS_SKIPPED
    else:
        contacts_text += "\nВы можете изменить их позже в настройках профиля."

    # Get is_admin from middleware data
    is_admin = data.get("is_admin", False)
    blacklist_entry = await get_blacklist_entry(current_user.telegram_id, session)
    await message.answer(
        contacts_text,
        reply_markup=main_menu_reply_keyboard(
            user=current_user,
            blacklist_entry=blacklist_entry,
            is_admin=is_admin,
        ),
    )
    await state.clear()
