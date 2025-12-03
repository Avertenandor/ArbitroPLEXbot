"""Pytest configuration and shared fixtures for all tests."""

import os
import sys
from pathlib import Path

# Установить минимальные переменные окружения для тестов
# Используем корректный формат токена Telegram бота для валидации
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("BSC_RPC_URL", "https://bsc-dataseed.binance.org/")
os.environ.setdefault("BSC_TESTNET_RPC_URL", "https://data-seed-prebsc-1-s1.binance.org:8545/")
os.environ.setdefault("TREASURY_ADDRESS", "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
os.environ.setdefault("TREASURY_PRIVATE_KEY", "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing_only")
os.environ.setdefault("ENCRYPTION_KEY", "test_encryption_key_32_bytes_000")
os.environ.setdefault("ADMIN_USER_IDS", "123456789")

# Дополнительные переменные из settings.py
os.environ.setdefault("WALLET_ADDRESS", "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
os.environ.setdefault("USDT_CONTRACT_ADDRESS", "0x55d398326f99059fF775485246999027B3197955")
os.environ.setdefault("RPC_URL", "https://bsc-dataseed.binance.org/")
os.environ.setdefault("AUTH_PLEX_TOKEN_ADDRESS", "0x0000000000000000000000000000000000000000")
os.environ.setdefault("AUTH_SYSTEM_WALLET_ADDRESS", "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")
os.environ.setdefault("SYSTEM_WALLET_ADDRESS", "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0")

# Добавить корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_session():
    """Mock AsyncSession для тестов без БД."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    session.delete = MagicMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_blockchain_service():
    """Mock BlockchainService."""
    service = AsyncMock()
    service.get_usdt_balance = AsyncMock(return_value=Decimal("100.00"))
    service.get_plex_balance = AsyncMock(return_value=Decimal("1000"))
    service.send_payment = AsyncMock(
        return_value={"success": True, "tx_hash": "0x123"}
    )
    service.verify_transaction = AsyncMock(return_value=True)
    service.get_transaction_status = AsyncMock(
        return_value={"status": "confirmed"}
    )
    return service


@pytest.fixture
def mock_bot():
    """Mock Telegram Bot."""
    bot = AsyncMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.edit_message_reply_markup = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    bot.session = AsyncMock()
    bot.session.close = AsyncMock()
    return bot


@pytest.fixture
def sample_wallet_address():
    """Sample valid BSC wallet address for testing."""
    return "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"


@pytest.fixture
def sample_transaction_hash():
    """Sample transaction hash for testing."""
    return "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


@pytest.fixture
def mock_web3_provider():
    """Mock Web3 provider for blockchain interactions."""
    provider = AsyncMock()
    provider.eth = AsyncMock()
    provider.eth.get_balance = AsyncMock(return_value=1000000000000000000)
    provider.eth.get_transaction = AsyncMock(
        return_value={
            "hash": "0x123",
            "from": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            "to": "0x0000000000000000000000000000000000000000",
            "value": 1000000000000000000,
        }
    )
    provider.eth.get_transaction_receipt = AsyncMock(
        return_value={"status": 1, "blockNumber": 12345}
    )
    return provider


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for caching tests."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.delete = AsyncMock()
    client.expire = AsyncMock()
    client.exists = AsyncMock(return_value=0)
    return client
