"""
Security utilities for masking sensitive data in logs.

Provides functions to safely mask sensitive information like:
- Wallet addresses
- Transaction hashes
- Private keys
- Passwords
- Master keys
"""


def mask_address(address: str | None) -> str:
    """
    Mask wallet address for logging: 0x1234...5678

    Args:
        address: Wallet address to mask

    Returns:
        Masked address showing first 6 and last 4 characters

    Examples:
        >>> mask_address("0x1234567890abcdef1234567890abcdef12345678")
        '0x1234...5678'
        >>> mask_address(None)
        '***'
        >>> mask_address("short")
        '***'
    """
    if not address or len(address) < 10:
        return "***"
    return f"{address[:6]}...{address[-4:]}"


def mask_tx_hash(tx_hash: str | None) -> str:
    """
    Mask transaction hash for logging.

    Args:
        tx_hash: Transaction hash to mask

    Returns:
        Masked hash showing first 10 and last 6 characters

    Examples:
        >>> mask_tx_hash("0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
        '0x12345678...abcdef'
    """
    if not tx_hash or len(tx_hash) < 16:
        return "***"
    return f"{tx_hash[:10]}...{tx_hash[-6:]}"


def mask_sensitive(value: str | None, show_chars: int = 4) -> str:
    """
    Mask sensitive string (keys, passwords, etc).

    Args:
        value: Sensitive value to mask
        show_chars: Number of characters to show at start and end

    Returns:
        Masked value or '***' if too short

    Examples:
        >>> mask_sensitive("my_secret_key_1234567890", show_chars=4)
        'my_s...7890'
        >>> mask_sensitive("short")
        '***'
        >>> mask_sensitive(None)
        '***'
    """
    if not value or len(value) <= show_chars * 2:
        return "***"
    return f"{value[:show_chars]}...{value[-show_chars:]}"


def mask_master_key(key: str | None) -> str:
    """
    Completely mask master key - never show any part.

    Args:
        key: Master key to mask

    Returns:
        Always returns '***MASKED***'

    Note:
        Master keys should NEVER appear in logs, even partially.
    """
    return "***MASKED***" if key else "***"


def mask_private_key(key: str | None) -> str:
    """
    Completely mask private key - never show any part.

    Args:
        key: Private key to mask

    Returns:
        Always returns '***MASKED***'

    Note:
        Private keys should NEVER appear in logs, even partially.
    """
    return "***MASKED***" if key else "***"
