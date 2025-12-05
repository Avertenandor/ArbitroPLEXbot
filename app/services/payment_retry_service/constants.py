"""
Payment Retry Service Constants.

Module: constants.py
Contains configuration constants for retry mechanism.
"""

# Exponential backoff: 1min, 2min, 4min, 8min, 16min
BASE_RETRY_DELAY_MINUTES = 1
DEFAULT_MAX_RETRIES = 5
