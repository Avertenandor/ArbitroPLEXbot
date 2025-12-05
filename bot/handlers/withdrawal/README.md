# Withdrawal Handlers Module

This module has been refactored from a single large file (749 lines) into smaller, well-organized modules for better maintainability and code organization.

## Module Structure

### `__init__.py` (54 lines)
- Main package initialization file
- Creates and exports the main `router` used by `bot/main.py`
- Re-exports all public functions for backward compatibility
- Includes all sub-routers from individual modules

### `eligibility.py` (59 lines)
**Purpose:** User eligibility and verification checks

**Functions:**
- `is_level1_only_user()` - Check if user has only level 1 deposits
- `check_withdrawal_eligibility()` - Verify if user can withdraw (financial password + level-based verification)

**Key Logic:**
- Level 1 users: Only need financial password
- Level 2+ users: Need financial password + phone OR email

### `auto_payout.py` (93 lines)
**Purpose:** Automatic withdrawal processing

**Functions:**
- `_safe_process_auto_payout()` - Safe wrapper for auto-payout execution
- `process_auto_payout()` - Process blockchain transaction and notify user

**Key Features:**
- Background task execution
- Blockchain service integration
- Transaction status updates
- User notifications with transaction links

### `handlers.py` (156 lines)
**Purpose:** Main withdrawal menu and entry point handlers

**Handlers:**
- `show_withdrawal_menu()` - Display withdrawal options menu
- `withdraw_all()` - Handle "withdraw all balance" request
- `withdraw_amount()` - Handle "withdraw specific amount" request

**Key Features:**
- Menu navigation
- Eligibility checks before allowing withdrawals
- Balance validation
- Minimum amount checks

### `processors.py` (417 lines)
**Purpose:** Amount validation and financial password processing

**Handlers:**
- `confirm_withdrawal()` - Handle user confirmation (yes/no)
- `process_withdrawal_amount()` - Validate and process entered amount
- `process_financial_password()` - Verify password and create withdrawal transaction
- `handle_smart_withdrawal_amount()` - Smart handler for direct numeric input

**Key Features:**
- FSM state management
- Amount validation with common validator
- Financial password verification with rate limiting
- Rate limiting for withdrawal requests
- Auto-payout vs manual processing logic
- Transaction creation and user notifications

### `history.py` (93 lines)
**Purpose:** Withdrawal history display

**Functions:**
- `show_history()` - Public entry point for showing history
- `_show_withdrawal_history()` - Internal function with pagination support

**Key Features:**
- Pagination support (10 items per page)
- Status icons for different transaction states
- Transaction details display (amount, fee, net amount)
- BscScan transaction links

## Backward Compatibility

All imports remain compatible:
```python
from bot.handlers import withdrawal

# Router for bot registration
dp.include_router(withdrawal.router)

# All public functions are still accessible
withdrawal.check_withdrawal_eligibility(...)
withdrawal.process_auto_payout(...)
```

## Handler Registration

All handlers are registered through the main router:
1. Menu button: "💸 Вывести средства"
2. Menu button: "💸 Вывести всю сумму"
3. Menu button: "💵 Вывести указанную сумму"
4. Menu button: "📜 История выводов"
5. FSM state: `WithdrawalStates.waiting_for_confirmation`
6. FSM state: `WithdrawalStates.waiting_for_amount`
7. FSM state: `WithdrawalStates.waiting_for_financial_password`
8. Regex handler: Numeric input in withdrawal context

## Dependencies

### Internal Dependencies
- `app.models.user.User`
- `app.models.transaction.Transaction`
- `app.models.enums.TransactionStatus`
- `app.services.user_service.UserService`
- `app.services.withdrawal_service.WithdrawalService`
- `app.services.blockchain_service.get_blockchain_service`
- `app.repositories.deposit_repository.DepositRepository`
- `app.validators.common.validate_amount`
- `app.utils.security.mask_address`
- `bot.keyboards.reply.*`
- `bot.states.withdrawal.WithdrawalStates`
- `bot.i18n.loader.*`
- `bot.utils.menu_buttons.is_menu_button`
- `bot.utils.operation_rate_limit.OperationRateLimiter`

### External Dependencies
- `aiogram` - Telegram bot framework
- `sqlalchemy` - Database ORM
- `loguru` - Logging
- `decimal.Decimal` - Precise financial calculations

## Testing Checklist

When testing the refactored module, verify:
- [ ] All menu buttons work correctly
- [ ] FSM state transitions work properly
- [ ] Withdrawal eligibility checks work
- [ ] Amount validation works
- [ ] Financial password verification works
- [ ] Auto-payout triggers correctly
- [ ] Manual withdrawals are created correctly
- [ ] History display works with pagination
- [ ] Smart numeric input handler works
- [ ] Rate limiting works
- [ ] User notifications are sent correctly
- [ ] Transaction status updates work

## Future Improvements

Potential enhancements:
1. Further split `processors.py` if it grows beyond 500 lines
2. Add unit tests for each module
3. Extract configuration constants to a separate config file
4. Add more detailed logging for debugging
5. Consider adding a `validators.py` module for complex validation logic
