"""PLEX Payment Service - Operations.

Manages payment requirements, verification, and processing.
"""

from datetime import UTC, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.business_constants import PLEX_PER_DOLLAR_DAILY
from app.models.plex_payment import (
    PlexPaymentRequirement,
    PlexPaymentStatus,
)
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from app.repositories.plex_payment_repository import PlexPaymentRepository
from app.services.blockchain_service import get_blockchain_service


class PlexPaymentOperations:
    """PLEX payment operations mixin.

    Handles payment requirements, verification, and processing.
    """

    # These attributes should be provided by the parent class
    _session: AsyncSession
    _plex_repo: PlexPaymentRepository

    async def create_payment_requirement(
        self,
        user_id: int,
        deposit_id: int,
        deposit_amount: Decimal,
        deposit_created_at: datetime,
    ) -> PlexPaymentRequirement:
        """Create PLEX payment requirement for a new deposit.

        Args:
            user_id: User ID
            deposit_id: Deposit ID
            deposit_amount: Deposit amount in USD
            deposit_created_at: When deposit was created

        Returns:
            Created PlexPaymentRequirement
        """
        daily_plex = deposit_amount * Decimal(
            str(PLEX_PER_DOLLAR_DAILY)
        )

        return await self._plex_repo.create(
            user_id=user_id,
            deposit_id=deposit_id,
            daily_plex_required=daily_plex,
            deposit_created_at=deposit_created_at,
        )

    async def get_user_payment_status(self, user_id: int) -> dict:
        """Get comprehensive payment status for user.

        Args:
            user_id: User ID

        Returns:
            Dict with payment status details
        """
        payments = await self._plex_repo.get_active_by_user_id(user_id)

        settings_repo = GlobalSettingsRepository(self._session)
        project_start_at = await settings_repo.get_project_start_at()

        total_daily_required = Decimal("0")
        overdue_count = 0
        warning_count = 0
        blocked_count = 0

        # New fields for strict debt logic
        total_historical_debt = Decimal("0")
        deposits_with_debt = 0
        missing_recent_payment = 0

        payment_details = []
        now = datetime.now(UTC)

        for payment in payments:
            daily_required = (
                payment.daily_plex_required or Decimal("0")
            )
            total_daily_required += daily_required

            # Legacy status counters (for monitoring/UI)
            if payment.status == PlexPaymentStatus.WARNING_SENT:
                warning_count += 1
            elif payment.status == PlexPaymentStatus.BLOCKED:
                blocked_count += 1
            elif payment.is_payment_overdue():
                overdue_count += 1

            # --- Historical debt calculation ---
            # Base point: max(project_start_at, deposit_created_at)
            # to avoid retro-debt before launch
            deposit_created_at = (
                getattr(payment.deposit, "created_at", None)
                or payment.created_at
            )
            if (
                deposit_created_at
                and deposit_created_at.tzinfo is None
            ):
                deposit_created_at = deposit_created_at.replace(
                    tzinfo=UTC
                )
            base_start = project_start_at
            if (
                deposit_created_at
                and deposit_created_at > base_start
            ):
                base_start = deposit_created_at

            if daily_required > 0 and base_start:
                delta_days = (
                    now - base_start
                ).total_seconds() / 86400
                # At least 1 day of obligation once deposit exists
                days_expected = int(delta_days) + 1
                if days_expected < 1:
                    days_expected = 1

                required_total = daily_required * Decimal(
                    days_expected
                )
                paid_total = payment.total_plex_paid or Decimal("0")
                debt = required_total - paid_total

                if debt > 0:
                    total_historical_debt += debt
                    deposits_with_debt += 1

            # --- Last 24h payment check ---
            if not payment.last_payment_at or (
                now - payment.last_payment_at
            ).total_seconds() > 86400:
                missing_recent_payment += 1

            payment_details.append(
                {
                    "deposit_id": payment.deposit_id,
                    "daily_required": daily_required,
                    "status": payment.status,
                    "next_due": payment.next_payment_due,
                    "is_overdue": payment.is_payment_overdue(),
                    "total_paid": payment.total_plex_paid,
                    "last_payment_at": payment.last_payment_at,
                }
            )

        has_debt = total_historical_debt > 0
        has_recent_issue = missing_recent_payment > 0

        return {
            "total_daily_plex": total_daily_required,
            "active_deposits": len(payments),
            "overdue_count": overdue_count,
            "warning_count": warning_count,
            "blocked_count": blocked_count,
            "historical_debt_plex": total_historical_debt,
            "deposits_with_debt": deposits_with_debt,
            "missing_recent_payment_count": missing_recent_payment,
            # Withdrawal must be blocked if debt OR no payment in 24h
            "has_debt": has_debt,
            "has_recent_issue": has_recent_issue,
            # has_issues means payment debts exist,
            # not just missing transactions in last 24 hours.
            "has_issues": has_debt,
            "payment_details": payment_details,
        }

    async def verify_daily_payment(
        self,
        user_id: int,
        sender_wallet: str,
    ) -> dict:
        """Verify PLEX payment from user's wallet to system wallet.

        Checks recent transfers from sender to system wallet.

        Args:
            user_id: User ID
            sender_wallet: User's wallet address

        Returns:
            Dict with verification result
        """
        blockchain = get_blockchain_service()

        # Get required amount for user's deposits
        required = await self._plex_repo.get_total_daily_plex_required(
            user_id
        )

        # Check for PLEX transfers to system wallet
        # lookback_blocks=200 covers ~10 minutes on BSC (3 sec/block)
        # Pass Decimal directly to avoid float precision issues
        result = await blockchain.verify_plex_payment(
            sender_address=sender_wallet,
            amount_plex=required,  # Decimal - converted safely
            lookback_blocks=200,
        )

        if not result.get("success"):
            return {
                "success": False,
                "error": "Payment not found",
            }

        # Check if received amount is sufficient
        received = Decimal(str(result.get("amount", 0)))

        if received < required:
            error_msg = (
                f"Insufficient payment: received {received} PLEX, "
                f"required {required} PLEX"
            )
            return {
                "success": False,
                "error": error_msg,
                "received": received,
                "required": required,
            }

        return {
            "success": True,
            "tx_hash": result.get("tx_hash"),
            "amount": received,
            "required": required,
        }

    async def process_payment_for_deposit(
        self,
        deposit_id: int,
        tx_hash: str,
        amount: Decimal,
    ) -> PlexPaymentRequirement | None:
        """Process confirmed PLEX payment for a deposit.

        Args:
            deposit_id: Deposit ID
            tx_hash: Transaction hash
            amount: Amount paid

        Returns:
            Updated payment requirement or None
        """
        payment = await self._plex_repo.get_by_deposit_id(deposit_id)
        if not payment:
            logger.warning(
                f"No payment requirement for deposit {deposit_id}"
            )
            return None

        return await self._plex_repo.mark_paid(
            payment.id, tx_hash, amount
        )
