"""Default Knowledge Base Data for ARIA AI Assistant.

This module combines knowledge base data from multiple sources:
- data_core: Founder, Ecosystem, Arbitrage, Token
- data_operations: Deposits, Withdrawals, ROI, Session, Rabbits
- data_admin: Referrals, Bonuses, Analytics

All data is combined into DEFAULT_KB for use by the KnowledgeBase.
"""

from typing import Any

from .data_admin import KB_ADMIN
from .data_core import KB_CORE
from .data_operations import KB_OPERATIONS


DEFAULT_KB: list[dict[str, Any]] = [
    *KB_CORE,
    *KB_OPERATIONS,
    *KB_ADMIN,
]
