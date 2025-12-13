"""
Payment Retry Service Constants.

Module: constants.py
Contains configuration constants for retry mechanism.
"""

from app.config.constants import (
    PAYMENT_RETRY_BASE_DELAY_MINUTES,
    PAYMENT_RETRY_MAX_ATTEMPTS,
)

# Exponential backoff: 1min, 2min, 4min, 8min, 16min
BASE_RETRY_DELAY_MINUTES = PAYMENT_RETRY_BASE_DELAY_MINUTES
DEFAULT_MAX_RETRIES = PAYMENT_RETRY_MAX_ATTEMPTS
