"""
Blockchain services module.

Provides unified access to blockchain operations through a modular architecture.
All blockchain functionality is organized into specialized managers and utilities.
"""

# Re-export main service and singleton pattern from refactored modules
from .service_facade import BlockchainService
from .singleton import get_blockchain_service, init_blockchain_service

# Re-export constants for convenience
from .constants import USDT_ABI, USDT_DECIMALS

__all__ = [
    "BlockchainService",
    "get_blockchain_service",
    "init_blockchain_service",
    "USDT_ABI",
    "USDT_DECIMALS",
]
