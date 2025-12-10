"""
Authentication and payment handlers.

This module contains handlers for:
- Wallet verification and payment processing
- Payment status checking
- Deposit scanning and validation
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
)
from loguru import logger

from app.config.settings import settings
from app.models.user import User
from app.services.blockchain_service import get_blockchain_service
from app.services.wallet_verification_service import WalletVerificationService
from app.utils.security import mask_address
from bot.i18n.loader import get_translator
from bot.keyboards.reply import (
    auth_continue_keyboard,
    auth_payment_keyboard,
    auth_rescan_keyboard,
    auth_retry_keyboard,
    auth_wallet_input_keyboard,
    main_menu_reply_keyboard,
)
from bot.middlewares.session_middleware import SESSION_KEY_PREFIX, SESSION_TTL
from bot.states.auth import AuthStates


router = Router()

# Constants
from bot.constants.rules import (
    LEVELS_TABLE,
    MINIMUM_PLEX_BALANCE,
    RULES_SHORT_TEXT,
    can_spend_plex,
    get_available_plex_balance,
)


ECOSYSTEM_INFO = (
    "🚀 **Добро пожаловать в ArbitroPLEXbot!**\n\n"
    "Мы строим **крипто-фиатную экосистему** на базе монеты "
    "**PLEX** и высокодоходных торговых роботов.\n\n"
    "📊 **Ваш потенциальный доход:** от **30% до 70%** в день!\n\n"
    f"📋 **УРОВНИ ДОСТУПА:**\n"
    f"```\n{LEVELS_TABLE}```\n"
    f"{RULES_SHORT_TEXT}\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "**Все условия являются ОБЯЗАТЕЛЬНЫМИ для каждого пользователя!**"
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
            "📝 Введите адрес кошелька, с которого был совершен перевод:\n"
            "Формат: `0x...`",
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
        await message.answer("❌ Неверный формат адреса. Попробуйте еще раз:")
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
        await event.answer("⏳ Проверяем...", show_alert=False)
    else:
        await event.answer("⏳ Проверяем транзакции...")

    try:
        bs = get_blockchain_service()
        # Scan blocks: 1000 blocks lookback (~50 min) in chunks of 100
        # to avoid RPC rate limits on public BSC nodes
        logger.info(f"Verifying PLEX payment for {mask_address(wallet_address)} with lookback=1000")
        result = await bs.verify_plex_payment(
            sender_address=wallet_address,
            amount_plex=settings.auth_price_plex,
            lookback_blocks=1000
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
                            f"📊 **Требуется PLEX в сутки:** {int(required_plex):,} PLEX\n\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"{ECOSYSTEM_INFO}",
                            parse_mode="Markdown",
                            disable_web_page_preview=True
                        )

                        await state.clear()

                        await send(
                            "Нажмите кнопку для начала работы:",
                            reply_markup=auth_continue_keyboard()
                        )
                    else:
                        # Deposit insufficient (< 30 USDT)
                        message = scan_result.get("validation_message")
                        if message:
                            await send(message, parse_mode="Markdown")

                        await send(
                            "После пополнения нажмите «Обновить депозит»:",
                            reply_markup=auth_rescan_keyboard()
                        )
                else:
                    # Scan failed, but let user continue
                    logger.warning(f"Deposit scan failed: {scan_result.get('error')}")
                    await send(
                        "⚠️ Не удалось просканировать депозиты. "
                        "Вы можете продолжить работу.",
                        parse_mode="Markdown"
                    )
                    await state.clear()
                    await send(
                        "Нажмите кнопку:",
                        reply_markup=auth_continue_keyboard()
                    )

                await db_session.commit()
            else:
                # No DB user - NEW USER! Need to complete registration
                # Save wallet to state and redirect to financial password input
                state_data = await state.get_data()
                wallet = state_data.get("auth_wallet")
                referrer_arg = state_data.get("pending_referrer_arg")

                logger.info(
                    f"[AUTH] New user {event.from_user.id} paid PLEX successfully. "
                    f"Redirecting to registration. Wallet: {mask_address(wallet)}"
                )

                # Import registration states and messages
                from bot.handlers.start.registration import messages
                from bot.states.registration import RegistrationStates

                # Save wallet address for registration
                await state.update_data(
                    wallet_address=wallet,
                    referrer_telegram_id=referrer_arg,
                    plex_payment_verified=True,
                    plex_tx_hash=result.get("tx_hash"),
                )

                # Ask for financial password to complete registration
                await send(
                    "✅ **Оплата подтверждена!**\n\n"
                    "Для завершения регистрации создайте финансовый пароль.\n\n"
                    f"{messages.WALLET_ACCEPTED}",
                    parse_mode="Markdown",
                )

                await state.set_state(RegistrationStates.waiting_for_financial_password)

        else:
            await send(
                "❌ **Оплата не найдена**\n\n"
                "Мы проверили последние транзакции, но не нашли поступления.\n"
                "• Убедитесь, что отправили 10 PLEX\n"
                "• Подождите 1-2 минуты, если транзакция еще в пути\n\n"
                "Попробуйте еще раз:",
                reply_markup=auth_retry_keyboard(),
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Auth check failed: {e}")
        await send("⚠️ Ошибка проверки. Попробуйте позже.")


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

    # Check if user has minimum PLEX balance
    if verification.is_onchain_ok and not verification.has_required_plex:
        # Get translator for unregistered user
        _ = get_translator("ru")
        await message.answer(
            _('auth.insufficient_plex',
              plex_balance=verification.plex_balance or 0,
              minimum_plex=MINIMUM_PLEX_BALANCE),
            parse_mode="Markdown",
        )

    # Check if user can afford authorization payment (10 PLEX)
    # while keeping minimum reserve on wallet
    auth_price = settings.auth_price_plex
    plex_balance = verification.plex_balance or 0
    if verification.is_onchain_ok and plex_balance > 0:
        if not can_spend_plex(plex_balance, auth_price):
            available = get_available_plex_balance(plex_balance)
            shortage = auth_price - float(available)
            await message.answer(
                f"⚠️ **Недостаточно свободных PLEX для авторизации**\n\n"
                f"🔒 Несгораемый минимум: **{MINIMUM_PLEX_BALANCE:,}** PLEX\n"
                f"💰 Ваш баланс: **{int(plex_balance):,}** PLEX\n"
                f"📊 Доступно для оплаты: **{int(available):,}** PLEX\n"
                f"💳 Требуется для авторизации: **{auth_price}** PLEX\n"
                f"📉 Не хватает: **{int(shortage)}** PLEX\n\n"
                f"Пополните баланс PLEX минимум на **{int(shortage)}** токенов,\n"
                f"чтобы после оплаты на кошельке осталось ≥ {MINIMUM_PLEX_BALANCE:,} PLEX.",
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
