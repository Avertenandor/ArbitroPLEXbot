"""
AI Tool Executor - Backward Compatibility Wrapper.

This file now serves as a compatibility layer, importing from the
refactored modular structure in app/services/ai/executor/.

The ToolExecutor class and validation functions are now organized into:
- executor/validators.py - Input validation helpers
- executor/core.py - Main ToolExecutor class
- executor/message_handlers.py - Message and communication handlers
- executor/user_handlers.py - User management handlers
- executor/deposit_handlers.py - Deposit management handlers
- executor/withdrawal_handlers.py - Withdrawal management handlers
- executor/admin_handlers.py - Admin and security handlers
- executor/system_handlers.py - System administration handlers

For new code, import directly from app.services.ai.executor:
    from app.services.ai.executor import ToolExecutor

For validation functions, import from validators:
    from app.services.ai.executor.validators import (
        validate_required_string,
        validate_positive_decimal,
        # etc.
    )
"""

# Re-export for backward compatibility
from app.services.ai.executor import ToolExecutor
from app.services.ai.executor.validators import (
    validate_limit,
    validate_optional_string,
    validate_positive_decimal,
    validate_positive_int,
    validate_required_string,
    validate_user_identifier,
)

__all__ = [
    "ToolExecutor",
    "validate_required_string",
    "validate_optional_string",
    "validate_positive_int",
    "validate_positive_decimal",
    "validate_user_identifier",
    "validate_limit",
]
