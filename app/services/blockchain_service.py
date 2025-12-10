"""
Blockchain Service - Backward Compatibility Wrapper.

REFACTORED STRUCTURE:
====================
The original blockchain_service.py (627 lines) has been refactored into a modular structure:

app/services/blockchain/
├── service_facade.py            - Main BlockchainService class (coordinator, ~500 lines)
├── singleton.py                 - Singleton pattern for global service access (~45 lines)
├── async_executor.py            - Async execution with failover support (~150 lines)
├── block_operations.py          - Block-related operations (~50 lines)
├── balance_operations.py        - Token balance operations (existing)
├── gas_operations.py            - Gas price optimization (existing)
├── payment_verification.py      - Payment verification (existing)
├── sync_provider_management.py  - RPC provider management (existing)
├── transaction_operations.py    - Transaction sending (existing)
├── wallet_operations.py         - Wallet operations (existing)
└── rpc_rate_limiter.py          - RPC rate limiting (existing)

Each module is focused on a single responsibility with clear separation of concerns.

MIGRATION GUIDE:
===============
All existing imports continue to work without any changes:

Old code (still works):
    from app.services.blockchain_service import (
        BlockchainService,
        get_blockchain_service,
        init_blockchain_service,
    )

New code (recommended):
    from app.services.blockchain import (
        BlockchainService,
        get_blockchain_service,
        init_blockchain_service,
    )

BENEFITS:
=========
1. Better code organization - each module has a single responsibility
2. Improved maintainability - smaller, focused modules are easier to understand
3. Better testability - isolated components can be tested independently
4. No breaking changes - all public APIs remain the same
5. Full backward compatibility - existing code continues to work
"""

# Re-export BlockchainService and singleton functions for backward compatibility
from app.services.blockchain import (
    BlockchainService,
    get_blockchain_service,
    init_blockchain_service,
)


__all__ = [
    "BlockchainService",
    "get_blockchain_service",
    "init_blockchain_service",
]
