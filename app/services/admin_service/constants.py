"""
Admin Service - Constants.

Configuration constants for admin authentication and session management.
"""

# Admin session configuration
SESSION_DURATION_HOURS = 24

# Master key configuration
MASTER_KEY_LENGTH = 32  # 32 bytes = 256 bits

# Admin login rate limiting
ADMIN_LOGIN_MAX_ATTEMPTS = 5
ADMIN_LOGIN_WINDOW_SECONDS = 3600  # 1 hour
