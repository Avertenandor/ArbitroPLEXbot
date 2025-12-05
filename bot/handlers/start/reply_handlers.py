"""
Reply keyboard button handlers.

This module contains handlers for reply keyboard buttons related to:
- Payment confirmation
- Deposit rescanning
- Starting work after auth
- Password display
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.utils.security import mask_address
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import auth_continue_keyboard, auth_rescan_keyboard
from bot.states.auth import AuthStates

router = Router()


@router.message(F.text == "✅ Я оплатил")
async def handle_payment_confirmed_reply(
    message: Message,
    state: FSMContext,
    **data: Any,
) -> None:
    """Handle payment confirmation via Reply keyboard."""
    logger.info(f"=== PAYMENT CHECK START === user {message.from_user.id}")

    # Import _check_payment_logic from authentication module
    from .authentication import _check_payment_logic

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
                "📝 Введите адрес кошелька, с которого был совершен перевод:\n"
                "Формат: `0x...`",
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
    # Import cmd_start from registration module
    from .registration import cmd_start

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
            f"✅ **Депозит подтверждён!**\n\n"
            f"💰 **Ваш депозит:** {total_deposit:.2f} USDT\n"
            f"📊 **Требуется PLEX в сутки:** {int(required_plex):,} PLEX\n\n"
            f"Теперь вы можете начать работу!",
            parse_mode="Markdown"
        )

        await message.answer(
            "Нажмите кнопку:",
            reply_markup=auth_continue_keyboard()
        )
    else:
        msg = scan_result.get("validation_message")
        if msg:
            await message.answer(msg, parse_mode="Markdown")

        await message.answer(
            "После пополнения нажмите «Обновить депозит»:",
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
    # Import cmd_start from registration module
    from .registration import cmd_start

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
    # Import _check_payment_logic from authentication module
    from .authentication import _check_payment_logic

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
                "📝 Введите адрес кошелька, с которого был совершен перевод:\n"
                "Формат: `0x...`",
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
        await message.answer("❌ Ошибка: пользователь не найден")
        return

    # Get password from Redis
    redis_client = data.get("redis_client")
    if not redis_client:
        await message.answer(
            "⚠️ Пароль больше недоступен (прошло более 1 часа с момента регистрации).\n\n"
            "Используйте функцию восстановления пароля в настройках."
        )
        return

    try:
        from bot.utils.secure_storage import SecureRedisStorage

        secure_storage = SecureRedisStorage(redis_client)
        password_key = f"password:plain:{user.id}"
        plain_password = await secure_storage.get_secret(password_key)

        if not plain_password:
            await message.answer(
                "⚠️ Пароль больше недоступен (прошло более 1 часа с момента регистрации).\n\n"
                "Используйте функцию восстановления пароля в настройках."
            )
            return

        # Show password
        await message.answer(
            f"🔑 **Ваш финансовый пароль:**\n\n"
            f"`{plain_password}`\n\n"
            f"⚠️ Сохраните его сейчас! Он больше не будет показан.",
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
            "❌ Ошибка при получении пароля. Обратитесь в поддержку."
        )
