"""
Output Wallet Setup Handlers.

Handles the setup of the output wallet (private key/seed phrase).
This wallet is used for making payments to users.
"""

import os
from typing import Any

from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from eth_account import Account
from mnemonic import Mnemonic

from app.config.settings import settings
from app.utils.encryption import get_encryption_service
from bot.utils.admin_utils import clear_state_preserve_admin_token

from .router import router
from .states import WalletSetupStates
from .utils import secure_zero_memory, update_env_variable


@router.message(F.text == "📤 Настроить кошелек для выдачи")
async def start_output_wallet_setup(message: Message, state: FSMContext, **data: Any):
    """Start output wallet setup."""
    # Only super admin is allowed to configure payout (hot) wallet
    if not message.from_user or message.from_user.id != settings.super_admin_telegram_id:
        return

    from bot.keyboards.reply import cancel_keyboard

    await state.set_state(WalletSetupStates.setting_output_key)
    await message.answer(
        "📤 **НАСТРОЙКА КОШЕЛЬКА ДЛЯ ВЫДАЧИ**\n\n"
        "⚠️ **ВНИМАНИЕ! КРИТИЧЕСКАЯ ОПЕРАЦИЯ**\n"
        "Этот кошелек используется для автоматических выплат.\n"
        "Системе требуется **Приватный ключ** или **Seed фраза**.\n\n"
        "📝 **Отправьте Приватный ключ (hex) ИЛИ Seed фразу:**\n"
        "• Сообщение будет удалено сразу после получения.\n"
        "• Ключ сохраняется локально в зашифрованном виде.",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


@router.message(WalletSetupStates.setting_output_key)
async def process_output_key(message: Message, state: FSMContext):
    """Process private key or seed phrase."""
    text = message.text.strip()

    if text == "❌ Отмена":
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    # Delete message immediately
    try:
        await message.delete()
    except Exception:
        pass

    private_key = None
    wallet_address = None

    # Try as Private Key
    account = None
    try:
        # Remove 0x prefix
        if text.startswith("0x"):
            pk_candidate = text[2:]
        else:
            pk_candidate = text

        if len(pk_candidate) == 64:
            account = Account.from_key(pk_candidate)
            private_key = pk_candidate
            wallet_address = account.address
    except Exception:
        pass
    finally:
        # SECURITY: Clear Account object immediately
        if account:
            del account

    # Try as Seed Phrase
    if not private_key:
        try:
            mnemo = Mnemonic("english")
            if mnemo.check(text):
                # SECURITY: Encrypt seed phrase before storing in FSM state
                encryption_service = get_encryption_service()
                if not encryption_service or not encryption_service.enabled:
                    await message.answer(
                        "❌ **КРИТИЧЕСКАЯ ОШИБКА**\n"
                        "Сервис шифрования недоступен. Невозможно безопасно сохранить seed-фразу.\n"
                        "Обратитесь к администратору системы.",
                        parse_mode="Markdown"
                    )
                    # SECURITY: Clear seed phrase from memory
                    secure_zero_memory(text)
                    return

                encrypted_seed = encryption_service.encrypt(text)
                if not encrypted_seed:
                    await message.answer(
                        "❌ **КРИТИЧЕСКАЯ ОШИБКА**\n"
                        "Не удалось зашифровать seed-фразу. Операция отменена.\n"
                        "Обратитесь к администратору системы.",
                        parse_mode="Markdown"
                    )
                    # SECURITY: Clear seed phrase from memory
                    secure_zero_memory(text)
                    return

                # Store encrypted seed phrase
                await state.update_data(temp_seed_phrase_encrypted=encrypted_seed)

                # SECURITY: Clear plaintext seed from memory
                secure_zero_memory(text)

                from bot.keyboards.reply import cancel_keyboard
                await state.set_state(WalletSetupStates.setting_derivation_index)
                await message.answer(
                    "🌱 **Обнаружена Seed-фраза**\n\n"
                    "Для HD-кошельков (Trust Wallet, Metamask, Ledger) можно выбрать адрес.\n"
                    "Путь деривации: `m/44'/60'/0'/0/{index}`\n\n"
                    "🔢 **Введите индекс адреса (обычно 0):**",
                    parse_mode="Markdown",
                    reply_markup=cancel_keyboard(),
                )
                return
        except Exception:
            pass

    if not private_key or not wallet_address:
        await message.answer(
            "❌ **Невалидный ключ или seed фраза.**\n"
            "Попробуйте еще раз или нажмите Отмена.",
            parse_mode="Markdown",
        )
        # SECURITY: Clear any sensitive data
        secure_zero_memory(text)
        return

    # SECURITY: Encrypt private key before storing in FSM state
    encryption_service = get_encryption_service()
    if not encryption_service or not encryption_service.enabled:
        await message.answer(
            "❌ **КРИТИЧЕСКАЯ ОШИБКА**\n"
            "Сервис шифрования недоступен. Невозможно безопасно сохранить приватный ключ.\n"
            "Обратитесь к администратору системы.",
            parse_mode="Markdown"
        )
        # SECURITY: Clear sensitive data
        secure_zero_memory(private_key)
        secure_zero_memory(text)
        return

    encrypted_key = encryption_service.encrypt(private_key)
    if not encrypted_key:
        await message.answer(
            "❌ **КРИТИЧЕСКАЯ ОШИБКА**\n"
            "Не удалось зашифровать приватный ключ. Операция отменена.\n"
            "Обратитесь к администратору системы.",
            parse_mode="Markdown"
        )
        # SECURITY: Clear sensitive data
        secure_zero_memory(private_key)
        secure_zero_memory(text)
        return

    # Save encrypted key to state (Private Key flow)
    await state.update_data(
        new_private_key_encrypted=encrypted_key,
        new_output_address=wallet_address
    )

    # SECURITY: Clear plaintext key from memory
    secure_zero_memory(private_key)
    secure_zero_memory(text)

    from bot.keyboards.reply import confirmation_keyboard

    await state.set_state(WalletSetupStates.confirming_output)
    await message.answer(
        f"📤 **Подтверждение ВЫХОДНОГО кошелька**\n\n"
        f"Адрес: `{wallet_address}`\n\n"
        "✅ Ключ валиден.\n"
        "✅ Этот кошелек будет использоваться для выплат.\n"
        "⚠️ Убедитесь, что на этом кошельке есть BNB для газа и USDT для выплат.\n\n"
        "Подтвердить сохранение?",
        parse_mode="Markdown",
        reply_markup=confirmation_keyboard(),
    )


@router.message(WalletSetupStates.setting_derivation_index)
async def process_derivation_index(message: Message, state: FSMContext):
    """Process derivation index for Seed Phrase."""
    text = message.text.strip()

    if text == "❌ Отмена":
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    try:
        index = int(text)
        if index < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число (например, 0):")
        return

    data = await state.get_data()
    encrypted_seed = data.get("temp_seed_phrase_encrypted")

    if not encrypted_seed:
        await message.answer("❌ Ошибка: Seed-фраза потеряна. Начните заново.")
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    # SECURITY: Decrypt seed phrase only for derivation
    encryption_service = get_encryption_service()
    if not encryption_service or not encryption_service.enabled:
        await message.answer(
            "❌ **КРИТИЧЕСКАЯ ОШИБКА**\n"
            "Сервис шифрования недоступен. Невозможно продолжить.\n"
            "Обратитесь к администратору системы.",
            parse_mode="Markdown"
        )
        await state.update_data(temp_seed_phrase_encrypted=None)
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    seed_phrase = encryption_service.decrypt(encrypted_seed)
    if not seed_phrase:
        await message.answer("❌ Ошибка: Не удалось расшифровать seed-фразу. Начните заново.")
        await state.update_data(temp_seed_phrase_encrypted=None)
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    account = None
    private_key = None
    try:
        # Enable HD Wallet features safely
        if hasattr(Account, "enable_unaudited_hdwallet_features"):
            try:
                Account.enable_unaudited_hdwallet_features()
            except Exception:
                pass

        # Derive account
        # Standard Ethereum/BSC path: m/44'/60'/0'/0/{index}
        path = f"m/44'/60'/0'/0/{index}"
        account = Account.from_mnemonic(seed_phrase, account_path=path)

        private_key = account.key.hex()[2:]  # remove 0x
        wallet_address = account.address

        # SECURITY: Encrypt private key before storing in FSM state
        if not encryption_service or not encryption_service.enabled:
            await message.answer(
                "❌ **КРИТИЧЕСКАЯ ОШИБКА**\n"
                "Сервис шифрования недоступен. Невозможно безопасно сохранить ключ.",
                parse_mode="Markdown"
            )
            from .menu import handle_wallet_menu
            await handle_wallet_menu(message, state)
            return

        encrypted_key = encryption_service.encrypt(private_key)
        if not encrypted_key:
            await message.answer("❌ Ошибка шифрования ключа. Начните заново.")
            from .menu import handle_wallet_menu
            await handle_wallet_menu(message, state)
            return

        # Save encrypted key to state
        await state.update_data(
            new_private_key_encrypted=encrypted_key,
            new_output_address=wallet_address,
            temp_seed_phrase_encrypted=None  # Clear encrypted seed
        )

        from bot.keyboards.reply import confirmation_keyboard

        await state.set_state(WalletSetupStates.confirming_output)
        await message.answer(
            f"📤 **Подтверждение ВЫХОДНОГО кошелька**\n\n"
            f"🌱 Seed-фраза (Index: {index})\n"
            f"Адрес: `{wallet_address}`\n\n"
            "✅ Ключ успешно деривирован.\n"
            "✅ Этот кошелек будет использоваться для выплат.\n\n"
            "Подтвердить сохранение?",
            parse_mode="Markdown",
            reply_markup=confirmation_keyboard(),
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка деривации кошелька: {e}")
        # SECURITY: Clear encrypted seed from state on error
        await state.update_data(temp_seed_phrase_encrypted=None)
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
    finally:
        # SECURITY: Clear all sensitive data from memory
        if seed_phrase:
            secure_zero_memory(seed_phrase)
            del seed_phrase
        if private_key:
            secure_zero_memory(private_key)
            del private_key
        if account:
            del account


@router.message(WalletSetupStates.confirming_output)
async def confirm_output_wallet(message: Message, state: FSMContext):
    """Confirm and save output wallet."""
    if message.text != "✅ Да":
        # SECURITY: Clear all encrypted data from state on cancel
        await state.update_data(
            temp_seed_phrase_encrypted=None,
            new_private_key_encrypted=None,
            new_output_address=None
        )
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    data = await state.get_data()
    encrypted_key = data.get("new_private_key_encrypted")
    address = data.get("new_output_address")

    if not encrypted_key or not address:
        await message.answer("❌ Ошибка данных.")
        await state.update_data(
            temp_seed_phrase_encrypted=None,
            new_private_key_encrypted=None,
            new_output_address=None
        )
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    # SECURITY: Decrypt key only for saving to .env
    encryption_service = get_encryption_service()
    if not encryption_service or not encryption_service.enabled:
        await message.answer(
            "❌ **КРИТИЧЕСКАЯ ОШИБКА**\n"
            "Сервис шифрования недоступен. Невозможно сохранить ключ.\n"
            "Обратитесь к администратору системы.",
            parse_mode="Markdown"
        )
        await state.update_data(
            temp_seed_phrase_encrypted=None,
            new_private_key_encrypted=None,
            new_output_address=None
        )
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    private_key = encryption_service.decrypt(encrypted_key)
    if not private_key:
        await message.answer("❌ Ошибка расшифровки ключа.")
        await state.update_data(
            temp_seed_phrase_encrypted=None,
            new_private_key_encrypted=None,
            new_output_address=None
        )
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
        return

    try:
        # Update .env (private_key will be encrypted automatically in update_env_variable)
        update_env_variable("wallet_private_key", private_key)
        update_env_variable("wallet_address", address)

        # SECURITY: Clear all sensitive data from FSM state after saving
        # This ensures no private keys or seed phrases remain in memory/FSM storage
        await state.update_data(
            temp_seed_phrase_encrypted=None,
            new_private_key_encrypted=None,
            new_output_address=None
        )

        # Force restart via exit
        await message.answer(
            "✅ **Кошелек для выдачи сохранен!**\n\n"
            "🔄 Бот перезапускается для применения нового ключа...",
            parse_mode="Markdown",
        )
        await clear_state_preserve_admin_token(state)
        os._exit(0)

    except Exception as e:
        # SECURITY: Clear sensitive data even on error
        await state.update_data(
            temp_seed_phrase_encrypted=None,
            new_private_key_encrypted=None,
            new_output_address=None
        )
        await message.answer(f"❌ Ошибка при сохранении: {e}")
        from .menu import handle_wallet_menu
        await handle_wallet_menu(message, state)
    finally:
        # SECURITY: Clear plaintext key from memory
        if private_key:
            secure_zero_memory(private_key)
            del private_key
