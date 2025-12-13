"""
Financial password handlers for registration flow.

Contains handlers for:
- Financial password input
- Password confirmation
- Password validation
"""

from typing import Any

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import UserService
from app.utils.validation import normalize_bsc_address
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import main_menu_reply_keyboard, show_password_keyboard
from bot.states.registration import RegistrationStates
from bot.utils.menu_buttons import is_menu_button

from . import messages
from .blacklist_checks import get_blacklist_entry
from .validators import validate_password


router = Router()


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
                "❌ Системная ошибка. Отправьте /start или обратитесь в "
                "поддержку."
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
                    f"Double registration attempt caught for user "
                    f"{message.from_user.id} - checking existing user"
                )
                # Try to fetch existing user to confirm it's really them
                async with session_factory() as session:
                    user_service = UserService(session)
                    user = await user_service.get_by_telegram_id(
                        message.from_user.id
                    )

                if user:
                    logger.info(
                        f"User {user.id} found, treating double registration "
                        f"error as success"
                    )
                    # Proceed to success flow below
                else:
                    # User not found but error says registered? Race condition
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

        from jobs.tasks.blockchain_indexer_task import (
            index_user_on_registration,
        )
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
            success = await secure_storage.set_secret(
                password_key, password, ttl=3600
            )
            if success:
                logger.info(
                    f"Encrypted password stored in Redis for user {user.id} "
                    f"(1 hour TTL)"
                )
            else:
                logger.warning(
                    f"Failed to encrypt and store password in Redis for user "
                    f"{user.id}"
                )
        except Exception as e:
            logger.warning(
                f"Failed to store encrypted password in Redis for user "
                f"{user.id}: {e}"
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
