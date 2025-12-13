"""
Operational constants for ArbitroPLEXbot.

Technical/operational constants used across the application.
Includes timeouts, limits, retry configurations, and AI service parameters.
"""

# =============================================================================
# LOCK TIMEOUTS (seconds)
# =============================================================================
# Used by distributed_lock.py for Redis locks

# Short operations (balance checks, user lookups)
LOCK_TIMEOUT_SHORT = 30

# Medium operations (transactions, deposits)
LOCK_TIMEOUT_MEDIUM = 60

# Long operations (scans, batch processing)
LOCK_TIMEOUT_LONG = 300

# Very long operations (reconciliation, cleanup)
LOCK_TIMEOUT_EXTENDED = 600


# =============================================================================
# BLOCKING TIMEOUTS (seconds)
# =============================================================================
# How long to wait for lock acquisition

BLOCKING_TIMEOUT_SHORT = 3.0
BLOCKING_TIMEOUT_DEFAULT = 5.0
BLOCKING_TIMEOUT_LONG = 10.0


# =============================================================================
# RETRY CONFIGURATIONS
# =============================================================================

# Default retry count for most operations
DEFAULT_MAX_RETRIES = 3

# Payment operations (more critical - more retries)
PAYMENT_MAX_RETRIES = 5

# Notification operations
NOTIFICATION_MAX_RETRIES = 3


# =============================================================================
# DRAMATIQ TASK TIME LIMITS (milliseconds)
# =============================================================================

# Short tasks (1 minute) - session cleanup, health checks
DRAMATIQ_TIME_LIMIT_SHORT = 60_000

# Medium tasks (2 minutes) - cache sync, metrics
DRAMATIQ_TIME_LIMIT_MEDIUM = 120_000

# Standard tasks (5 minutes) - most background jobs
DRAMATIQ_TIME_LIMIT_STANDARD = 300_000

# Long tasks (10 minutes) - scans, reconciliation, PLEX monitoring
DRAMATIQ_TIME_LIMIT_LONG = 600_000


# =============================================================================
# PAGINATION LIMITS
# =============================================================================

# Default page size for most lists
DEFAULT_PAGE_SIZE = 10

# Medium page size for admin panels
MEDIUM_PAGE_SIZE = 15

# Large page size for batch processing
LARGE_PAGE_SIZE = 20

# Extra large page size for exports
EXPORT_PAGE_SIZE = 50

# Maximum page size for batch operations
MAX_PAGE_SIZE = 100

# Maximum page size for large batch operations
MAX_LARGE_PAGE_SIZE = 1000


# =============================================================================
# BLOCKCHAIN SCANNING LIMITS
# =============================================================================

# Maximum blocks per scan iteration
MAX_BLOCKS_PER_SCAN = 10_000

# Maximum blocks for payment verification
MAX_BLOCKS_PAYMENT_VERIFICATION = 50_000

# Maximum blocks for history scanning
MAX_BLOCKS_HISTORY_SCAN = 100_000


# =============================================================================
# AI SERVICE PARAMETERS
# =============================================================================

# Token limits for AI responses
AI_MAX_TOKENS_SHORT = 1024      # Quick responses, classifications
AI_MAX_TOKENS_MEDIUM = 2048     # Standard conversations
AI_MAX_TOKENS_LONG = 4096       # Detailed responses, code generation


# =============================================================================
# RATE LIMITING
# =============================================================================

# Rate limit for user requests (per time window)
USER_RATE_LIMIT = 30

# Rate limit time window (seconds)
RATE_LIMIT_WINDOW = 60


# =============================================================================
# RPC/BLOCKCHAIN TIMEOUTS (seconds)
# =============================================================================
# Note: More blockchain timeouts in app/config/constants.py

RPC_TIMEOUT = 30

# Transaction confirmation wait time
TX_CONFIRMATION_TIMEOUT = 120
