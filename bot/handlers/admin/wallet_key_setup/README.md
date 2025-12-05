# Wallet Key Setup Module

This module handles secure wallet management with separate workflows for input and output wallets.

## Structure

```
wallet_key_setup/
├── __init__.py          # Module exports and public API (69 lines)
├── router.py            # Router definition (10 lines)
├── states.py            # FSM states (18 lines)
├── menu.py              # Menu navigation (53 lines)
├── input_wallet.py      # Input wallet setup (120 lines)
├── output_wallet.py     # Output wallet setup (419 lines)
└── utils.py             # Utility functions (94 lines)
```

## Features

### Input Wallet Setup (`input_wallet.py`)
- Configures wallet address for receiving user deposits
- Address-only (no private key required)
- Validates Ethereum/BSC address format
- Stores address in .env file
- System monitors incoming transactions

### Output Wallet Setup (`output_wallet.py`)
- Configures wallet for automated payments
- Supports private key or seed phrase input
- HD wallet derivation support (BIP-44)
- Automatic message deletion for security
- Encrypted storage in .env file
- Automatic bot restart after setup

### Security Features (`utils.py`)
- **Secure Memory Wiping**: Best-effort clearing of sensitive data from memory
- **Automatic Encryption**: All private keys encrypted before storage
- **No Plaintext Fallback**: Fails safely if encryption unavailable
- **Atomic Updates**: Environment variable updates are atomic

## Wallet Types

### Input Wallet (Deposit)
- **Purpose**: Receive user deposits
- **Required**: Address only
- **Security**: No private key needed
- **Operations**: Read-only monitoring

### Output Wallet (Payment)
- **Purpose**: Send payments to users
- **Required**: Private key or seed phrase
- **Security**: Encrypted storage, memory wiping
- **Operations**: Sign and send transactions

## FSM States

```python
class WalletSetupStates:
    setting_input_wallet       # Entering input wallet address
    confirming_input           # Confirming input wallet
    setting_output_key         # Entering private key/seed
    setting_derivation_index   # HD wallet index selection
    confirming_output          # Confirming output wallet
```

## HD Wallet Support

The module supports HD wallet derivation using BIP-44 standard:
- Path: `m/44'/60'/0'/0/{index}`
- Compatible with Trust Wallet, Metamask, Ledger
- User can select any derivation index (usually 0)

## Usage

```python
# Import the router
from bot.handlers.admin.wallet_key_setup import router

# Import states
from bot.handlers.admin.wallet_key_setup import WalletSetupStates

# Import functions
from bot.handlers.admin.wallet_key_setup import handle_wallet_menu
from bot.handlers.admin.wallet_key_setup import start_input_wallet_setup
from bot.handlers.admin.wallet_key_setup import start_output_wallet_setup
```

## Security Notes

1. **Message Deletion**: Private keys/seeds are deleted from chat immediately
2. **FSM Encryption**: Sensitive data encrypted in FSM state storage
3. **Memory Clearing**: Sensitive variables wiped from memory after use
4. **No Logging**: Private keys never logged or printed
5. **Atomic Operations**: Environment updates are atomic
6. **Restart Required**: Bot restarts after output wallet setup to load new keys

## Dependencies

- aiogram: Bot framework
- eth_account: Ethereum account management
- eth_utils: Address validation
- mnemonic: BIP-39 mnemonic phrase validation
- app.utils.encryption: Encryption service

## Original File

This module was refactored from `/home/user/ArbitroPLEXbot/bot/handlers/admin/wallet_key_setup.py` (649 lines).
The original file is backed up as `wallet_key_setup.py.old`.
