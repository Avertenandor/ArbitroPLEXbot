"""
Shared fixtures for unit tests.

This module provides common fixtures used across multiple test modules:
- Mock database session
- RewardCalculator instance
- Mock deposit objects
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.reward.reward_calculator import RewardCalculator


@pytest.fixture
def mock_session():
    """
    Mock async database session.

    Returns:
        AsyncMock: Mocked async session for database operations
    """
    session = AsyncMock()
    return session


@pytest.fixture
def calculator(mock_session):
    """
    Create RewardCalculator instance with mocked session.

    Args:
        mock_session: Mocked database session

    Returns:
        RewardCalculator: Calculator instance for testing
    """
    return RewardCalculator(mock_session)


@pytest.fixture
def mock_deposit():
    """
    Create mock deposit object with default values.

    Default values:
    - id: 1
    - user_id: 100
    - amount: 1000 (deposit amount)
    - level: 1
    - roi_cap_amount: 5000 (500% ROI cap)
    - roi_paid_amount: 0 (no payments yet)
    - is_roi_completed: False

    Returns:
        MagicMock: Mock deposit object
    """
    deposit = MagicMock()
    deposit.id = 1
    deposit.user_id = 100
    deposit.amount = Decimal("1000")
    deposit.level = 1
    deposit.roi_cap_amount = Decimal("5000")  # 500% cap
    deposit.roi_paid_amount = Decimal("0")
    deposit.is_roi_completed = False
    return deposit
