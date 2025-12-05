# Admin Keyboards Module

This directory contains the refactored admin keyboard components, organized by functionality.

## Structure

The original `admin_keyboards.py` file (1175 lines) has been refactored into smaller, well-organized modules:

```
bot/keyboards/admin/
├── __init__.py (162 lines) - Re-exports all functions for convenient access
├── main_keyboards.py (92 lines) - Main admin panel keyboard
├── user_keyboards.py (121 lines) - User management keyboards
├── withdrawal_keyboards.py (181 lines) - Withdrawal management keyboards
├── wallet_keyboards.py (33 lines) - Wallet management keyboards
├── broadcast_keyboards.py (65 lines) - Broadcast message keyboards
├── support_keyboards.py (104 lines) - Support ticket keyboards
├── blacklist_keyboards.py (33 lines) - Blacklist management keyboards
├── admin_management_keyboards.py (36 lines) - Admin management keyboards
├── deposit_keyboards.py (214 lines) - Deposit and ROI management keyboards
├── financial_keyboards.py (271 lines) - Financial reporting keyboards
└── inquiry_keyboards.py (101 lines) - User inquiry keyboards
```

## Modules Overview

### main_keyboards.py
Core admin panel keyboard with role-based access control.

**Functions:**
- `admin_keyboard()` - Main admin panel with dynamic buttons based on roles
- `get_admin_keyboard_from_data()` - Helper to get keyboard from handler data

### user_keyboards.py
User management keyboards for viewing, searching, and managing users.

**Functions:**
- `admin_users_keyboard()` - User management menu
- `admin_user_list_keyboard()` - Paginated user list
- `admin_user_profile_keyboard()` - User profile actions

### withdrawal_keyboards.py
Withdrawal management keyboards for approving/rejecting withdrawals.

**Functions:**
- `admin_withdrawals_keyboard()` - Withdrawal management menu
- `withdrawal_list_keyboard()` - Paginated withdrawal list
- `admin_withdrawal_detail_keyboard()` - Withdrawal detail view
- `withdrawal_confirm_keyboard()` - Confirmation for approve/reject
- `admin_withdrawal_settings_keyboard()` - Withdrawal settings
- `admin_withdrawal_history_pagination_keyboard()` - Paginated withdrawal history

### wallet_keyboards.py
Wallet management keyboards for configuring crypto wallets.

**Functions:**
- `admin_wallet_keyboard()` - Wallet management menu

### broadcast_keyboards.py
Keyboards for creating and sending mass messages to users.

**Functions:**
- `admin_broadcast_button_choice_keyboard()` - Choose to add button or not
- `admin_broadcast_cancel_keyboard()` - Cancel broadcast
- `admin_broadcast_keyboard()` - Broadcast composition

### support_keyboards.py
Support ticket management keyboards.

**Functions:**
- `admin_support_keyboard()` - Support ticket menu
- `admin_support_ticket_keyboard()` - Ticket detail view
- `admin_ticket_list_keyboard()` - Paginated ticket list

### blacklist_keyboards.py
Blacklist management keyboards.

**Functions:**
- `admin_blacklist_keyboard()` - Blacklist management menu

### admin_management_keyboards.py
Admin management keyboards (super admin only).

**Functions:**
- `admin_management_keyboard()` - Admin management menu

### deposit_keyboards.py
Deposit level and ROI corridor management keyboards.

**Functions:**
- `admin_deposit_settings_keyboard()` - Deposit settings menu
- `admin_deposit_management_keyboard()` - Main deposit management menu
- `admin_deposit_levels_keyboard()` - Level selection
- `admin_deposit_level_actions_keyboard()` - Actions for a specific level
- `admin_roi_corridor_menu_keyboard()` - ROI corridor management menu
- `admin_roi_level_select_keyboard()` - Level selection for ROI
- `admin_roi_mode_select_keyboard()` - ROI mode selection
- `admin_roi_applies_to_keyboard()` - Choose session scope
- `admin_roi_confirmation_keyboard()` - Confirm ROI changes

### financial_keyboards.py
Financial reporting and finpass recovery keyboards.

**Functions:**
- `admin_finpass_request_list_keyboard()` - Paginated finpass recovery requests
- `admin_finpass_request_actions_keyboard()` - Actions for a request
- `admin_financial_list_keyboard()` - Paginated financial user list
- `admin_user_financial_keyboard()` - Financial user actions
- `admin_back_keyboard()` - Simple back navigation
- `admin_user_financial_detail_keyboard()` - Financial detail view
- `admin_deposits_list_keyboard()` - Paginated deposits
- `admin_withdrawals_list_keyboard()` - Paginated withdrawals
- `admin_wallet_history_keyboard()` - Wallet history view

### inquiry_keyboards.py
User inquiry (questions to sponsor) management keyboards.

**Functions:**
- `admin_inquiry_menu_keyboard()` - Inquiry management menu
- `admin_inquiry_list_keyboard()` - Paginated inquiry list
- `admin_inquiry_detail_keyboard()` - Inquiry detail view
- `admin_inquiry_response_keyboard()` - Response composition

## Usage

### Import from package (recommended)
```python
from bot.keyboards.admin import admin_keyboard, admin_users_keyboard
from bot.keyboards.admin.deposit_keyboards import admin_roi_corridor_menu_keyboard
```

### Import from backward compatibility wrapper (still works)
```python
from bot.keyboards.admin_keyboards import admin_keyboard, admin_users_keyboard
```

## Backward Compatibility

The original `bot/keyboards/admin_keyboards.py` file has been converted to a backward compatibility wrapper that re-exports all functions from this package. All existing code will continue to work without modification.

## Benefits

1. **Smaller files**: Each file is under 300 lines (largest: 271 lines)
2. **Logical organization**: Related keyboards are grouped together
3. **Easier maintenance**: Find keyboards by functionality
4. **Better documentation**: Each module has clear docstrings
5. **No functionality loss**: All 42 keyboard functions preserved
6. **Zero breaking changes**: Existing imports still work
