"""
Wallet input handlers for registration flow.

Contains handlers for:
- Wallet address input
- Wallet validation
- Wallet blacklist checks
"""

from typing import Any

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.user_service import UserService
from app.utils.validation import validate_bsc_address
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.states.registration import RegistrationStates
from bot.utils.menu_buttons import is_menu_button

from . import messages
from .blacklist_checks import check_wallet_blacklist, get_blacklist_entry


router = Router()


@router.message(RegistrationStates.waiting_for_wallet)
async def process_wallet(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """
    Process wallet address.

    Uses session_factory to ensure transaction is closed before FSM state
    change.

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
                logger.warning(
                    f"Failed to get user language, using default: {e}"
                )
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
        allowed, error_msg = await rate_limiter.check_registration_limit(
            telegram_id
        )
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
                            "❌ Этот кошелек уже привязан к другому "
                            "пользователю!\n"
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
                "❌ Системная ошибка. Отправьте /start или обратитесь в "
                "поддержку."
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
