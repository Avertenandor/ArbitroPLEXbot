"""
Input Wallet Setup Handlers.

Handles the setup of the input wallet (address only).
This wallet is used for receiving deposits from users.
"""

from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from eth_utils import is_address, to_checksum_address

from app.config.settings import settings

from .router import router
from .states import WalletSetupStates
from .utils import update_env_variable


@router.message(F.text == "📥 Настроить кошелек для входа")
async def start_input_wallet_setup(message: Message, state: FSMContext, **data: Any):
    """Start input wallet setup."""
    # Only super admin is allowed to change system input wallet
    if not message.from_user or message.from_user.id != settings.super_admin_telegram_id:
        return

    from bot.keyboards.reply import cancel_keyboard

    await state.set_state(WalletSetupStates.setting_input_wallet)
    await message.answer(
        "📥 **НАСТРОЙКА КОШЕЛЬКА ДЛЯ ВХОДА**\n\n"
        "Этот кошелек будет показываться пользователям для пополнения.\n"
        "Система будет **только мониторить** поступления на этот адрес.\n\n"
        "📝 **Введите адрес кошелька (BEP-20/BSC):**\n"
        "Формат: `0x...` (42 символа)",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(WalletSetupStates.setting_input_wallet)
async def process_input_wallet(message: Message, state: FSMContext):
    """Validate input wallet address."""
    address = message.text.strip()

    if message.text == "❌ Отмена":
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    if not is_address(address):
        await message.answer(
            "❌ Некорректный формат адреса.\n"
            "Адрес должен начинаться с 0x и содержать 42 символа.\n"
            "Попробуйте еще раз:",
        )
        return

    try:
        checksum_address = to_checksum_address(address)
    except Exception:
        await message.answer("❌ Ошибка валидации контрольной суммы адреса.")
        return

    # Save to state
    await state.update_data(new_input_wallet=checksum_address)

    from bot.keyboards.reply import confirmation_keyboard

    await state.set_state(WalletSetupStates.confirming_input)
    await message.answer(
        f"📥 **Подтверждение ВХОДНОГО кошелька**\n\n"
        f"Адрес: `{checksum_address}`\n\n"
        "✅ Пользователи будут отправлять средства на этот адрес.\n"
        "✅ Бот будет отслеживать входящие транзакции.\n"
        "❌ Бот НЕ сможет выводить средства с этого адреса (нет приватного ключа).\n\n"
        "Подтвердить сохранение?",
        parse_mode="Markdown",
        reply_markup=confirmation_keyboard(),
    )


@router.message(WalletSetupStates.confirming_input)
async def confirm_input_wallet(message: Message, state: FSMContext):
    """Confirm and save input wallet."""
    if message.text != "✅ Да":
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    data = await state.get_data()
    new_address = data.get("new_input_wallet")

    if not new_address:
        await message.answer("❌ Ошибка данных. Начните заново.")
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    try:
        # Update .env
        update_env_variable("system_wallet_address", new_address)

        # Update settings in memory (hacky but works until restart)
        settings.system_wallet_address = new_address

        await message.answer(
            "✅ **Кошелек для входа успешно обновлен!**\n\n"
            "Для полного применения изменений рекомендуется перезапуск.",
            parse_mode="Markdown",
        )
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)

    except Exception as e:
        await message.answer(f"❌ Ошибка при сохранении: {e}")
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
