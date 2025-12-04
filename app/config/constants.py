"""
Application constants.

Centralized constants for the application.
"""

# Support ticket limits
MAX_OPEN_TICKETS_PER_USER = 5

# Blockchain operation timeouts (in seconds)
BLOCKCHAIN_TIMEOUT = 30.0  # Standard blockchain operations (get_transaction, etc.)
BLOCKCHAIN_LONG_TIMEOUT = 120.0  # Long-running operations (scanning, large filters)
BLOCKCHAIN_EXECUTOR_TIMEOUT = 60.0  # Timeout for run_in_executor operations

# Telegram bot timeouts (in seconds)
TELEGRAM_TIMEOUT = 10.0  # Telegram API operations timeout

# Telegram rate limiting (in seconds)
# Telegram has ~30 msg/sec limit, but we keep a safety buffer
TELEGRAM_MESSAGE_DELAY = 0.1  # 100ms between messages (10 msg/sec)
TELEGRAM_BATCH_DELAY = 1.0    # 1 second between batches
TELEGRAM_BATCH_SIZE = 20      # Messages per batch before additional delay
