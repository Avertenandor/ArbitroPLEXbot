# Menu Handlers Module

This directory contains the refactored menu handlers that were previously in a single 1424-line `menu.py` file.

## Refactoring Summary

**Original:** `menu.py` - 1424 lines (single file)  
**Refactored:** 15 modular files - 1726 total lines (avg ~115 lines per file)

All files are under the 300-line target, with the largest being `profile.py` at 202 lines.

## Module Organization

### Core Navigation
- **`core.py`** (148 lines)
  - Main menu display and navigation handlers
  - `show_main_menu()` function (exported for backward compatibility)
  - `handle_main_menu()` handler for menu button clicks

### Financial Menus
- **`balance.py`** (67 lines)
  - Balance display handlers
  - User balance information

- **`deposit_menu.py`** (97 lines)
  - Deposit menu with level statuses
  - Deposit validation and availability checking

- **`withdrawal_menu.py`** (74 lines)
  - Withdrawal menu handlers
  - Minimum withdrawal amount display

### User Information
- **`profile.py`** (202 lines)
  - Detailed user profile display
  - Report download functionality
  - ROI progress tracking

- **`wallet.py`** (64 lines)
  - Wallet information and history
  - Wallet address display

- **`deposits.py`** (110 lines)
  - Active deposits listing
  - ROI progress bars

### Referral System
- **`referral_menu.py`** (107 lines)
  - Referral menu with stats
  - Share link generation
  - Quick actions buttons

### Settings & Preferences
- **`settings.py`** (47 lines)
  - Main settings menu

- **`notifications.py`** (200 lines)
  - Notification preferences management
  - Toggle handlers for each notification type
  - Generic toggle function

- **`language.py`** (135 lines)
  - Language selection menu
  - Language change processing
  - Back button handler

### Information Pages
- **`info.py`** (184 lines)
  - Platform rules display
  - Ecosystem tools menu
  - Partner (DEXRabbit) information

### Actions
- **`update.py`** (111 lines)
  - Deposit scan and update
  - Blockchain validation

- **`registration.py`** (89 lines)
  - Registration process initiation from menu

### Integration
- **`__init__.py`** (91 lines)
  - Combines all routers into a single router
  - Exports `show_main_menu` for backward compatibility
  - Maintains all imports from `bot.handlers.menu`

## Backward Compatibility

The refactoring maintains 100% backward compatibility:

1. **Router export:** `from bot.handlers import menu` → `menu.router`
2. **Function export:** `from bot.handlers.menu import show_main_menu`

### Files that import from this module:
- `/home/user/ArbitroPLEXbot/bot/main.py` (imports `menu.router`)
- `/home/user/ArbitroPLEXbot/bot/handlers/contact_update.py` (imports `show_main_menu`)
- `/home/user/ArbitroPLEXbot/bot/handlers/admin/panel/main.py` (imports `show_main_menu`)

## Handler Registration Order

The routers are registered in the following order in `__init__.py`:

1. Core menu handlers (highest priority)
2. Balance and financial menus
3. User profile and data
4. Referral system
5. Settings and preferences
6. Information pages
7. Actions (update, registration)

## Key Features Preserved

✓ All handlers and callbacks preserved  
✓ All imports work correctly  
✓ FSM states maintained  
✓ Middleware integration preserved  
✓ Logging and error handling maintained  
✓ i18n support preserved  
✓ Blacklist checking maintained

## Benefits of Refactoring

1. **Maintainability:** Easier to find and modify specific handlers
2. **Readability:** Each file has a clear, focused purpose
3. **Testing:** Individual modules can be tested in isolation
4. **Collaboration:** Multiple developers can work on different modules
5. **Performance:** No performance impact - same runtime behavior
6. **Scalability:** Easy to add new menu items in appropriate modules

## File Size Comparison

| File | Lines | Purpose |
|------|-------|---------|
| `settings.py` | 47 | Smallest - simple menu display |
| `balance.py` | 67 | Balance information |
| `wallet.py` | 64 | Wallet display |
| `withdrawal_menu.py` | 74 | Withdrawal menu |
| `registration.py` | 89 | Registration flow |
| `__init__.py` | 91 | Module integration |
| `deposit_menu.py` | 97 | Deposit menu |
| `referral_menu.py` | 107 | Referral system |
| `deposits.py` | 110 | Deposits listing |
| `update.py` | 111 | Deposit scanning |
| `language.py` | 135 | Language settings |
| `core.py` | 148 | Main menu logic |
| `info.py` | 184 | Information pages |
| `notifications.py` | 200 | Notification settings |
| `profile.py` | 202 | Largest - comprehensive profile |

## Comments and Documentation

Each module includes:
- Module-level docstring explaining purpose
- Function docstrings with parameter descriptions
- Clear section comments where appropriate
- Type hints for all parameters
