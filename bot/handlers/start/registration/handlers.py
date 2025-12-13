"""
Main registration flow handlers.

Contains all handler functions for the registration process:
- /start command handler
- Router registration from sub-modules
"""

from typing import Any

from aiogram import Router
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
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.middlewares.session_middleware import SESSION_KEY_PREFIX
from bot.states.registration import RegistrationStates

from . import messages
from .blacklist_checks import check_registration_blacklist, get_blacklist_entry
from .helpers import escape_markdown, format_balance, reset_bot_blocked_flag
from .referral import parse_referral_code


# Main router for registration flow
router = Router()

# Import and include sub-routers from specialized modules
from . import finpass_handlers, verification_handlers, wallet_handlers

router.include_router(wallet_handlers.router)
router.include_router(finpass_handlers.router)
router.include_router(verification_handlers.router)


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
            f"cmd_start: registered user {user.telegram_id}, "
            f"clearing FSM state"
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
            f"[START] Main menu keyboard sent successfully to user "
            f"{user.telegram_id}"
        )

        # --- CHECK DAILY PAYMENT STATUS ---
        # Show payment status message after login
        try:
            payment_check_service = DailyPaymentCheckService(session)
            payment_status = (
                await payment_check_service.check_daily_payment_status(
                    user.id
                )
            )

            # Only show message if user has deposits
            if not payment_status.get("no_deposits") and not (
                payment_status.get("error")
            ):
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

                        wallet_address = payment_status.get(
                            "wallet_address", ""
                        )
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
                            f"{user.telegram_id}, required: {required_plex} "
                            f"PLEX"
                        )
        except Exception as e:
            logger.error(
                f"[START] Failed to check daily payment for user "
                f"{user.telegram_id}: {e}"
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
            logger.warning(
                f"Failed to get user language, using default: {e}"
            )

    _ = get_translator(user_language)

    is_admin = data.get("is_admin", False)
    await message.answer(
        _("common.choose_action"),
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=None, is_admin=is_admin
        ),
    )

    await state.set_state(RegistrationStates.waiting_for_wallet)
