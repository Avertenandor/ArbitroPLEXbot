"""PLEX Payment Service.

Manages PLEX payment requirements, verification, and access level checks.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.plex_payment.core import PlexPaymentServiceCore
from app.services.plex_payment.operations import PlexPaymentOperations


class PlexPaymentService(PlexPaymentServiceCore, PlexPaymentOperations):
    """Service for managing PLEX payments.

    Handles:
    - User level verification based on PLEX balance
    - Daily payment tracking and verification
    - Warning and blocking for non-payment

    This class combines core functionality and operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        PlexPaymentServiceCore.__init__(self, session)


__all__ = ["PlexPaymentService"]
