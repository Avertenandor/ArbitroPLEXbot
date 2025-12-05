# Admin Management Module

This module handles all admin-related operations.

## Structure

```
admins/
├── __init__.py          # Module exports and public API (54 lines)
├── router.py            # Router definition (10 lines)
├── menu.py              # Admin management menu (44 lines)
├── create.py            # Admin creation handlers (264 lines)
├── list.py              # Admin listing handlers (66 lines)
├── delete.py            # Admin deletion handlers (168 lines)
└── emergency.py         # Emergency blocking handlers (276 lines)
```

## Features

### Admin Creation (`create.py`)
- Creates new admin accounts with role assignment
- Supports three roles: admin, extended_admin, super_admin
- Automatically generates and sends master keys
- Validates Telegram IDs
- Logs all creation events

### Admin Listing (`list.py`)
- Displays all administrators
- Shows roles and creator information
- Only accessible to super_admins

### Admin Deletion (`delete.py`)
- Safely deletes admin accounts
- Prevents deletion of last super_admin
- Prevents self-deletion
- Logs all deletion events

### Emergency Blocking (`emergency.py`)
- Emergency blocking of compromised admin accounts
- Blacklists Telegram ID (TERMINATED status)
- Deletes admin from system
- Bans user account if exists
- Notifies all super_admins
- Atomic operation with rollback on failure

## Usage

```python
# Import the router
from bot.handlers.admin.admins import router

# Import specific functions
from bot.handlers.admin.admins import show_admin_management

# All handlers are automatically registered on the router
```

## Dependencies

- aiogram: Bot framework
- sqlalchemy: Database operations
- app.services.admin_service: Admin management
- app.services.admin_log_service: Audit logging
- bot.handlers.admin.utils.admin_checks: Permission checks

## Original File

This module was refactored from `/home/user/ArbitroPLEXbot/bot/handlers/admin/admins.py` (733 lines).
The original file is backed up as `admins.py.old`.
