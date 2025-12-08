"""
User statistics functionality.

Handles user statistics, balance calculations, and reporting.
"""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository


class UserStatisticsMixin:
    """
    Mixin for user statistics functionality.

    Provides methods for retrieving user statistics and balance information.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize user statistics mixin."""
        self.session = session
        self.user_repo = UserRepository(session)

    async def get_user_stats(self, user_id: int) -> dict:
        """
        Get user statistics.

        Args:
            user_id: User ID

        Returns:
            User stats dict
        """
        from app.models.enums import TransactionStatus
        from app.repositories.deposit_repository import DepositRepository
        from app.repositories.referral_repository import ReferralRepository

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {}

        # Get deposits total from confirmed deposits
        deposit_repo = DepositRepository(self.session)
        total_deposits = await deposit_repo.get_total_deposited(user_id)

        # Also check user.total_deposited_usdt as fallback
        user_total = getattr(user, "total_deposited_usdt", None) or Decimal("0")
        if user_total > total_deposits:
            total_deposits = user_total

        # Get referral count
        referral_repo = ReferralRepository(self.session)
        referrals = await referral_repo.get_by_referrer(user_id, level=1)
        referral_count = len(referrals) if referrals else 0

        # Get activated levels from confirmed deposits
        deposits = await deposit_repo.find_by(
            user_id=user_id,
            status=TransactionStatus.CONFIRMED.value,
        )
        activated_levels = list({d.level for d in deposits}) if deposits else []

        return {
            "total_deposits": total_deposits,
            "referral_count": referral_count,
            "activated_levels": activated_levels,
        }

    async def get_user_balance(self, user_id: int) -> dict:
        """
        Get user balance with detailed statistics.

        Args:
            user_id: User ID

        Returns:
            Balance dict with all statistics
        """
        from app.models.enums import TransactionStatus, TransactionType
        from app.repositories.deposit_repository import DepositRepository
        from app.repositories.transaction_repository import (
            TransactionRepository,
        )

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {
                "available_balance": Decimal("0.00"),
                "total_balance": Decimal("0.00"),
                "total_earned": Decimal("0.00"),
                "pending_earnings": Decimal("0.00"),
                "pending_withdrawals": Decimal("0.00"),
                "total_deposits": Decimal("0.00"),
                "total_withdrawals": Decimal("0.00"),
                "total_earnings": Decimal("0.00"),
            }

        # Get deposits total
        deposit_repo = DepositRepository(self.session)
        total_deposits = await deposit_repo.get_total_deposited(user_id)

        # Get withdrawals total
        transaction_repo = TransactionRepository(self.session)
        withdrawals = await transaction_repo.get_by_user(
            user_id=user_id,
            type=TransactionType.WITHDRAWAL.value,
            status=TransactionStatus.CONFIRMED.value,
        )
        total_withdrawals = (
            sum(w.amount for w in withdrawals)
            if withdrawals else Decimal("0.00")
        )

        # Get pending withdrawals
        pending_withdrawals_list = await transaction_repo.get_by_user(
            user_id=user_id,
            type=TransactionType.WITHDRAWAL.value,
            status=TransactionStatus.PENDING.value,
        )
        pending_withdrawals = (
            sum(w.amount for w in pending_withdrawals_list)
            if pending_withdrawals_list else Decimal("0.00")
        )

        # Get earnings (deposit rewards + referral earnings)
        earnings_transactions = await transaction_repo.get_by_user(
            user_id=user_id,
            type=TransactionType.DEPOSIT_REWARD.value,
            status=TransactionStatus.CONFIRMED.value,
        )
        total_earnings = (
            sum(e.amount for e in earnings_transactions)
            if earnings_transactions else Decimal("0.00")
        )

        # Add referral earnings if any
        referral_earnings = await transaction_repo.get_by_user(
            user_id=user_id,
            type=TransactionType.REFERRAL_REWARD.value,
            status=TransactionStatus.CONFIRMED.value,
        )
        if referral_earnings:
            total_earnings += sum(e.amount for e in referral_earnings)

        # Calculate total balance (available + pending earnings)
        available_balance = getattr(user, "balance", Decimal("0.00"))
        pending_earnings = getattr(user, "pending_earnings", Decimal("0.00"))
        total_balance = available_balance + pending_earnings

        # Get bonus balance info
        bonus_balance = getattr(user, "bonus_balance", Decimal("0.00")) or Decimal("0.00")
        bonus_roi_earned = getattr(user, "bonus_roi_earned", Decimal("0.00")) or Decimal("0.00")

        return {
            "available_balance": available_balance,
            "total_balance": total_balance,
            "total_earned": getattr(user, "total_earned", Decimal("0.00")),
            "pending_earnings": pending_earnings,
            "pending_withdrawals": pending_withdrawals,
            "total_deposits": total_deposits,
            "total_withdrawals": total_withdrawals,
            "total_earnings": total_earnings,
            "bonus_balance": bonus_balance,
            "bonus_roi_earned": bonus_roi_earned,
        }
