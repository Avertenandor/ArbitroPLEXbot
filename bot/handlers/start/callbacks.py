"""
Callback query handlers.

This module contains handlers for inline keyboard button callbacks:
- Show password callback
- Rescan deposits callback
- Start after auth callback
"""

from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from bot.i18n.loader import get_translator, get_user_language
from bot.keyboards.reply import auth_continue_keyboard, auth_rescan_keyboard

router = Router()


@router.callback_query(F.data.startswith("show_password_"))
async def handle_show_password_again(
    callback: CallbackQuery,
    **data: Any,
) -> None:
    """
    R1-19: Показать финансовый пароль ещё раз (в течение часа после регистрации).

    Args:
        callback: Callback query
        data: Handler data
    """
    # Извлекаем user_id из callback_data
    user_id_str = callback.data.replace("show_password_", "")
    try:
        user_id = int(user_id_str)
    except ValueError:
        await callback.answer("❌ Ошибка: неверный формат запроса", show_alert=True)
        return

    # Проверяем, что пользователь существует и совпадает
    user: User | None = data.get("user")
    if not user or user.id != user_id:
        await callback.answer(
            "❌ Ошибка: доступ запрещен",
            show_alert=True
        )
        return

    # Получаем пароль из Redis
    redis_client = data.get("redis_client")
    if not redis_client:
        await callback.answer(
            "⚠️ Пароль больше недоступен (прошло более 1 часа с момента регистрации).\n\n"
            "Используйте функцию восстановления пароля в настройках.",
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
                "⚠️ Пароль больше недоступен (прошло более 1 часа с момента регистрации).\n\n"
                "Используйте функцию восстановления пароля в настройках.",
                show_alert=True
            )
            return

        # Показываем пароль в alert
        await callback.answer(
            f"🔑 Ваш финансовый пароль:\n\n{plain_password}\n\n"
            "⚠️ Сохраните его сейчас! Он больше не будет показан.",
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
            "❌ Ошибка при получении пароля. Обратитесь в поддержку.",
            show_alert=True
        )


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
            f"⚠️ Ошибка сканирования: {scan_result.get('error', 'Неизвестная ошибка')}"
        )
        return

    total_deposit = scan_result.get("total_amount", 0)
    is_valid = scan_result.get("is_valid", False)
    required_plex = scan_result.get("required_plex", 0)

    if is_valid:
        # Deposit now sufficient
        await session.commit()

        await callback.message.answer(
            f"✅ **Депозит подтверждён!**\n\n"
            f"💰 **Ваш депозит:** {total_deposit:.2f} USDT\n"
            f"📊 **Требуется PLEX в сутки:** {int(required_plex):,} PLEX\n\n"
            f"Теперь вы можете начать работу!",
            parse_mode="Markdown"
        )

        await callback.message.answer(
            "Нажмите кнопку:",
            reply_markup=auth_continue_keyboard()
        )
    else:
        # Still insufficient
        message = scan_result.get("validation_message")
        if message:
            await callback.message.answer(message, parse_mode="Markdown")

        await callback.message.answer(
            "После пополнения нажмите «Обновить депозит»:",
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

    # Import cmd_start from registration module
    from .registration import cmd_start

    # Mimic /start command
    msg = callback.message
    msg.text = "/start"
    msg.from_user = callback.from_user

    # Call cmd_start
    await cmd_start(msg, session, state, **data)
