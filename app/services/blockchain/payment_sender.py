"""
Payment Sender (Backward Compatibility Wrapper).

This file maintains backward compatibility by re-exporting the refactored
PaymentSender class from the payment_sender/ subdirectory.

REFACTORED STRUCTURE:
====================
The original payment_sender.py (748 lines) has been refactored into a modular structure:

payment_sender/
├── __init__.py              - Main PaymentSender class (orchestrator)
├── security_utils.py        - Security utilities (32 lines)
├── nonce_manager.py         - Nonce management (103 lines)
├── transaction_status.py    - Transaction status checking (100 lines)
├── balance_checker.py       - Balance queries (119 lines)
├── gas_estimator.py         - Gas estimation (112 lines)
└── transaction_sender.py    - Core transaction sending (282 lines)

Each module is now under 300 lines and focused on a single responsibility.

USAGE:
======
Old code:
    from app.services.blockchain.payment_sender import PaymentSender

New code (same as above, backward compatible):
    from app.services.blockchain.payment_sender import PaymentSender

Or directly from the subdirectory:
    from app.services.blockchain.payment_sender import PaymentSender
"""

# Re-export PaymentSender for backward compatibility
from .payment_sender import PaymentSender


__all__ = ["PaymentSender"]
