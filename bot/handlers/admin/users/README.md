# Admin Users Handler - Refactored Module Structure

## Overview

This module was refactored from a single 1068-line file (`users.py`) into a well-organized directory structure with smaller, focused modules. The refactoring maintains **100% backward compatibility** - all existing imports continue to work exactly as before.

## Module Structure

```
bot/handlers/admin/users/
├── __init__.py          # Router aggregation and module exports (75 lines)
├── menu.py              # Main menu and navigation (50 lines)
├── search.py            # User search functionality (135 lines)
├── list.py              # Paginated user list (121 lines)
├── profile.py           # User profile display (155 lines)
├── balance.py           # Balance management (161 lines)
├── security.py          # Block/unblock/terminate (410 lines)
├── transactions.py      # Transaction history (56 lines)
├── deposits.py          # Deposit scanning (84 lines)
├── referrals.py         # Referral statistics (39 lines)
└── README.md            # This file
```

## Module Descriptions

### 1. menu.py - Menu and Navigation
- **Purpose**: Main users management menu and back navigation
- **Handlers**:
  - `handle_admin_users_menu`: Show users menu
  - `handle_back_to_admin_panel`: Return to admin panel
- **Lines**: 50

### 2. search.py - User Search
- **Purpose**: Search users by username, telegram ID, wallet address, or user ID
- **Handlers**:
  - `cmd_search_user`: Quick search via `/search` command
  - `handle_find_user`: Start interactive search flow
  - `process_find_user_input`: Process search input
- **Lines**: 135

### 3. list.py - User List Management
- **Purpose**: Display paginated list of users with selection
- **Handlers**:
  - `handle_list_users`: Show paginated user list
  - `handle_user_list_pagination`: Handle prev/next buttons
  - `handle_user_selection`: Handle user selection from list
  - `handle_back_to_list`: Return to list view
- **Lines**: 121

### 4. profile.py - User Profile Display
- **Purpose**: Display detailed user profile information
- **Handlers**:
  - `handle_profile_by_id_command`: Open profile by command
  - `show_user_profile`: Main profile display function (shared utility)
- **Lines**: 155

### 5. balance.py - Balance Management
- **Purpose**: Adjust user balances (credit/debit)
- **Handlers**:
  - `handle_profile_balance`: Start balance change flow
  - `process_balance_change`: Process balance adjustment
- **Lines**: 161
- **Notes**: Requires extended admin permissions

### 6. security.py - Security Operations
- **Purpose**: User blocking, unblocking, and account termination
- **Handlers**:
  - `handle_profile_block_toggle`: Toggle block from profile
  - `handle_profile_terminate`: Terminate from profile
  - `handle_start_block_user`: Start direct block flow
  - `handle_block_user_input`: Process block input
  - `handle_terminate_user_input`: Process terminate input
  - `handle_start_terminate_user_direct`: Start direct terminate flow
- **Lines**: 410 (largest module)
- **Notes**: Contains both profile-based and direct flow handlers

### 7. transactions.py - Transaction History
- **Purpose**: Display user transaction history
- **Handlers**:
  - `handle_profile_history`: Show last 10 transactions
- **Lines**: 56

### 8. deposits.py - Deposit Scanning
- **Purpose**: Admin-initiated blockchain deposit scanning
- **Handlers**:
  - `handle_admin_scan_deposit`: Force scan user deposits
- **Lines**: 84

### 9. referrals.py - Referral Statistics
- **Purpose**: Display referral statistics for a user
- **Handlers**:
  - `handle_profile_referrals`: Show referral stats
- **Lines**: 39

## Backward Compatibility

The refactoring maintains **100% backward compatibility**. The original import pattern:

```python
from bot.handlers.admin import users
users.router  # Access the router
```

...continues to work exactly as before. The `__init__.py` file aggregates all sub-module routers into a single router object.

## Import Strategy

To avoid circular dependencies, modules use lazy imports for cross-module references:

```python
# Import at function level to avoid circular dependency
from bot.handlers.admin.users.profile import show_user_profile
await show_user_profile(message, user, state, session)
```

This pattern is used when:
- search.py needs to show profiles
- list.py needs to show profiles
- balance.py needs to show profiles after updates
- security.py needs to show profiles after actions
- deposits.py needs to show profiles after scanning

## Statistics

- **Original file**: 1068 lines
- **Refactored total**: 1286 lines (including documentation)
- **Functions preserved**: 22 functions
- **Handlers preserved**: 22 handlers
- **Largest module**: security.py (410 lines)
- **Smallest module**: referrals.py (39 lines)
- **Average module size**: ~143 lines (excluding __init__.py)

## Handler Registration Order

The `__init__.py` registers routers in a specific order to ensure correct handler priority:

1. menu.router - Base menu functionality
2. search.router - Search handlers
3. list.router - List management
4. profile.router - Profile display
5. balance.router - Balance management
6. security.router - Security operations (after profile for proper precedence)
7. transactions.router - Transaction history
8. deposits.router - Deposit scanning
9. referrals.router - Referral stats

## Development Notes

### Adding New Functionality
To add new user management features:
1. Create a new module in `bot/handlers/admin/users/`
2. Create a router with a unique name
3. Add handlers to the router
4. Import and include the router in `__init__.py`

### Circular Dependencies
If you encounter circular dependencies:
- Use lazy imports (import inside functions)
- Share utility functions through profile.py's `show_user_profile`
- Avoid importing handlers at module level

### Testing
All handlers have been verified to:
- Preserve original functionality
- Maintain proper FSM state management
- Use correct admin permission checks
- Handle errors appropriately
- Send proper notifications

## Related Files

- **State definitions**: `bot/states/admin_states.py`
- **Admin checks**: `bot/handlers/admin/utils/admin_checks.py`
- **Keyboards**: `bot/keyboards/reply.py`
- **Services used**:
  - `app.services.user_service.UserService`
  - `app.services.blacklist_service.BlacklistService`
  - `app.services.admin_log_service.AdminLogService`
  - `app.services.deposit_scan_service.DepositScanService`
  - `app.services.referral_service.ReferralService`

## Backup

The original file has been preserved as:
- `bot/handlers/admin/users.py.backup`

This backup can be restored if needed, but all functionality has been verified to work in the refactored structure.
