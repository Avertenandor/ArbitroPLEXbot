"""
Admin Service - Cryptographic Utilities.

This module provides utilities for:
- Master key generation
- Master key hashing and verification
- Session token generation
"""

import secrets

import bcrypt

from .constants import MASTER_KEY_LENGTH


def generate_master_key() -> str:
    """
    Generate random master key.

    Returns:
        Hex-encoded master key
    """
    return secrets.token_hex(MASTER_KEY_LENGTH)


def hash_master_key(master_key: str) -> str:
    """
    Hash master key using bcrypt.

    Args:
        master_key: Plain master key

    Returns:
        Hashed master key
    """
    return bcrypt.hashpw(
        master_key.encode(), bcrypt.gensalt()
    ).decode()


def verify_master_key(
    plain_key: str, hashed_key: str
) -> bool:
    """
    Verify master key against hash.

    Args:
        plain_key: Plain master key
        hashed_key: Hashed master key

    Returns:
        True if match
    """
    return bcrypt.checkpw(
        plain_key.encode(), hashed_key.encode()
    )


def generate_session_token() -> str:
    """
    Generate random session token.

    Returns:
        URL-safe session token
    """
    return secrets.token_urlsafe(32)
