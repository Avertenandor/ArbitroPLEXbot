"""
Master key management module.

Allows super admin to get and regenerate master key.
Similar to @BotFather token management.

FULL FUNCTIONALITY (with REPLY keyboards):
- Show master key menu with current status
- Generate new master key (with confirmation)
- Show current key status (hashed, cannot be recovered)
- Cancel operation
- Security logging for all actions
- Role-based access control
"""

from aiogram import F, Router
from aiogram.filters import Command

from bot.states.admin import AdminMasterKeyStates

from .handlers import (
    back_to_main_menu,
    btn_my_master_key,
    cmd_masterkey,
    confirm_regenerate_master_key,
    process_confirmation,
    show_master_key_menu,
    show_master_key_status,
)
from .messages import (
    build_confirmation_message,
    build_key_already_exists_message,
    build_key_copy_message,
    build_key_status_message,
    build_master_key_menu_message,
    build_new_key_message,
    build_quick_key_created_message,
    build_quick_key_regenerated_message,
    build_usage_instructions,
)
from .operations import regenerate_master_key
from .security import SUPER_ADMIN_TELEGRAM_ID, is_super_admin

# Create router
router = Router()

# Register command handlers
router.message.register(cmd_masterkey, Command("masterkey"))

# Register button handlers
router.message.register(btn_my_master_key, F.text == "🔑 Мой мастер-ключ")
router.message.register(show_master_key_menu, F.text == "🔑 Управление мастер-ключом")
router.message.register(show_master_key_status, F.text == "🔍 Показать текущий ключ")
router.message.register(confirm_regenerate_master_key, F.text == "🔄 Сгенерировать новый ключ")
router.message.register(back_to_main_menu, F.text == "◀️ Главное меню")

# Register state handler
router.message.register(process_confirmation, AdminMasterKeyStates.awaiting_confirmation)

# Public exports for backward compatibility
__all__ = [
    # Router
    "router",
    # Security
    "SUPER_ADMIN_TELEGRAM_ID",
    "is_super_admin",
    # Handlers
    "cmd_masterkey",
    "btn_my_master_key",
    "show_master_key_menu",
    "show_master_key_status",
    "confirm_regenerate_master_key",
    "process_confirmation",
    "back_to_main_menu",
    # Operations
    "regenerate_master_key",
    # Messages
    "build_master_key_menu_message",
    "build_key_status_message",
    "build_confirmation_message",
    "build_new_key_message",
    "build_key_copy_message",
    "build_usage_instructions",
    "build_key_already_exists_message",
    "build_quick_key_created_message",
    "build_quick_key_regenerated_message",
]
