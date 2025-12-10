"""
Blockchain services module.

Provides unified access to blockchain operations through a modular architecture.
All blockchain functionality is organized into specialized managers and utilities.
"""

# Re-export main service and singleton pattern from refactored modules
# Re-export constants for convenience
from .constants import USDT_ABI, USDT_DECIMALS
from .core_constants import (
    PLEX_ABI,
    PLEX_CONTRACT_ADDRESS,
    PLEX_DECIMALS,
    PLEX_PER_DOLLAR_DAILY,
)
from .service_facade import BlockchainService
from .singleton import get_blockchain_service, init_blockchain_service


__all__ = [
    "BlockchainService",
    "get_blockchain_service",
    "init_blockchain_service",
    "USDT_ABI",
    "USDT_DECIMALS",
    "PLEX_ABI",
    "PLEX_CONTRACT_ADDRESS",
    "PLEX_DECIMALS",
    "PLEX_PER_DOLLAR_DAILY",
]
