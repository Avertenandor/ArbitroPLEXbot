"""
Admin service.

REFACTORED: This file has been refactored into smaller modules.
For backward compatibility, all public APIs are re-exported from here.

New module structure:
- app/services/admin_service/constants.py: Configuration constants
- app/services/admin_service/crypto.py: Key generation and hashing
- app/services/admin_service/admin_manager.py: Admin CRUD operations
- app/services/admin_service/session_manager.py: Session lifecycle management
- app/services/admin_service/rate_limiter.py: Rate limiting and security
- app/services/admin_service/service.py: Main AdminService class

To use the new structure directly:
    from app.services.admin_service import AdminService

This provides the same API as before, but the implementation is now
better organized into smaller, focused modules.

The AdminService class delegates work to specialized managers:
- AdminManager: Handles admin creation, retrieval, and deletion
- SessionManager: Manages session creation, validation, and logout
- RateLimiter: Tracks failed logins and enforces rate limits
"""

# Re-export AdminService from the new admin_service package
from app.services.admin_service import AdminService

# Re-export constants for backward compatibility (if needed)
from app.services.admin_service.constants import (
    ADMIN_LOGIN_MAX_ATTEMPTS,
    ADMIN_LOGIN_WINDOW_SECONDS,
    MASTER_KEY_LENGTH,
    SESSION_DURATION_HOURS,
)


__all__ = [
    "AdminService",
    # Constants (for backward compatibility)
    "SESSION_DURATION_HOURS",
    "MASTER_KEY_LENGTH",
    "ADMIN_LOGIN_MAX_ATTEMPTS",
    "ADMIN_LOGIN_WINDOW_SECONDS",
]
