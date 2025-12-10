"""
Blockchain Service (Backward Compatibility Wrapper).

This file maintains backward compatibility by re-exporting the refactored
BlockchainService class from the blockchain_service/ subdirectory.

REFACTORED STRUCTURE:
====================
The original blockchain_service.py (695 lines) has been refactored into a modular structure:

blockchain_service/
├── __init__.py              - Module entry point with re-exports
├── service.py               - Main BlockchainService class (orchestrator, 288 lines)
├── deposit_operations.py    - Deposit-related operations (235 lines)
├── payment_operations.py    - Payment-related operations (78 lines)
├── balance_operations.py    - Balance query operations (61 lines)
├── validation.py            - Validation utilities (45 lines)
├── health_check.py          - Health check operations (106 lines)
├── failover.py              - Failover logic (97 lines)
└── singleton.py             - Singleton pattern (88 lines)

Each module is now under 300 lines and focused on a single responsibility.

USAGE:
======
Old code:
    from app.services.blockchain.blockchain_service import (
        BlockchainService,
        get_blockchain_service,
        init_blockchain_service,
    )

New code (same as above, backward compatible):
    from app.services.blockchain.blockchain_service import (
        BlockchainService,
        get_blockchain_service,
        init_blockchain_service,
    )

Or directly from the subdirectory:
    from app.services.blockchain.blockchain_service import (
        BlockchainService,
        get_blockchain_service,
        init_blockchain_service,
    )
"""

# Re-export BlockchainService and singleton functions for backward compatibility
from .blockchain_service import (
    BlockchainService,
    get_blockchain_service,
    init_blockchain_service,
)


__all__ = [
    "BlockchainService",
    "get_blockchain_service",
    "init_blockchain_service",
]
