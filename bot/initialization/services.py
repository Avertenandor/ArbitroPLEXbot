"""
Bot Initialization - Services Module.

Module: services.py
Initializes critical services: encryption and blockchain.
Validates environment variables.
"""

from loguru import logger

from app.config.database import async_session_maker
from app.config.settings import settings
from app.services.blockchain_service import init_blockchain_service
from app.utils.encryption import init_encryption_service


def validate_environment() -> None:
    """Validate critical environment variables."""
    try:
        # Quick validation of critical settings
        if (
            not settings.telegram_bot_token
            or "your_" in settings.telegram_bot_token.lower()
        ):
            logger.error("TELEGRAM_BOT_TOKEN is not properly configured")
        if (
            not settings.database_url
            or "your_" in settings.database_url.lower()
        ):
            logger.error("DATABASE_URL is not properly configured")
        if (
            not settings.wallet_private_key
            or "your_" in settings.wallet_private_key.lower()
        ):
            logger.warning(
                "WALLET_PRIVATE_KEY is not configured. "
                "Bot will start, but blockchain operations will be unavailable. "
                "Set key via /wallet_menu in bot interface."
            )
    except Exception as e:
        logger.warning(f"Could not validate environment: {e}")


def initialize_encryption() -> None:
    """Initialize EncryptionService for secure key storage."""
    try:
        init_encryption_service(encryption_key=settings.encryption_key)
        logger.info("EncryptionService initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize EncryptionService: {e}")
        logger.warning("Keys will be stored/loaded without encryption")


def initialize_blockchain() -> None:
    """Initialize BlockchainService."""
    try:
        init_blockchain_service(
            settings=settings,
            session_factory=async_session_maker,
        )
        logger.info("BlockchainService initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize BlockchainService: {e}")
        logger.warning("Bot will continue, but blockchain operations may fail")


def initialize_all_services() -> None:
    """Initialize all critical services."""
    validate_environment()
    initialize_encryption()
    initialize_blockchain()
