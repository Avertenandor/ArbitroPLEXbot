"""
Wallet Key Setup Module.

This module handles secure wallet management with separate workflows for:
1. Input Wallet (Address only) - Users deposit here
2. Output Wallet (Private Key/Seed) - System pays from here

Module Structure:
- router.py: Main router for all wallet setup handlers
- states.py: FSM states for wallet setup flow
- menu.py: Menu navigation handlers
- input_wallet.py: Input wallet setup (address only)
- output_wallet.py: Output wallet setup (private key/seed phrase)
- utils.py: Utility functions (secure memory, env updates)

Security Features:
- Automatic encryption of private keys
- Secure memory wiping for sensitive data
- Atomic environment variable updates
- HD wallet derivation support

Usage:
    from bot.handlers.admin.wallet_key_setup import router
    from bot.handlers.admin.wallet_key_setup import WalletSetupStates
    from bot.handlers.admin.wallet_key_setup import handle_wallet_menu

All handlers are automatically registered on the router.
"""

# Import router first
from .router import router

# Import states
from .states import WalletSetupStates

# Import all handlers to register them on the router
from . import menu
from . import input_wallet
from . import output_wallet
from . import utils

# Re-export main functions for backward compatibility
from .menu import handle_wallet_menu, handle_wallet_status, handle_back_to_admin_panel
from .input_wallet import start_input_wallet_setup, process_input_wallet, confirm_input_wallet
from .output_wallet import (
    start_output_wallet_setup,
    process_output_key,
    process_derivation_index,
    confirm_output_wallet,
)
from .utils import secure_zero_memory, update_env_variable

# Public API
__all__ = [
    "router",
    "WalletSetupStates",
    "handle_wallet_menu",
    "handle_wallet_status",
    "handle_back_to_admin_panel",
    "start_input_wallet_setup",
    "process_input_wallet",
    "confirm_input_wallet",
    "start_output_wallet_setup",
    "process_output_key",
    "process_derivation_index",
    "confirm_output_wallet",
    "secure_zero_memory",
    "update_env_variable",
]
