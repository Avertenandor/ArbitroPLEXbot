"""
Blockchain Service Module.

Refactored module structure:
- service.py              - Main BlockchainService class (orchestrator)
- deposit_operations.py   - Deposit-related operations (235 lines)
- payment_operations.py   - Payment-related operations (78 lines)
- balance_operations.py   - Balance query operations (61 lines)
- validation.py           - Validation utilities (45 lines)
- health_check.py         - Health check operations (106 lines)
- failover.py             - Failover logic (97 lines)
- singleton.py            - Singleton pattern (88 lines)

Each module is now under 300 lines and focused on a single responsibility.
"""

# Import main service class
from .service import BlockchainService

# Import singleton functions
from .singleton import get_blockchain_service, init_blockchain_service


# Re-export for backward compatibility
__all__ = [
    "BlockchainService",
    "get_blockchain_service",
    "init_blockchain_service",
]
