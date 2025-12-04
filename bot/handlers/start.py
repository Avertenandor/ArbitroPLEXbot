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

    # РљР РРўРР§РќРћ: Р’СЃРµРіРґР° РѕС‡РёС‰Р°РµРј СЃРѕСЃС‚РѕСЏРЅРёРµ РїСЂРё /start
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
    # Format: /start ref123456 or /start ref_123456 or /start ref_CODE
    referrer_telegram_id = None
    if message.text and len(message.text.split()) > 1:
        ref_arg = message.text.split()[1].strip()
        # Support formats: ref123456, ref_123456, ref-123456
        if ref_arg.startswith("ref"):
            try:
                # Extract value from ref code
                # Note: We remove 'ref', '_', '-' prefix/separators.
                # If the code itself contains '_' or '-',
                # this might be an issue if we strip them globally.
                # But legacy IDs were digits.
                # New codes are urlsafe base64, which can contain '-' and '_'.
                # So we should be careful about stripping.

                # Better parsing strategy:
                # 1. Remove 'ref' prefix (case insensitive?)
                # 2. If starts with '_' or '-', remove ONE leading separator.

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
                else:
                    # New Referral Code
                    # We need UserService here.
                    # Note: Creating service inside handler is fine.
                    user_service = UserService(session)
                    referrer = await user_service.get_by_referral_code(
                        clean_arg
                    )

                    if referrer:
                        referrer_telegram_id = referrer.telegram_id
                        logger.info(
                            "Referral code detected",
                            extra={
                                "ref_code": clean_arg,
                                "referrer_telegram_id": referrer_telegram_id,
                            },
                        )
                    else:
                        logger.warning(
                            "Referral code not found",
                            extra={"ref_code": clean_arg},
                        )

            except (ValueError, AttributeError) as e:
                logger.warning(
                    f"Invalid referral code format: {e}",
                    extra={"ref_code": ref_arg},
                )

    # Check if already registered
    if user:
        logger.info(
            f"cmd_start: registered user {user.telegram_id}, "
            f"clearing FSM state"
        )
        # РљР РРўРР§РќРћ: РѕС‡РёСЃС‚РёРј Р»СЋР±РѕРµ FSM СЃРѕСЃС‚РѕСЏРЅРёРµ, С‡С‚РѕР±С‹ /start РІСЃРµРіРґР° СЂР°Р±РѕС‚Р°Р»
        await state.clear()

        # R8-2: Reset bot_blocked flag if user successfully sent /start
        # (means user unblocked the bot)
        try:
            if hasattr(user, 'bot_blocked') and user.bot_blocked:
                from app.repositories.user_repository import UserRepository
                user_repo = UserRepository(session)
                await user_repo.update(user.id, bot_blocked=False)
                await session.commit()
                logger.info(
                    f"User {user.telegram_id} unblocked bot, "
                    f"flag reset in /start"
                )
        except Exception as reset_error:
            # Don't fail /start if flag reset fails
            logger.warning(f"Failed to reset bot_blocked flag: {reset_error}")

        # R13-3: Get user language for i18n
        user_language = await get_user_language(session, user.id)
        _ = get_translator(user_language)

        # Format balance properly (avoid scientific notation)
        balance_str = f"{user.balance:.8f}".rstrip('0').rstrip('.')
        if balance_str == '':
            balance_str = '0'

        # Escape username for Markdown to prevent TelegramBadRequest
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
        # 1) РћС‡РёСЃС‚РёРј СЃС‚Р°СЂСѓСЋ РєР»Р°РІРёР°С‚СѓСЂСѓ
        await message.answer(
            welcome_text,
            parse_mode="Markdown",
            disable_web_page_preview=False,
            reply_markup=ReplyKeyboardRemove(),
        )
        logger.debug("cmd_start: sending main menu keyboard")
        # 2) Р РѕС‚РїСЂР°РІРёРј РіР»Р°РІРЅРѕРµ РјРµРЅСЋ РѕС‚РґРµР»СЊРЅС‹Рј СЃРѕРѕР±С‰РµРЅРёРµРј
        # Get is_admin from middleware data
        is_admin = data.get("is_admin", False)
        logger.info(
            f"[START] cmd_start for registered user {user.telegram_id}: "
            f"is_admin={is_admin}, data keys: {list(data.keys())}"
        )
        # Get blacklist status if needed (try to get from middleware first)
        blacklist_entry = data.get("blacklist_entry")
        try:
            if blacklist_entry is None:
                from app.repositories.blacklist_repository import (
                    BlacklistRepository
                )
                blacklist_repo = BlacklistRepository(session)
                blacklist_entry = await blacklist_repo.find_by_telegram_id(
                    user.telegram_id
                )
        except (OperationalError, InterfaceError, DatabaseError) as e:
            logger.error(
                f"Database error in /start while checking blacklist "
                f"for user {user.telegram_id}: {e}",
                exc_info=True,
            )
            await message.answer(
                "вљ пёЏ РЎРёСЃС‚РµРјРЅР°СЏ РѕС€РёР±РєР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ РёР»Рё РѕР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
            )
            return
        logger.info(
            f"[START] Creating keyboard for user {user.telegram_id} with "
            f"is_admin={is_admin}, "
            f"blacklist_entry={blacklist_entry is not None}"
        )
        # R13-3: Use i18n (already loaded above)
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
        return

    # R1-3: Check blacklist for non-registered users (REGISTRATION_DENIED)
    # This check must happen BEFORE showing welcome message
    blacklist_entry = data.get("blacklist_entry")
    try:
        if blacklist_entry is None:
            from app.repositories.blacklist_repository import (
                BlacklistRepository
            )
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(
                message.from_user.id
            )

        if blacklist_entry and blacklist_entry.is_active:
            from app.models.blacklist import BlacklistActionType

            action = BlacklistActionType.REGISTRATION_DENIED
            if blacklist_entry.action_type == action:
                logger.info(
                    f"[START] Registration denied for "
                    f"telegram_id {message.from_user.id}"
                )
                await message.answer(
                    "вќЊ Р РµРіРёСЃС‚СЂР°С†РёСЏ РЅРµРґРѕСЃС‚СѓРїРЅР°.\n\n"
                    "РћР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕР№ РёРЅС„РѕСЂРјР°С†РёРё."
                )
                await state.clear()
                return
    except (OperationalError, InterfaceError, DatabaseError) as e:
        logger.error(
            f"Database error in /start while checking blacklist "
            f"for non-registered user {message.from_user.id}: {e}",
            exc_info=True,
        )
        await message.answer(
            "вљ пёЏ РЎРёСЃС‚РµРјРЅР°СЏ РѕС€РёР±РєР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ РёР»Рё РѕР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
        )
        return

    # Not registered: РїРѕРєР°Р¶РµРј РїСЂРёРІРµС‚СЃС‚РІРёРµ Рё СЃСЂР°Р·Сѓ РіР»Р°РІРЅРѕРµ РјРµРЅСЋ
    welcome_text = (
        "🚀 **Добро пожаловать в ArbitroPLEXbot!**\n\n"
        "РњС‹ СЃС‚СЂРѕРёРј **РєСЂРёРїС‚Рѕ-С„РёР°С‚РЅСѓСЋ СЌРєРѕСЃРёСЃС‚РµРјСѓ** РЅР° Р±Р°Р·Рµ РјРѕРЅРµС‚С‹ "
        "**PLEX** Рё РІС‹СЃРѕРєРѕРґРѕС…РѕРґРЅС‹С… С‚РѕСЂРіРѕРІС‹С… СЂРѕР±РѕС‚РѕРІ.\n\n"
        "рџ“Љ **Р”РѕС…РѕРґ:** РѕС‚ **30% РґРѕ 70%** РІ РґРµРЅСЊ!\n\n"
        "вљ пёЏ **РћР‘РЇР—РђРўР•Р›Р¬РќР«Р• РЈРЎР›РћР’РРЇ:**\n"
        "1пёЏвѓЈ РљР°Р¶РґС‹Р№ РґРѕР»Р»Р°СЂ РґРµРїРѕР·РёС‚Р° = **10 PLEX**\n"
        "2пёЏвѓЈ Р’Р»Р°РґРµРЅРёРµ РјРёРЅРёРјСѓРј **1 РєСЂРѕР»РёРєРѕРј** РЅР° [DEXRabbit](https://xn--80apagbbfxgmuj4j.site/)\n\n"
        "в”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓ\n"
        "**Р’Р°Р¶РЅРѕ:**\n"
        "вЂў Р Р°Р±РѕС‚Р° РІРµРґРµС‚СЃСЏ С‚РѕР»СЊРєРѕ СЃ СЃРµС‚СЊСЋ **BSC (BEP-20)**\n"
        "вЂў Р‘Р°Р·РѕРІР°СЏ РІР°Р»СЋС‚Р° РґРµРїРѕР·РёС‚РѕРІ вЂ” **USDT BEP-20**\n\n"
        "рџЊђ **РћС„РёС†РёР°Р»СЊРЅС‹Р№ СЃР°Р№С‚:**\n"
        "[arbitrage-bot.com](https://arbitrage-bot.com/)\n\n"
        "рџђ° **РќР°С€ РїР°СЂС‚РЅРµСЂ DEXRabbit:**\n"
        "Р”Р»СЏ СЂР°Р±РѕС‚С‹ РІ ArbitroPLEXbot РЅРµРѕР±С…РѕРґРёРјРѕ РєСѓРїРёС‚СЊ РјРёРЅРёРјСѓРј РѕРґРЅРѕРіРѕ РєСЂРѕР»РёРєР° "
        "РЅР° СЃР°Р№С‚Рµ РЅР°С€РµРіРѕ РїР°СЂС‚РЅРµСЂР°: [dexrabbit.site](https://xn--80apagbbfxgmuj4j.site/)\n\n"
        "Р”Р»СЏ РЅР°С‡Р°Р»Р° СЂР°Р±РѕС‚С‹ РЅРµРѕР±С…РѕРґРёРјРѕ РїСЂРѕР№С‚Рё СЂРµРіРёСЃС‚СЂР°С†РёСЋ.\n\n"
        "рџ“ќ **РЁР°Рі 1:** Р’РІРµРґРёС‚Рµ РІР°С€ BSC (BEP-20) Р°РґСЂРµСЃ РєРѕС€РµР»СЊРєР°\n"
        "Р¤РѕСЂРјР°С‚: `0x...` (42 СЃРёРјРІРѕР»Р°)\n\n"
        "вљ пёЏ **РљР РРўРР§РќРћ:** РЈРєР°Р·С‹РІР°Р№С‚Рµ С‚РѕР»СЊРєРѕ **Р›РР§РќР«Р™** РєРѕС€РµР»РµРє (Trust Wallet, MetaMask, SafePal РёР»Рё Р»СЋР±РѕР№ С…РѕР»РѕРґРЅС‹Р№ РєРѕС€РµР»РµРє).\n"
        "рџљ« **РќР• СѓРєР°Р·С‹РІР°Р№С‚Рµ** Р°РґСЂРµСЃ Р±РёСЂР¶Рё (Binance, Bybit), РёРЅР°С‡Рµ РІС‹РїР»Р°С‚С‹ РјРѕРіСѓС‚ Р±С‹С‚СЊ СѓС‚РµСЂСЏРЅС‹!"
    )

    if referrer_telegram_id:
        # Save referrer to state for later use
        await state.update_data(referrer_telegram_id=referrer_telegram_id)
        welcome_text += (
            "\n\nвњ… Р РµС„РµСЂР°Р»СЊРЅС‹Р№ РєРѕРґ РїСЂРёРЅСЏС‚! "
            "РџРѕСЃР»Рµ СЂРµРіРёСЃС‚СЂР°С†РёРё РІС‹ Р±СѓРґРµС‚Рµ РїСЂРёРІСЏР·Р°РЅС‹ Рє РїСЂРёРіР»Р°СЃРёРІС€РµРјСѓ."
        )

    # 1) РћС‡РёСЃС‚РёРј РєР»Р°РІРёР°С‚СѓСЂСѓ РІ РїСЂРёРІРµС‚СЃС‚РІРёРё
    await message.answer(
        welcome_text,
        parse_mode="Markdown",
        disable_web_page_preview=False,
        reply_markup=ReplyKeyboardRemove(),
    )
    # 2) Р”РѕР±Р°РІРёРј Р±РѕР»СЊС€РѕРµ РіР»Р°РІРЅРѕРµ РјРµРЅСЋ РѕС‚РґРµР»СЊРЅРѕ
    # R13-3: Get user language for i18n (if user exists)
    user_language = "ru"  # Default
    if user:
        try:
            user_language = await get_user_language(session, user.id)
        except Exception as e:
            logger.warning(f"Failed to get user language, using default: {e}")
            pass
    _ = get_translator(user_language)

    # For unregistered users, is_admin will be False
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

    Uses session_factory to ensure transaction is closed before FSM "
        "state change.

    Args:
        message: Telegram message
        state: FSM state
        data: Additional data including session_factory
    """
    # РљР РРўРР§РќРћ: РѕР±СЂР°Р±Р°С‚С‹РІР°РµРј /start РїСЂСЏРјРѕ Р·РґРµСЃСЊ, РЅРµ РїРѕР»Р°РіР°СЏСЃСЊ РЅР° dispatcher
    if message.text and message.text.startswith("/start"):
        logger.info(
            "process_wallet: /start caught, clearing state, showing main menu"
        )
        await state.clear()
        # РЎСЂР°Р·Сѓ РїРѕРєР°Р·С‹РІР°РµРј РіР»Р°РІРЅРѕРµ РјРµРЅСЋ
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        # РџРѕР»СѓС‡Р°РµРј session РёР· data
        session = data.get("session")
        # Try to get from middleware first
        blacklist_entry = data.get("blacklist_entry")
        # РљР РРўРР§РќРћ: РїСЂРѕРІРµСЂСЏРµРј session РїРµСЂРµРґ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј
        if blacklist_entry is None and user and session:
            try:
                from app.repositories.blacklist_repository import (
                    BlacklistRepository,
                )
                blacklist_repo = BlacklistRepository(session)
                blacklist_entry = await blacklist_repo.find_by_telegram_id(
                    user.telegram_id
                )
            except Exception as e:
                logger.warning(
                    f"Failed to get blacklist entry for user {user.telegram_id}: {e}"
                )
                blacklist_entry = None
        # R13-3: Get user language for i18n
        user_language = "ru"  # Default
        if user:
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

    # Check if message is a menu button - if so, clear state and ignore
    from bot.utils.menu_buttons import is_menu_button

    # Handle "Р РµРіРёСЃС‚СЂР°С†РёСЏ" button specially while in waiting_for_wallet state
    # This prevents the loop where clicking "Registration" clears state and shows menu again
    if message.text == "рџ“ќ Р РµРіРёСЃС‚СЂР°С†РёСЏ":
        await message.answer(
            "рџ“ќ **Р РµРіРёСЃС‚СЂР°С†РёСЏ**\n\n"
            "Р’РІРµРґРёС‚Рµ РІР°С€ BSC (BEP-20) Р°РґСЂРµСЃ РєРѕС€РµР»СЊРєР°:\n"
            "Р¤РѕСЂРјР°С‚: `0x...` (42 СЃРёРјРІРѕР»Р°)\n\n"
            "вљ пёЏ РЈРєР°Р·С‹РІР°Р№С‚Рµ С‚РѕР»СЊРєРѕ **Р›РР§РќР«Р™** РєРѕС€РµР»РµРє (Trust Wallet, MetaMask, SafePal РёР»Рё С…РѕР»РѕРґРЅС‹Р№ РєРѕС€РµР»РµРє).\n"
            "рџљ« **РќР• СѓРєР°Р·С‹РІР°Р№С‚Рµ** Р°РґСЂРµСЃ Р±РёСЂР¶Рё!",
            parse_mode="Markdown",
        )
        return

    if is_menu_button(message.text):
        logger.debug(
            f"process_wallet: menu button {message.text}, showing main menu"
        )
        await state.clear()
        # РџРѕРєР°Р¶РµРј РіР»Р°РІРЅРѕРµ РјРµРЅСЋ СЃСЂР°Р·Сѓ, РЅРµ РїРѕР»Р°РіР°СЏСЃСЊ РЅР° РїРѕРІС‚РѕСЂРЅСѓСЋ РґРёСЃРїРµС‚С‡РµСЂРёР·Р°С†РёСЋ
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        # РџРѕР»СѓС‡Р°РµРј session РёР· data
        session = data.get("session")
        blacklist_entry = None
        # РљР РРўРР§РќРћ: РїСЂРѕРІРµСЂСЏРµРј session РїРµСЂРµРґ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј
        if user and session:
            try:
                from app.repositories.blacklist_repository import (
                    BlacklistRepository,
                )
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
            "рџ“Љ Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ",
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
            await message.answer(error_msg or "РЎР»РёС€РєРѕРј РјРЅРѕРіРѕ РїРѕРїС‹С‚РѕРє СЂРµРіРёСЃС‚СЂР°С†РёРё")
            return

    # Validate wallet format using proper validation
    from app.utils.validation import validate_bsc_address

    if not validate_bsc_address(wallet_address, checksum=False):
        await message.answer(
            "вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ Р°РґСЂРµСЃР°!\n\n"
            "BSC Р°РґСЂРµСЃ РґРѕР»Р¶РµРЅ РЅР°С‡РёРЅР°С‚СЊСЃСЏ СЃ '0x' Рё СЃРѕРґРµСЂР¶Р°С‚СЊ 42 СЃРёРјРІРѕР»Р° "
            "(0x + 40 hex СЃРёРјРІРѕР»РѕРІ).\n"
            "РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰Рµ СЂР°Р·:"
        )
        return

    # R1-13: Check wallet blacklist
    session_factory = data.get("session_factory")
    if session_factory:
        try:
            async with session_factory() as session:
                async with session.begin():
                    from app.services.blacklist_service import BlacklistService
                    blacklist_service = BlacklistService(session)
                    if await blacklist_service.is_blacklisted(
                        wallet_address=wallet_address.lower()
                    ):
                        await message.answer(
                            "вќЊ Р РµРіРёСЃС‚СЂР°С†РёСЏ Р·Р°РїСЂРµС‰РµРЅР°. РћР±СЂР°С‰Р°Р№С‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
                        )
                        await state.clear()
                        return

                    # Check if wallet is already used by another user
                    # (Unique constraint)
                    from app.services.user_service import UserService
                    user_service = UserService(session)
                    existing_user = await user_service.get_by_wallet(
                        wallet_address
                    )
                    if existing_user:
                        tg_id = (
                            message.from_user.id if message.from_user else None
                        )
                        if existing_user.telegram_id != tg_id:
                            await message.answer(
                                "вќЊ Р­С‚РѕС‚ РєРѕС€РµР»РµРє СѓР¶Рµ РїСЂРёРІСЏР·Р°РЅ Рє РґСЂСѓРіРѕРјСѓ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ!\n"
                                "РџРѕР¶Р°Р»СѓР№СЃС‚Р°, РёСЃРїРѕР»СЊР·СѓР№С‚Рµ РґСЂСѓРіРѕР№ РєРѕС€РµР»РµРє."
                            )
                            return
                        else:
                            await message.answer(
                                "в„№пёЏ Р­С‚РѕС‚ РєРѕС€РµР»РµРє СѓР¶Рµ РїСЂРёРІСЏР·Р°РЅ Рє РІР°С€РµРјСѓ Р°РєРєР°СѓРЅС‚Сѓ.\n"
                                "РСЃРїРѕР»СЊР·СѓР№С‚Рµ /start РґР»СЏ РІС…РѕРґР°."
                            )
                            await state.clear()
                            return

        except (OperationalError, InterfaceError, DatabaseError) as e:
            logger.error(
                f"Database error checking wallet blacklist: {e}", exc_info=True
            )
            await message.answer(
                "вљ пёЏ РЎРёСЃС‚РµРјРЅР°СЏ РѕС€РёР±РєР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РїРѕР·Р¶Рµ РёР»Рё РѕР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
            )
            return

    # SHORT transaction scope - check wallet and close BEFORE FSM state change
    if not session_factory:
        # Fallback to old session for backward compatibility
        session = data.get("session")
        if not session:
            await message.answer(
                "вќЊ РЎРёСЃС‚РµРјРЅР°СЏ РѕС€РёР±РєР°. РћС‚РїСЂР°РІСЊС‚Рµ /start РёР»Рё "
                "РѕР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
            )
            return

        user_service = UserService(session)

        # Check if wallet is already used
        existing = await user_service.get_by_wallet(wallet_address)
    else:
        # NEW pattern: short transaction
        async with session_factory() as session:
            async with session.begin():
                user_service = UserService(session)
                existing = await user_service.get_by_wallet(wallet_address)
        # Transaction closed here, before FSM state change

    # R1-12: РљРѕС€РµР»С‘Рє СѓР¶Рµ РїСЂРёРІСЏР·Р°РЅ Рє СЃСѓС‰РµСЃС‚РІСѓСЋС‰РµРјСѓ РїРѕР»СЊР·РѕРІР°С‚РµР»СЋ
    if existing:
        telegram_id = message.from_user.id if message.from_user else None
        # Р•СЃР»Рё СЌС‚Рѕ С‚РѕС‚ Р¶Рµ telegram_id вЂ” РїСЂРµРґР»Р°РіР°РµРј /start Рё РёСЃРїРѕР»СЊР·СѓРµРј СЃС‚Р°СЂС‹Р№ Р°РєРєР°СѓРЅС‚
        if telegram_id and existing.telegram_id == telegram_id:
            await message.answer(
                "в„№пёЏ Р­С‚РѕС‚ РєРѕС€РµР»РµРє СѓР¶Рµ РїСЂРёРІСЏР·Р°РЅ Рє РІР°С€РµРјСѓ Р°РєРєР°СѓРЅС‚Сѓ.\n\n"
                "РСЃРїРѕР»СЊР·СѓР№С‚Рµ РєРѕРјР°РЅРґСѓ /start РґР»СЏ РІС…РѕРґР° РІ СЃРёСЃС‚РµРјСѓ."
            )
            await state.clear()
            return
        # Р•СЃР»Рё РґСЂСѓРіРѕР№ telegram_id вЂ” РІС‹РІРѕРґРёРј СЃРѕРѕР±С‰РµРЅРёРµ, С‡С‚Рѕ РєРѕС€РµР»С‘Рє Р·Р°РЅСЏС‚
        else:
            await message.answer(
                "вќЊ Р­С‚РѕС‚ РєРѕС€РµР»РµРє СѓР¶Рµ Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅ РґСЂСѓРіРёРј РїРѕР»СЊР·РѕРІР°С‚РµР»РµРј!\n\n"
                "РСЃРїРѕР»СЊР·СѓР№С‚Рµ РґСЂСѓРіРѕР№ Р°РґСЂРµСЃ:"
            )
            return

    # Save wallet to state
    await state.update_data(wallet_address=wallet_address)

    # Ask for financial password
    await message.answer(
        "вњ… РђРґСЂРµСЃ РєРѕС€РµР»СЊРєР° РїСЂРёРЅСЏС‚!\n\n"
        "рџ“ќ РЁР°Рі 2: РЎРѕР·РґР°Р№С‚Рµ С„РёРЅР°РЅСЃРѕРІС‹Р№ РїР°СЂРѕР»СЊ\n"
        "Р­С‚РѕС‚ РїР°СЂРѕР»СЊ Р±СѓРґРµС‚ РёСЃРїРѕР»СЊР·РѕРІР°С‚СЊСЃСЏ РґР»СЏ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ РІС‹РІРѕРґРѕРІ.\n\n"
        "РўСЂРµР±РѕРІР°РЅРёСЏ:\n"
        "вЂў РњРёРЅРёРјСѓРј 6 СЃРёРјРІРѕР»РѕРІ\n"
        "вЂў РќРµ РёСЃРїРѕР»СЊР·СѓР№С‚Рµ РїСЂРѕСЃС‚С‹Рµ РїР°СЂРѕР»Рё\n\n"
        "Р’РІРµРґРёС‚Рµ РїР°СЂРѕР»СЊ:"
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
    # РљР РРўРР§РќРћ: РїСЂРѕРїСѓСЃРєР°РµРј /start Рє РѕСЃРЅРѕРІРЅРѕРјСѓ РѕР±СЂР°Р±РѕС‚С‡РёРєСѓ
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
    # РљР РРўРР§РќРћ: РїСЂРѕРїСѓСЃРєР°РµРј /start Рє РѕСЃРЅРѕРІРЅРѕРјСѓ РѕР±СЂР°Р±РѕС‚С‡РёРєСѓ
    if message.text and message.text.startswith("/start"):
        await state.clear()
        return  # РџРѕР·РІРѕР»СЏРµРј CommandStart() РѕР±СЂР°Р±РѕС‚Р°С‚СЊ СЌС‚Рѕ

    # Check if message is a menu button - if so, clear state and ignore
    from bot.utils.menu_buttons import is_menu_button

    if is_menu_button(message.text):
        await state.clear()
        user: User | None = data.get("user")
        is_admin = data.get("is_admin", False)
        # РџРѕР»СѓС‡Р°РµРј session РёР· data
        session = data.get("session")
        blacklist_entry = None
        # РљР РРўРР§РќРћ: РїСЂРѕРІРµСЂСЏРµРј session РїРµСЂРµРґ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј
        if user and session:
            try:
                from app.repositories.blacklist_repository import (
                    BlacklistRepository,
                )
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
            "рџ“Љ Р“Р»Р°РІРЅРѕРµ РјРµРЅСЋ",
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
        await message.answer(
            "вќЊ РџР°СЂРѕР»Рё РЅРµ СЃРѕРІРїР°РґР°СЋС‚!\n\nР’РІРµРґРёС‚Рµ РїР°СЂРѕР»СЊ РµС‰Рµ СЂР°Р·:"
        )
        await state.set_state(
            RegistrationStates.waiting_for_financial_password
        )
        return

    # SHORT transaction for user registration
    wallet_address = state_data.get("wallet_address")
    referrer_telegram_id = state_data.get("referrer_telegram_id")

    # Normalize wallet address to checksum format
    from app.utils.validation import normalize_bsc_address
    try:
        wallet_address = normalize_bsc_address(wallet_address)
    except ValueError as e:
        await message.answer(
            f"вќЊ РћС€РёР±РєР° РІР°Р»РёРґР°С†РёРё Р°РґСЂРµСЃР° РєРѕС€РµР»СЊРєР°:\n{str(e)}\n\n"
            "РџРѕРїСЂРѕР±СѓР№С‚Рµ РЅР°С‡Р°С‚СЊ Р·Р°РЅРѕРІРѕ: /start"
        )
        await state.clear()
        return

    session_factory = data.get("session_factory")
    if not session_factory:
        # Fallback to old session for backward compatibility
        session = data.get("session")
        if not session:
            await message.answer(
                "вќЊ РЎРёСЃС‚РµРјРЅР°СЏ РѕС€РёР±РєР°. РћС‚РїСЂР°РІСЊС‚Рµ /start РёР»Рё "
                "РѕР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
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
                    await message.answer(
                        "Р—РґСЂР°РІСЃС‚РІСѓР№С‚Рµ, РїРѕ СЂРµС€РµРЅРёСЋ СѓС‡Р°СЃС‚РЅРёРєРѕРІ РЅР°С€РµРіРѕ "
                        "СЃРѕРѕР±С‰РµСЃС‚РІР° РІР°Рј РѕС‚РєР°Р·Р°РЅРѕ РІ СЂРµРіРёСЃС‚СЂР°С†РёРё РІ РЅР°С€РµРј "
                        "Р±РѕС‚Рµ Рё РґСЂСѓРіРёС… РёРЅСЃС‚СЂСѓРјРµРЅС‚Р°С… РЅР°С€РµРіРѕ СЃРѕРѕР±С‰РµСЃС‚РІР°."
                    )
                else:
                    await message.answer(
                        "вќЊ РћС€РёР±РєР° СЂРµРіРёСЃС‚СЂР°С†РёРё. РћР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
                    )
            else:
                await message.answer(
                    f"вќЊ РћС€РёР±РєР° СЂРµРіРёСЃС‚СЂР°С†РёРё:\n{error_msg}\n\n"
                    "РџРѕРїСЂРѕР±СѓР№С‚Рµ РЅР°С‡Р°С‚СЊ Р·Р°РЅРѕРІРѕ: /start"
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

            # FIX: Handle "User already registered" as success (Double Submit race condition)
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
                    # User not found but error says registered? Weird race or different user.
                    await message.answer(
                        "вќЊ РћС€РёР±РєР°: РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ СѓР¶Рµ Р·Р°СЂРµРіРёСЃС‚СЂРёСЂРѕРІР°РЅ, РЅРѕ РґР°РЅРЅС‹Рµ РЅРµ РЅР°Р№РґРµРЅС‹. РћР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
                    )
                    await state.clear()
                    return

            # Check if it's a blacklist error
            elif error_msg.startswith("BLACKLISTED:"):
                action_type = error_msg.split(":")[1]
                from app.models.blacklist import BlacklistActionType

                if action_type == BlacklistActionType.REGISTRATION_DENIED:
                    await message.answer(
                        "Р—РґСЂР°РІСЃС‚РІСѓР№С‚Рµ, РїРѕ СЂРµС€РµРЅРёСЋ СѓС‡Р°СЃС‚РЅРёРєРѕРІ РЅР°С€РµРіРѕ "
                        "СЃРѕРѕР±С‰РµСЃС‚РІР° РІР°Рј РѕС‚РєР°Р·Р°РЅРѕ РІ СЂРµРіРёСЃС‚СЂР°С†РёРё РІ РЅР°С€РµРј "
                        "Р±РѕС‚Рµ Рё РґСЂСѓРіРёС… РёРЅСЃС‚СЂСѓРјРµРЅС‚Р°С… РЅР°С€РµРіРѕ СЃРѕРѕР±С‰РµСЃС‚РІР°."
                    )
                else:
                    await message.answer(
                        "вќЊ РћС€РёР±РєР° СЂРµРіРёСЃС‚СЂР°С†РёРё. РћР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ."
                    )
                await state.clear()
                return
            else:
                await message.answer(
                    f"вќЊ РћС€РёР±РєР° СЂРµРіРёСЃС‚СЂР°С†РёРё:\n{error_msg}\n\n"
                    "РџРѕРїСЂРѕР±СѓР№С‚Рµ РЅР°С‡Р°С‚СЊ Р·Р°РЅРѕРІРѕ: /start"
                )
                await state.clear()
                return

    # Registration successful
    if not user:
        # Should not happen if logic above is correct
        await message.answer("вќЊ РќРµРёР·РІРµСЃС‚РЅР°СЏ РѕС€РёР±РєР° СЂРµРіРёСЃС‚СЂР°С†РёРё.")
        await state.clear()
        return

    logger.info(
        "User registered successfully",
        extra={
            "user_id": user.id,
            "telegram_id": message.from_user.id,
        },
    )

    # R1-19: РЎРѕС…СЂР°РЅСЏРµРј plain password РІ Redis РЅР° 1 С‡Р°СЃ РґР»СЏ РїРѕРІС‚РѕСЂРЅРѕРіРѕ РїРѕРєР°Р·Р°
    redis_client = data.get("redis_client")
    if redis_client and password:
        try:
            password_key = f"password:plain:{user.id}"
            # РЎРѕС…СЂР°РЅСЏРµРј РїР°СЂРѕР»СЊ РЅР° 1 С‡Р°СЃ (3600 СЃРµРєСѓРЅРґ)
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
    # РџРѕР»СѓС‡Р°РµРј session РёР· data РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ blacklist_entry
    session = data.get("session")
    blacklist_entry = None
    if session:
        from app.repositories.blacklist_repository import BlacklistRepository
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(
                user.telegram_id
            )

    # R1-19: РљРЅРѕРїРєР° РґР»СЏ РїРѕРІС‚РѕСЂРЅРѕРіРѕ РїРѕРєР°Р·Р° РїР°СЂРѕР»СЏ (Reply keyboard)
    # РЎРѕС…СЂР°РЅСЏРµРј user.id РІ FSM РґР»СЏ РѕР±СЂР°Р±РѕС‚С‡РёРєР° "РџРѕРєР°Р·Р°С‚СЊ РїР°СЂРѕР»СЊ РµС‰С‘ СЂР°Р·"
    await state.update_data(show_password_user_id=user.id)

    await message.answer(
        "рџЋ‰ Р РµРіРёСЃС‚СЂР°С†РёСЏ Р·Р°РІРµСЂС€РµРЅР°!\n\n"
        f"Р’Р°С€ ID: {user.id}\n"
        f"РљРѕС€РµР»РµРє: {user.masked_wallet}\n\n"
        "Р”РѕР±СЂРѕ РїРѕР¶Р°Р»РѕРІР°С‚СЊ РІ ArbitroPLEXbot! рџљЂ\n\n"
        "вљ пёЏ **Р’Р°Р¶РЅРѕ:** РЎРѕС…СЂР°РЅРёС‚Рµ РІР°С€ С„РёРЅР°РЅСЃРѕРІС‹Р№ РїР°СЂРѕР»СЊ РІ Р±РµР·РѕРїР°СЃРЅРѕРј РјРµСЃС‚Рµ!\n"
        "РћРЅ РїРѕРЅР°РґРѕР±РёС‚СЃСЏ РґР»СЏ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ С„РёРЅР°РЅСЃРѕРІС‹С… РѕРїРµСЂР°С†РёР№.",
        reply_markup=show_password_keyboard(),
    )

    # R13-3: Get user language for i18n
    user_language = await get_user_language(session, user.id)
    _ = get_translator(user_language)

    # РћС‚РїСЂР°РІР»СЏРµРј РіР»Р°РІРЅРѕРµ РјРµРЅСЋ РѕС‚РґРµР»СЊРЅС‹Рј СЃРѕРѕР±С‰РµРЅРёРµРј
    await message.answer(
        _("common.choose_action"),
        reply_markup=main_menu_reply_keyboard(
            user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
        ),
    )

    # Ask if user wants to provide contacts (optional but recommended)
    from bot.keyboards.reply import contacts_choice_keyboard

    await message.answer(
        "рџ“ќ **Р РµРєРѕРјРµРЅРґСѓРµРј РѕСЃС‚Р°РІРёС‚СЊ РєРѕРЅС‚Р°РєС‚С‹!**\n\n"
        "рџ”’ **Р—Р°С‡РµРј СЌС‚Рѕ РЅСѓР¶РЅРѕ?**\n"
        "Р•СЃР»Рё РІР°С€ Telegram-Р°РєРєР°СѓРЅС‚ Р±СѓРґРµС‚ СѓРіРЅР°РЅ РёР»Рё Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅ, "
        "РјС‹ СЃРјРѕР¶РµРј СЃРІСЏР·Р°С‚СЊСЃСЏ СЃ РІР°РјРё Рё РїРѕРјРѕС‡СЊ РІРѕСЃСЃС‚Р°РЅРѕРІРёС‚СЊ РґРѕСЃС‚СѓРї Рє СЃСЂРµРґСЃС‚РІР°Рј.\n\n"
        "вљ пёЏ **Р’Р°Р¶РЅРѕ:** РЈРєР°Р·С‹РІР°Р№С‚Рµ *СЂРµР°Р»СЊРЅС‹Рµ* РґР°РЅРЅС‹Рµ!\n"
        "вЂў РўРµР»РµС„РѕРЅ: РІР°С€ РґРµР№СЃС‚РІСѓСЋС‰РёР№ РЅРѕРјРµСЂ\n"
        "вЂў Email: РїРѕС‡С‚Р°, Рє РєРѕС‚РѕСЂРѕР№ Сѓ РІР°СЃ РµСЃС‚СЊ РґРѕСЃС‚СѓРї\n\n"
        "РҐРѕС‚РёС‚Рµ РѕСЃС‚Р°РІРёС‚СЊ РєРѕРЅС‚Р°РєС‚С‹?",
        parse_mode="Markdown",
        reply_markup=contacts_choice_keyboard(),
    )

    await state.set_state(RegistrationStates.waiting_for_contacts_choice)

    # Notify referrer about new referral (non-blocking)
    referrer_telegram_id = state_data.get("referrer_telegram_id")
    if referrer_telegram_id:
        try:
            from app.services.referral.referral_notifications import (
                notify_new_referral,
            )
            bot = data.get("bot")
            if bot:
                await notify_new_referral(
                    bot=bot,
                    referrer_telegram_id=referrer_telegram_id,
                    new_user_username=message.from_user.username,
                    new_user_telegram_id=message.from_user.id,
                )
        except Exception as e:
            logger.warning(f"Failed to notify referrer: {e}")


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
    # РќРѕСЂРјР°Р»РёР·СѓРµРј С‚РµРєСЃС‚: СѓРґР°Р»СЏРµРј FE0F (emoji variation selector)
    elif message.text and message.text.replace("\ufe0f", "") in (
        "вЏ­ РџСЂРѕРїСѓСЃС‚РёС‚СЊ", "вЏ­пёЏ РџСЂРѕРїСѓСЃС‚РёС‚СЊ"
    ):
        await message.answer(
            "вњ… РљРѕРЅС‚Р°РєС‚С‹ РїСЂРѕРїСѓС‰РµРЅС‹.\n\n"
            "вљ пёЏ Р РµРєРѕРјРµРЅРґСѓРµРј РґРѕР±Р°РІРёС‚СЊ РёС… РїРѕР·Р¶Рµ РІ РЅР°СЃС‚СЂРѕР№РєР°С… РїСЂРѕС„РёР»СЏ "
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
            "рџ“§ Р’РІРµРґРёС‚Рµ email (РёР»Рё РѕС‚РїСЂР°РІСЊС‚Рµ /skip С‡С‚РѕР±С‹ РїСЂРѕРїСѓСЃС‚РёС‚СЊ):",
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
            "вќЊ РћС€РёР±РєР° РєРѕРЅС‚РµРєСЃС‚Р° РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ. РџРѕРІС‚РѕСЂРёС‚Рµ /start"
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
        contacts_text = "вњ… Р РµРіРёСЃС‚СЂР°С†РёСЏ Р·Р°РІРµСЂС€РµРЅР° Р±РµР· РєРѕРЅС‚Р°РєС‚РѕРІ.\n\n"
        contacts_text += "Р’С‹ РјРѕР¶РµС‚Рµ РґРѕР±Р°РІРёС‚СЊ РёС… РїРѕР·Р¶Рµ РІ РЅР°СЃС‚СЂРѕР№РєР°С… РїСЂРѕС„РёР»СЏ."
    else:
        contacts_text += "\nР’С‹ РјРѕР¶РµС‚Рµ РёР·РјРµРЅРёС‚СЊ РёС… РїРѕР·Р¶Рµ РІ РЅР°СЃС‚СЂРѕР№РєР°С… РїСЂРѕС„РёР»СЏ."

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
    R1-19: РџРѕРєР°Р·Р°С‚СЊ С„РёРЅР°РЅСЃРѕРІС‹Р№ РїР°СЂРѕР»СЊ РµС‰С‘ СЂР°Р· (РІ С‚РµС‡РµРЅРёРµ С‡Р°СЃР° РїРѕСЃР»Рµ СЂРµРіРёСЃС‚СЂР°С†РёРё).

    Args:
        callback: Callback query
        data: Handler data
    """
    # РР·РІР»РµРєР°РµРј user_id РёР· callback_data
    user_id_str = callback.data.replace("show_password_", "")
    try:
        user_id = int(user_id_str)
    except ValueError:
        await callback.answer("вќЊ РћС€РёР±РєР°: РЅРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ Р·Р°РїСЂРѕСЃР°", show_alert=True)
        return

    # РџСЂРѕРІРµСЂСЏРµРј, С‡С‚Рѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊ СЃСѓС‰РµСЃС‚РІСѓРµС‚ Рё СЌС‚Рѕ РµРіРѕ Р·Р°РїСЂРѕСЃ
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
            "вљ пёЏ РџР°СЂРѕР»СЊ Р±РѕР»СЊС€Рµ РЅРµРґРѕСЃС‚СѓРїРµРЅ (РїСЂРѕС€Р»Рѕ Р±РѕР»РµРµ 1 С‡Р°СЃР° СЃ РјРѕРјРµРЅС‚Р° СЂРµРіРёСЃС‚СЂР°С†РёРё).\n\n"
            "РСЃРїРѕР»СЊР·СѓР№С‚Рµ С„СѓРЅРєС†РёСЋ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ РїР°СЂРѕР»СЏ РІ РЅР°СЃС‚СЂРѕР№РєР°С….",
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
                "вљ пёЏ РџР°СЂРѕР»СЊ Р±РѕР»СЊС€Рµ РЅРµРґРѕСЃС‚СѓРїРµРЅ (РїСЂРѕС€Р»Рѕ Р±РѕР»РµРµ 1 С‡Р°СЃР° СЃ РјРѕРјРµРЅС‚Р° СЂРµРіРёСЃС‚СЂР°С†РёРё).\n\n"
                "РСЃРїРѕР»СЊР·СѓР№С‚Рµ С„СѓРЅРєС†РёСЋ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ РїР°СЂРѕР»СЏ РІ РЅР°СЃС‚СЂРѕР№РєР°С….",
                show_alert=True
            )
            return

        # РџРѕРєР°Р·С‹РІР°РµРј РїР°СЂРѕР»СЊ РІ alert
        await callback.answer(
            f"рџ”‘ Р’Р°С€ С„РёРЅР°РЅСЃРѕРІС‹Р№ РїР°СЂРѕР»СЊ:\n\n{plain_password}\n\n"
            "вљ пёЏ РЎРѕС…СЂР°РЅРёС‚Рµ РµРіРѕ СЃРµР№С‡Р°СЃ! РћРЅ Р±РѕР»СЊС€Рµ РЅРµ Р±СѓРґРµС‚ РїРѕРєР°Р·Р°РЅ.",
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
            "вќЊ РћС€РёР±РєР° РїСЂРё РїРѕР»СѓС‡РµРЅРёРё РїР°СЂРѕР»СЏ. РћР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ.",
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
    "РњС‹ СЃС‚СЂРѕРёРј **РєСЂРёРїС‚Рѕ-С„РёР°С‚РЅСѓСЋ СЌРєРѕСЃРёСЃС‚РµРјСѓ** РЅР° Р±Р°Р·Рµ РјРѕРЅРµС‚С‹ "
    "**PLEX** Рё РІС‹СЃРѕРєРѕРґРѕС…РѕРґРЅС‹С… С‚РѕСЂРіРѕРІС‹С… СЂРѕР±РѕС‚РѕРІ.\n\n"
    "рџ“Љ **Р’Р°С€ РїРѕС‚РµРЅС†РёР°Р»СЊРЅС‹Р№ РґРѕС…РѕРґ:** РѕС‚ **30% РґРѕ 70%** РІ РґРµРЅСЊ!\n\n"
    f"рџ“‹ **РЈР РћР’РќР Р”РћРЎРўРЈРџРђ:**\n"
    f"```\n{LEVELS_TABLE}```\n"
    f"{RULES_SHORT_TEXT}\n\n"
    "в”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓ\n"
    "**Р’СЃРµ СѓСЃР»РѕРІРёСЏ СЏРІР»СЏСЋС‚СЃСЏ РћР‘РЇР—РђРўР•Р›Р¬РќР«РњР РґР»СЏ РєР°Р¶РґРѕРіРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ!**"
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
            "рџ“ќ Р’РІРµРґРёС‚Рµ Р°РґСЂРµСЃ РєРѕС€РµР»СЊРєР°, СЃ РєРѕС‚РѕСЂРѕРіРѕ Р±С‹Р» СЃРѕРІРµСЂС€РµРЅ РїРµСЂРµРІРѕРґ:\n"
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
        await message.answer("вќЊ РќРµРІРµСЂРЅС‹Р№ С„РѕСЂРјР°С‚ Р°РґСЂРµСЃР°. РџРѕРїСЂРѕР±СѓР№С‚Рµ РµС‰Рµ СЂР°Р·:")
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
        # Scan blocks: 2000 blocks lookback (~1.5 hours) to catch slightly older transactions
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
                            f"рџ’° **Р’Р°С€ РґРµРїРѕР·РёС‚:** {total_deposit:.2f} USDT\n"
                            f"рџ“Љ **РўСЂРµР±СѓРµС‚СЃСЏ PLEX РІ СЃСѓС‚РєРё:** {int(required_plex):,} PLEX\n\n"
                            f"в”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓв”Ѓ\n\n"
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
                            "РџРѕСЃР»Рµ РїРѕРїРѕР»РЅРµРЅРёСЏ РЅР°Р¶РјРёС‚Рµ В«РћР±РЅРѕРІРёС‚СЊ РґРµРїРѕР·РёС‚В»:",
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
                await send(f"{ECOSYSTEM_INFO}", parse_mode="Markdown", disable_web_page_preview=True)
                await state.clear()
                await send(
                    "РќР°Р¶РјРёС‚Рµ РєРЅРѕРїРєСѓ РґР»СЏ РЅР°С‡Р°Р»Р° СЂР°Р±РѕС‚С‹:",
                    reply_markup=auth_continue_keyboard()
                )

        else:
            await send(
                "вќЊ **РћРїР»Р°С‚Р° РЅРµ РЅР°Р№РґРµРЅР°**\n\n"
                "РњС‹ РїСЂРѕРІРµСЂРёР»Рё РїРѕСЃР»РµРґРЅРёРµ С‚СЂР°РЅР·Р°РєС†РёРё, РЅРѕ РЅРµ РЅР°С€Р»Рё РїРѕСЃС‚СѓРїР»РµРЅРёСЏ.\n"
                "вЂў РЈР±РµРґРёС‚РµСЃСЊ, С‡С‚Рѕ РѕС‚РїСЂР°РІРёР»Рё 10 PLEX\n"
                "вЂў РџРѕРґРѕР¶РґРёС‚Рµ 1-2 РјРёРЅСѓС‚С‹, РµСЃР»Рё С‚СЂР°РЅР·Р°РєС†РёСЏ РµС‰Рµ РІ РїСѓС‚Рё\n\n"
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
        await callback.message.answer(
            f"вљ пёЏ РћС€РёР±РєР° СЃРєР°РЅРёСЂРѕРІР°РЅРёСЏ: {scan_result.get('error', 'РќРµРёР·РІРµСЃС‚РЅР°СЏ РѕС€РёР±РєР°')}"
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
    from bot.utils.qr_generator import generate_payment_qr
    from aiogram.types import BufferedInputFile

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
                "рџ“ќ Р’РІРµРґРёС‚Рµ Р°РґСЂРµСЃ РєРѕС€РµР»СЊРєР°, СЃ РєРѕС‚РѕСЂРѕРіРѕ Р±С‹Р» СЃРѕРІРµСЂС€РµРЅ РїРµСЂРµРІРѕРґ:\n"
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
                "рџ“ќ Р’РІРµРґРёС‚Рµ Р°РґСЂРµСЃ РєРѕС€РµР»СЊРєР°, СЃ РєРѕС‚РѕСЂРѕРіРѕ Р±С‹Р» СЃРѕРІРµСЂС€РµРЅ РїРµСЂРµРІРѕРґ:\n"
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
            "вљ пёЏ РџР°СЂРѕР»СЊ Р±РѕР»СЊС€Рµ РЅРµРґРѕСЃС‚СѓРїРµРЅ (РїСЂРѕС€Р»Рѕ Р±РѕР»РµРµ 1 С‡Р°СЃР° СЃ РјРѕРјРµРЅС‚Р° СЂРµРіРёСЃС‚СЂР°С†РёРё).\n\n"
            "РСЃРїРѕР»СЊР·СѓР№С‚Рµ С„СѓРЅРєС†РёСЋ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ РїР°СЂРѕР»СЏ РІ РЅР°СЃС‚СЂРѕР№РєР°С…."
        )
        return

    try:
        from bot.utils.secure_storage import SecureRedisStorage

        secure_storage = SecureRedisStorage(redis_client)
        password_key = f"password:plain:{user.id}"
        plain_password = await secure_storage.get_secret(password_key)

        if not plain_password:
            await message.answer(
                "вљ пёЏ РџР°СЂРѕР»СЊ Р±РѕР»СЊС€Рµ РЅРµРґРѕСЃС‚СѓРїРµРЅ (РїСЂРѕС€Р»Рѕ Р±РѕР»РµРµ 1 С‡Р°СЃР° СЃ РјРѕРјРµРЅС‚Р° СЂРµРіРёСЃС‚СЂР°С†РёРё).\n\n"
                "РСЃРїРѕР»СЊР·СѓР№С‚Рµ С„СѓРЅРєС†РёСЋ РІРѕСЃСЃС‚Р°РЅРѕРІР»РµРЅРёСЏ РїР°СЂРѕР»СЏ РІ РЅР°СЃС‚СЂРѕР№РєР°С…."
            )
            return

        # Show password
        await message.answer(
            f"рџ”‘ **Р’Р°С€ С„РёРЅР°РЅСЃРѕРІС‹Р№ РїР°СЂРѕР»СЊ:**\n\n"
            f"`{plain_password}`\n\n"
            f"вљ пёЏ РЎРѕС…СЂР°РЅРёС‚Рµ РµРіРѕ СЃРµР№С‡Р°СЃ! РћРЅ Р±РѕР»СЊС€Рµ РЅРµ Р±СѓРґРµС‚ РїРѕРєР°Р·Р°РЅ.",
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
        await message.answer("вќЊ РћС€РёР±РєР° РїСЂРё РїРѕР»СѓС‡РµРЅРёРё РїР°СЂРѕР»СЏ. РћР±СЂР°С‚РёС‚РµСЃСЊ РІ РїРѕРґРґРµСЂР¶РєСѓ.")
