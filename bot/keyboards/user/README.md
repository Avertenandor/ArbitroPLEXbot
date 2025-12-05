# User Keyboards Module Structure

This directory contains the refactored user keyboard modules, previously consolidated in a single 915-line `user_keyboards.py` file.

## Module Organization

The keyboards have been organized into 7 focused modules based on functionality:

### 1. `main_menu.py` (157 lines)
Contains the main menu keyboard with conditional button logic.

**Functions:**
- `main_menu_reply_keyboard()` - Main navigation keyboard with admin/blacklist/registration logic

**Features:**
- Conditional buttons based on user status (blocked, admin, unregistered)
- Admin panel button for administrators
- Master key management button for super admin
- Reduced menu for unregistered users
- Appeal button for blocked users

---

### 2. `menus.py` (380 lines)
Contains standard menu keyboards for various user actions.

**Functions:**
- `balance_menu_keyboard()` - Balance viewing menu
- `deposit_menu_keyboard()` - Deposit level selection with status indicators
- `withdrawal_menu_keyboard()` - Withdrawal options menu
- `referral_menu_keyboard()` - Referral program menu
- `settings_menu_keyboard()` - User settings menu
- `profile_menu_keyboard()` - Profile viewing menu
- `contact_update_menu_keyboard()` - Contact update options
- `contact_input_keyboard()` - Contact input with skip option
- `wallet_menu_keyboard()` - Wallet management menu
- `support_keyboard()` - Support menu with FAQ and tickets
- `notification_settings_reply_keyboard()` - Notification toggles
- `contacts_choice_keyboard()` - Contact sharing during registration

**Features:**
- Deposit menu shows level statuses (active/available/locked)
- Navigation buttons (back, main menu)
- Skip options where appropriate

---

### 3. `financial.py` (80 lines)
Contains keyboards for financial password operations.

**Functions:**
- `finpass_input_keyboard()` - Financial password input
- `finpass_recovery_keyboard()` - Password recovery flow
- `finpass_recovery_confirm_keyboard()` - Recovery confirmation
- `show_password_keyboard()` - Show password after registration

**Features:**
- Cancel options for all flows
- Confirmation before submitting recovery requests

---

### 4. `history.py` (161 lines)
Contains keyboards for viewing transaction history and lists.

**Functions:**
- `transaction_history_type_keyboard()` - Internal vs blockchain transactions
- `transaction_history_keyboard()` - Transaction filters and pagination
- `referral_list_keyboard()` - Referral level selection and pagination
- `withdrawal_history_keyboard()` - Withdrawal history pagination

**Features:**
- Filter buttons (all/deposit/withdrawal/referral)
- Pagination support (previous/next page)
- Excel export option for transaction history
- Level selection for referral views

---

### 5. `auth.py` (83 lines)
Contains keyboards for user authorization and payment flow.

**Functions:**
- `auth_wallet_input_keyboard()` - Wallet input during auth
- `auth_payment_keyboard()` - Payment confirmation
- `auth_continue_keyboard()` - Continue after successful payment
- `auth_rescan_keyboard()` - Rescan deposit option
- `auth_retry_keyboard()` - Retry payment check

**Features:**
- Cancel options
- Clear flow progression
- Rescan for payment verification

---

### 6. `inquiry.py` (66 lines)
Contains keyboards for user inquiry (questions to admins) functionality.

**Functions:**
- `inquiry_input_keyboard()` - Inquiry input screen
- `inquiry_dialog_keyboard()` - Active inquiry dialog (user side)
- `inquiry_waiting_keyboard()` - Waiting for admin response
- `inquiry_history_keyboard()` - Inquiry history view

**Features:**
- Close/cancel inquiry options
- Add more details to inquiry
- View inquiry history
- Start new inquiry

---

### 7. `utility.py` (43 lines)
Contains simple, reusable utility keyboards.

**Functions:**
- `confirmation_keyboard()` - Yes/No confirmation
- `cancel_keyboard()` - Simple cancel button

**Features:**
- Generic reusable keyboards
- Consistent UI patterns

---

## Package Structure

```
bot/keyboards/user/
├── __init__.py          (119 lines) - Re-exports all keyboards
├── main_menu.py         (157 lines) - Main menu keyboard
├── menus.py             (380 lines) - Basic menu keyboards
├── financial.py         (80 lines)  - Financial keyboards
├── history.py           (161 lines) - History/list keyboards
├── auth.py              (83 lines)  - Authorization keyboards
├── inquiry.py           (66 lines)  - Inquiry keyboards
├── utility.py           (43 lines)  - Utility keyboards
└── README.md            (this file)
```

**Total:** 1,089 lines across 8 files (averaging 136 lines per file)
**Original:** 915 lines in a single file

---

## Usage

All keyboards can be imported in three ways:

### 1. From the specific module (most explicit):
```python
from bot.keyboards.user.main_menu import main_menu_reply_keyboard
from bot.keyboards.user.menus import deposit_menu_keyboard
from bot.keyboards.user.financial import finpass_input_keyboard
```

### 2. From the user package (recommended):
```python
from bot.keyboards.user import (
    main_menu_reply_keyboard,
    deposit_menu_keyboard,
    finpass_input_keyboard,
)
```

### 3. From the main keyboards package (backward compatible):
```python
from bot.keyboards import (
    main_menu_reply_keyboard,
    deposit_menu_keyboard,
    finpass_input_keyboard,
)
```

---

## Backward Compatibility

The original `bot/keyboards/user_keyboards.py` file has been replaced with a compatibility shim (113 lines) that re-exports all functions from the new structure. All existing imports will continue to work without modification:

```python
# This still works!
from bot.keyboards.user_keyboards import main_menu_reply_keyboard
```

---

## Benefits of Refactoring

1. **Improved Maintainability**: Each module has a clear, focused purpose
2. **Better Code Organization**: Related keyboards are grouped together
3. **Easier Navigation**: Smaller files are easier to read and understand
4. **No Breaking Changes**: Full backward compatibility maintained
5. **Better Documentation**: Each module has clear docstrings and comments
6. **Scalability**: Easy to add new keyboards without bloating a single file

---

## Module Dependencies

All modules depend on:
- `aiogram.types.KeyboardButton`
- `aiogram.types.ReplyKeyboardMarkup`
- `aiogram.utils.keyboard.ReplyKeyboardBuilder`

Additional dependencies:
- `main_menu.py`: `loguru.logger`, `app.models.user.User`, `app.models.blacklist.*`, `app.config.settings`

---

## All Functions (32 total)

### Main Menu (1)
- main_menu_reply_keyboard

### Basic Menus (12)
- balance_menu_keyboard
- deposit_menu_keyboard
- withdrawal_menu_keyboard
- referral_menu_keyboard
- settings_menu_keyboard
- profile_menu_keyboard
- contact_update_menu_keyboard
- contact_input_keyboard
- wallet_menu_keyboard
- support_keyboard
- notification_settings_reply_keyboard
- contacts_choice_keyboard

### Financial (4)
- finpass_input_keyboard
- finpass_recovery_keyboard
- finpass_recovery_confirm_keyboard
- show_password_keyboard

### History (4)
- transaction_history_type_keyboard
- transaction_history_keyboard
- referral_list_keyboard
- withdrawal_history_keyboard

### Authorization (5)
- auth_wallet_input_keyboard
- auth_payment_keyboard
- auth_continue_keyboard
- auth_rescan_keyboard
- auth_retry_keyboard

### Inquiry (4)
- inquiry_input_keyboard
- inquiry_dialog_keyboard
- inquiry_waiting_keyboard
- inquiry_history_keyboard

### Utility (2)
- confirmation_keyboard
- cancel_keyboard

---

## Testing

All modules have been syntax-checked and verified:
- ✓ All Python syntax is valid
- ✓ All 32 functions are present and accounted for
- ✓ All imports are correctly configured
- ✓ Backward compatibility is maintained

---

## Future Improvements

Potential enhancements that could be made:
1. Add type hints for better IDE support
2. Add unit tests for each keyboard function
3. Extract button text to constants for i18n
4. Add keyboard preview documentation with screenshots
5. Consider creating a keyboard builder base class for consistency

---

Last Updated: 2025-12-05
