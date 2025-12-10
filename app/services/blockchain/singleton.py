"""
Singleton pattern for BlockchainService.

Provides global access to a single BlockchainService instance.
"""

from typing import Any

from app.config.settings import Settings


# Forward declaration to avoid circular import
_blockchain_service: Any = None


def get_blockchain_service():
    """
    Get the singleton blockchain service instance.

    Returns:
        BlockchainService instance

    Raises:
        RuntimeError: If service not initialized
    """
    global _blockchain_service
    if _blockchain_service is None:
        raise RuntimeError("BlockchainService not initialized")
    return _blockchain_service


def init_blockchain_service(settings: Settings, session_factory: Any = None) -> None:
    """
    Initialize the singleton blockchain service instance.

    Args:
        settings: Application settings
        session_factory: Optional async session factory for DB access
    """
    global _blockchain_service
    # Import here to avoid circular dependency
    from app.services.blockchain.service_facade import BlockchainService
    _blockchain_service = BlockchainService(settings, session_factory)
