"""
Application constants.

Centralized constants for the application.
"""

from app.config.business_constants import MAX_DEPOSITS_PER_USER

# Support ticket limits
MAX_OPEN_TICKETS_PER_USER = 5

# ========================================================================
# BLOCKCHAIN CONSTANTS
# ========================================================================

# Blockchain operation timeouts (in seconds)
BLOCKCHAIN_TIMEOUT = 30.0  # Standard blockchain operations (get_transaction, etc.)
BLOCKCHAIN_LONG_TIMEOUT = 120.0  # Long-running operations (scanning, large filters)
BLOCKCHAIN_EXECUTOR_TIMEOUT = 20.0  # Timeout for run_in_executor operations (reduced from 60s)
BLOCKCHAIN_RPC_TIMEOUT = 30  # RPC provider HTTP timeout

# Blockchain retry settings
BLOCKCHAIN_MAX_RETRIES = 5  # Maximum retry attempts for blockchain operations
BLOCKCHAIN_RETRY_DELAY_BASE = 2  # Base delay in seconds for exponential backoff
BLOCKCHAIN_WS_RECONNECT_DELAY = 5  # WebSocket reconnection delay in seconds
BLOCKCHAIN_WS_MAX_RECONNECT_ATTEMPTS = 10  # Maximum WebSocket reconnection attempts

# RPC rate limiting
RPC_MAX_CONCURRENT = 10  # Maximum concurrent RPC calls
RPC_MAX_RPS = 25  # Maximum requests per second

# Blockchain scanning limits
BLOCKCHAIN_MAX_SEARCH_BLOCKS = 100000  # Maximum blocks to search in deposit operations
BLOCKCHAIN_SCAN_MAX_BLOCKS = 50000  # Maximum blocks per deposit scan (reduced to avoid RPC limits)

# Distributed lock settings
DISTRIBUTED_LOCK_TIMEOUT = 30  # Lock timeout in seconds
DISTRIBUTED_LOCK_BLOCKING_TIMEOUT = 5.0  # Time to wait for lock acquisition

# ========================================================================
# TELEGRAM BOT CONSTANTS
# ========================================================================

# Telegram bot timeouts (in seconds)
TELEGRAM_TIMEOUT = 10.0  # Telegram API operations timeout
TELEGRAM_VIDEO_TIMEOUT = 60.0  # Video/document upload timeout (larger files)

# Telegram rate limiting (in seconds)
# Telegram has ~30 msg/sec limit, but we keep a safety buffer
TELEGRAM_MESSAGE_DELAY = 0.1  # 100ms between messages (10 msg/sec)
TELEGRAM_BATCH_DELAY = 1.0    # 1 second between batches
TELEGRAM_BATCH_SIZE = 20      # Messages per batch before additional delay

# ========================================================================
# RETRY SERVICE CONSTANTS
# ========================================================================

# Payment retry settings
PAYMENT_RETRY_BASE_DELAY_MINUTES = 1  # Base delay for exponential backoff (1min, 2min, 4min...)
PAYMENT_RETRY_MAX_ATTEMPTS = 5  # Maximum retry attempts before moving to DLQ

# Notification retry settings
NOTIFICATION_RETRY_MAX_ATTEMPTS = 5  # Maximum notification retry attempts
NOTIFICATION_RETRY_DELAYS_MINUTES = [1, 5, 15, 60, 120]  # Retry schedule: 1min, 5min, 15min, 1h, 2h
NOTIFICATION_RETRY_BATCH_LIMIT = 100  # Maximum notifications to process per batch

# Withdrawal retry settings
WITHDRAWAL_MAX_RETRIES = 3  # Maximum retry attempts for withdrawal operations
WITHDRAWAL_RETRY_DELAY_BASE = 1.0  # Base delay in seconds for exponential backoff
WITHDRAWAL_HIGH_FEE_WARNING_THRESHOLD = 0.5  # Warn if fee exceeds 50% of amount

# ========================================================================
# AUTHENTICATION & SECURITY CONSTANTS
# ========================================================================

# Financial password settings
FINPASS_MAX_ATTEMPTS = 5  # Maximum failed attempts before lockout
FINPASS_LOCKOUT_MINUTES = 15  # Account lockout duration in minutes

# Admin authentication settings
ADMIN_SESSION_DURATION_HOURS = 24  # Admin session validity duration
ADMIN_MASTER_KEY_LENGTH = 32  # Master key length in bytes (256 bits)
ADMIN_LOGIN_MAX_ATTEMPTS = 5  # Maximum failed login attempts
ADMIN_LOGIN_WINDOW_SECONDS = 3600  # Rate limiting window (1 hour)

# ========================================================================
# USER LIMITS & THRESHOLDS
# ========================================================================

# User message logging
USER_MESSAGE_LOG_MAX_MESSAGES = 500  # Maximum messages to store per user

# Balance notifications (arbitrage operations display)
BALANCE_NOTIF_MIN_OPERATIONS = 181  # Minimum operations per hour (avoid round 180)
BALANCE_NOTIF_MAX_OPERATIONS = 299  # Maximum operations per hour (avoid round 300)
BALANCE_NOTIF_OPERATIONS_MEAN_SHIFT = 0.7  # Shift distribution towards max (0.5=center, 1.0=max)

# ========================================================================
# ERROR MONITORING & LOGGING CONSTANTS
# ========================================================================

# Log aggregation thresholds
LOG_ERROR_FREQUENCY_WARNING = 10  # Errors per minute to trigger warning
LOG_ERROR_FREQUENCY_CRITICAL = 50  # Errors per minute to trigger critical alert
LOG_USER_ERROR_THRESHOLD = 20  # Errors per user per hour threshold

# Memory leak prevention for log aggregation
LOG_MAX_ERROR_KEYS = 10000  # Maximum unique error keys to track
LOG_MAX_USER_ERROR_KEYS = 5000  # Maximum users to track errors for

# ========================================================================
# BLOCKCHAIN EXPLORER URLS
# ========================================================================

# BSCScan URLs
BSCSCAN_BASE_URL = "https://bscscan.com"  # BSCScan base URL
BSCSCAN_TX_URL = "https://bscscan.com/tx"  # Transaction URL template (append /{tx_hash})
BSCSCAN_ADDRESS_URL = "https://bscscan.com/address"  # Address URL template (append /{address})
