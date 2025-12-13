"""
Financial password recovery handler.
Allows users to request recovery with admin approval.
"""
import re
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from loguru import logger
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.finpass_recovery_service import FinpassRecoveryService
from bot.keyboards.reply import main_menu_reply_keyboard
from bot.states.finpass_recovery import FinpassRecoveryStates

router = Router()

async def _start_finpass_recovery_flow(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """Common logic for starting financial password recovery."""
    from bot.keyboards.user.financial import finpass_recovery_type_keyboard
    recovery_service = FinpassRecoveryService(session)
    # Check if already has pending request
    pending = await recovery_service.get_pending_by_user(user.id)
    if pending:
        text = (
            "⚠️ **У вас уже есть активный запрос "
            "на восстановление пароля**\n\n"
            f"Статус: {pending.status}\n"
            f"Создан: {pending.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            "Дождитесь рассмотрения администратором."
        )
        is_admin = data.get("is_admin", False)
        from app.repositories.blacklist_repository import BlacklistRepository
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)

        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return
    # Check if has active recovery (approved but not verified)
    has_active = await recovery_service.has_active_recovery(user.id)
    if has_active:
        text = (
            "✅ **Ваш запрос одобрен!**\n\n"
            "Новый финансовый пароль был отправлен вам "
            "в личные сообщения.\n\n"
            "🔒 **Почему выплаты заблокированы?**\n"
            "Это защита: если злоумышленник "
            "запросил смену пароля, он не сможет вывести "
            "ваши средства без подтверждения.\n\n"
            "✅ **Как разблокировать:**\n"
            "Сделайте любой вывод с новым паролем — "
            "блокировка снимется автоматически.\n\n"
            "👉 Используйте '💸 Вывод' для проверки."
        )
        is_admin = data.get("is_admin", False)
        from app.repositories.blacklist_repository import BlacklistRepository
        blacklist_repo = BlacklistRepository(session)
        blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)

        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return
    # Show recovery type selection
    text = (
        "🔐 **Восстановление финансового пароля**\n\n"
        "⚠️ **Важно:**\n"
        "• Запрос рассматривается администратором\n"
        "• Выплаты заблокированы до первого вывода "
        "с новым паролем\n\n"
        "❓ **Что вам нужно восстановить?**\n\n"
        "🔑 **Только пароль** — если забыли пароль, "
        "но кошелёк в порядке\n\n"
        "💼 **Пароль + Новый кошелёк** — "
        "если потеряли доступ к кошельку\n"
        "(смена SIM, утеря телефона, взлом и т.д.)"
    )
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=finpass_recovery_type_keyboard(),
    )
    await state.set_state(FinpassRecoveryStates.choosing_recovery_type)

@router.message(F.text == "🔑 Восстановить финпароль")
async def start_finpass_recovery_from_button(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """Start financial password recovery from menu button."""
    await _start_finpass_recovery_flow(message, session, user, state, **data)

@router.message(FinpassRecoveryStates.choosing_recovery_type)
async def process_recovery_type_choice(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process recovery type selection."""
    from bot.keyboards.reply import (
        cancel_keyboard, finpass_recovery_keyboard
    )
    from bot.utils.menu_buttons import is_menu_button
    is_admin = data.get("is_admin", False)
    if is_menu_button(message.text) or message.text == "❌ Отмена":
        await state.clear()
        blacklist_entry = None
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        except OperationalError as error:
            logger.error(f"DB error checking blacklist: {error}")
        await message.answer(
            "❌ Восстановление отменено.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return
    if message.text == "🔑 Только пароль":
        # Standard password-only recovery
        await state.update_data(include_wallet_change=False, new_wallet=None)
        await message.answer(
            "📝 Укажите причину восстановления пароля:\n\n"
            "(Минимум 10 символов)",
            reply_markup=finpass_recovery_keyboard(),
        )
        await state.set_state(FinpassRecoveryStates.waiting_for_reason)
    elif message.text == "💼 Пароль + Новый кошелёк":
        # Password + wallet change
        await state.update_data(include_wallet_change=True)
        await message.answer(
            "💼 **Смена кошелька + Восстановление пароля**\n\n"
            "Введите адрес вашего **НОВОГО** BEP-20 кошелька:\n\n"
            "⚠️ **КРИТИЧНО:**\n"
            "• Указывайте только *ЛИЧНЫЙ* кошелёк\n"
            "  (Trust Wallet, MetaMask, SafePal)\n"
            "• 🚫 *НЕ указывайте* адрес биржи!\n\n"
            "Формат: `0x...` (42 символа)",
            parse_mode="Markdown",
            reply_markup=cancel_keyboard(),
        )
        await state.set_state(FinpassRecoveryStates.waiting_for_new_wallet)
    else:
        await message.answer(
            "❌ Пожалуйста, выберите один из вариантов:\n"
            "• 🔑 Только пароль\n"
            "• 💼 Пароль + Новый кошелёк"
        )


@router.message(FinpassRecoveryStates.waiting_for_new_wallet)
async def process_new_wallet_for_recovery(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process new wallet address for recovery with wallet change."""
    from bot.keyboards.reply import (
        cancel_keyboard, finpass_recovery_keyboard
    )
    from bot.utils.menu_buttons import is_menu_button
    is_admin = data.get("is_admin", False)
    if is_menu_button(message.text) or message.text == "❌ Отмена":
        await state.clear()
        blacklist_entry = None
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        except OperationalError as error:
            logger.error(f"DB error checking blacklist: {error}")
        await message.answer(
            "❌ Восстановление отменено.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return
    new_wallet = message.text.strip()
    # Validate BEP-20 format
    if not re.match(r"^0x[a-fA-F0-9]{40}$", new_wallet):
        await message.answer(
            "❌ Неверный формат адреса кошелька.\n"
            "Адрес должен начинаться с 0x "
            "и содержать 42 символа.\n\n"
            "Попробуйте ещё раз:",
            reply_markup=cancel_keyboard(),
        )
        return
    # Check if wallet is in blacklist
    from app.repositories.blacklist_repository import BlacklistRepository
    blacklist_repo = BlacklistRepository(session)
    blacklisted = await blacklist_repo.find_by_wallet(new_wallet)
    if blacklisted:
        await message.answer(
            "❌ Этот адрес кошелька заблокирован в системе.\n"
            "Укажите другой адрес:",
            reply_markup=cancel_keyboard(),
        )
        return
    # Check if wallet is already used
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(session)
    existing = await user_repo.get_by_wallet_address(new_wallet)
    if existing and existing.id != user.id:
        await message.answer(
            "❌ Этот кошелёк уже используется "
            "другим пользователем.\n"
            "Укажите другой адрес:",
            reply_markup=cancel_keyboard(),
        )
        return
    # Save new wallet and proceed to reason
    await state.update_data(new_wallet=new_wallet)
    await message.answer(
        f"✅ Новый кошелёк принят:\n`{new_wallet}`\n\n"
        "📝 Теперь укажите причину восстановления:\n"
        "(Опишите почему потеряли доступ "
        "к старому кошельку)",
        parse_mode="Markdown",
        reply_markup=finpass_recovery_keyboard(),
    )
    await state.set_state(FinpassRecoveryStates.waiting_for_reason)


@router.message(FinpassRecoveryStates.waiting_for_reason)
async def process_recovery_reason(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process recovery reason - show confirmation before creating request."""
    from bot.keyboards.reply import finpass_recovery_confirm_keyboard
    from bot.utils.menu_buttons import is_menu_button
    is_admin = data.get("is_admin", False)
    if is_menu_button(message.text) or message.text == "❌ Отмена":
        await state.clear()
        blacklist_entry = None
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        except OperationalError as error:
            logger.error(f"DB error checking blacklist: {error}")
            # For cancel operation, we can fallback to None
            pass
        await message.answer(
            "❌ Восстановление пароля отменено.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return
    reason = message.text.strip()
    if len(reason) < 10:
        await message.answer(
            "❌ Причина слишком короткая!\n\n"
            "Пожалуйста, опишите ситуацию подробнее "
            "(минимум 10 символов)."
        )
        return
    # Save reason to state and ask for confirmation
    await state.update_data(reason=reason)
    await state.set_state(FinpassRecoveryStates.waiting_for_confirmation)
    # Get state data to check if wallet change requested
    state_data = await state.get_data()
    include_wallet = state_data.get("include_wallet_change", False)
    new_wallet = state_data.get("new_wallet")
    if include_wallet and new_wallet:
        text = (
            "📋 **Проверьте вашу заявку:**\n\n"
            f"💼 **Новый кошелёк:**\n`{new_wallet}`\n\n"
            f"📝 **Причина:**\n{reason}\n\n"
            "⚠️ **Напоминание:**\n"
            "• После одобрения ваш кошелёк будет изменён\n"
            "• Выплаты блокируются до первого вывода\n"
            "• Администратор рассмотрит запрос вручную\n\n"
            "Нажмите **✅ Отправить заявку** "
            "для подтверждения:"
        )
    else:
        text = (
            "📋 **Проверьте вашу заявку:**\n\n"
            f"📝 **Причина:**\n{reason}\n\n"
            "⚠️ **Напоминание:**\n"
            "• После отправки заявки выплаты блокируются\n"
            "• Администратор рассмотрит запрос вручную\n"
            "• Разблокировка — при первом выводе "
            "с новым паролем\n\n"
            "Нажмите **✅ Отправить заявку** "
            "для подтверждения:"
        )
    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=finpass_recovery_confirm_keyboard(),
    )


@router.message(FinpassRecoveryStates.waiting_for_confirmation)
async def process_recovery_confirmation(
    message: Message,
    session: AsyncSession,
    user: User,
    state: FSMContext,
    **data: Any,
) -> None:
    """Process confirmation and create the recovery request."""
    from bot.utils.menu_buttons import is_menu_button
    is_admin = data.get("is_admin", False)
    # Handle cancel button FIRST to avoid getting stuck
    if message.text == "❌ Отменить" or message.text == "❌ Отмена":
        await state.clear()
        bl_entry = None
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        except OperationalError as error:
            logger.error(f"DB error checking blacklist: {error}")
            # For cancel operation, we can fallback to None
            pass
        await message.answer(
            "Заявка отменена.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=bl_entry, is_admin=is_admin
            ),
        )
        return
    # Handle menu buttons
    if is_menu_button(message.text):
        await state.clear()
        bl_entry = None
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        except OperationalError as error:
            logger.error(f"DB error checking blacklist: {error}")
            # For menu navigation, we can fallback to None
            pass
        await message.answer(
            "❌ Восстановление пароля отменено.",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        return
    # Handle confirm
    if message.text != "✅ Отправить заявку":
        await message.answer(
            "❌ Пожалуйста, используйте кнопки ниже:\n"
            "• **✅ Отправить заявку** — подтвердить\n"
            "• **❌ Отменить** — отменить",
            parse_mode="Markdown",
        )
        return
    # Get reason from state
    state_data = await state.get_data()
    reason = state_data.get("reason", "")
    new_wallet = state_data.get("new_wallet")
    if not reason:
        await state.clear()
        await message.answer(
            "❌ Ошибка: причина не найдена. "
            "Попробуйте заново.",
            reply_markup=main_menu_reply_keyboard(user=user, is_admin=is_admin),
        )
        return
    # Create recovery request
    recovery_service = FinpassRecoveryService(session)
    try:
        request = await recovery_service.create_recovery_request(
            user_id=user.id,
            reason=reason,
            new_wallet_address=new_wallet,
        )
        await session.commit()
        # Get bl_entry for keyboard
        bl_entry = None
        try:
            from app.repositories.blacklist_repository import BlacklistRepository
            blacklist_repo = BlacklistRepository(session)
            blacklist_entry = await blacklist_repo.find_by_telegram_id(user.telegram_id)
        except OperationalError as error:
            logger.error(f"DB error checking blacklist: {error}")
        await message.answer(
            "✅ **Заявка на восстановление отправлена!**\n\n"
            f"🔢 Номер заявки: **#{request.id}**\n\n"
            "📬 Что дальше:\n"
            "• Администратор рассмотрит вашу заявку\n"
            "• Вы получите уведомление с новым паролем\n"
            "• После получения — сделайте вывод "
            "для разблокировки\n\n"
            "⏱ Обычно рассмотрение занимает до 24 часов.",
            parse_mode="Markdown",
            reply_markup=main_menu_reply_keyboard(
                user=user, blacklist_entry=blacklist_entry, is_admin=is_admin
            ),
        )
        # Notify admins
        from app.config.settings import settings
        admin_ids = settings.get_admin_ids()
        if admin_ids:
            from bot.utils.notifications import notify_admins
            try:
                username_or_id = user.username or user.telegram_id
                wallet_info = ""
                if new_wallet:
                    wallet_info = (
                        f"\n💼 ЗАПРОШЕНА СМЕНА КОШЕЛЬКА!\n"
                        f"Новый: {new_wallet[:20]}..."
                    )
                await notify_admins(
                    message.bot,
                    admin_ids,
                    f"🔐 **Новый запрос на восстановление**\n\n"
                    f"👤 Пользователь: {username_or_id}\n"
                    f"🔢 ID: #{request.id}\n"
                    f"📝 Причина: {reason[:100]}"
                    f"{'...' if len(reason) > 100 else ''}"
                    f"{wallet_info}\n\n"
                    f"👉 Админ-панель → "
                    f"🔑 Восстановление пароля",
                )
            except Exception as error:
                logger.error(f"Failed to notify admins: {error}")
    except ValueError as error:
        await message.answer(
            f"❌ Ошибка: {error}\n\n"
            "Попробуйте позже или обратитесь в поддержку.",
            reply_markup=main_menu_reply_keyboard(user=user, is_admin=is_admin),
        )
    await state.clear()
