"""
AI Users Service - User profile operations.
"""
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.ai.commons import find_user_by_identifier, verify_admin


class ProfileMixin:
    """Mixin for user profile operations."""

    session: AsyncSession
    admin_telegram_id: int | None
    user_repo: UserRepository

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        return await verify_admin(self.session, self.admin_telegram_id)

    async def _find_user(self, identifier: str) -> tuple[User | None, str | None]:
        return await find_user_by_identifier(self.session, identifier, self.user_repo)

    async def get_user_profile(self, user_identifier: str) -> dict[str, Any]:
        """Get detailed user profile."""
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        balance = getattr(user, 'balance', Decimal("0")) or Decimal("0")
        bonus_balance = getattr(user, 'bonus_balance', Decimal("0")) or Decimal("0")
        bonus_roi = getattr(user, 'bonus_roi_earned', Decimal("0")) or Decimal("0")

        # Total earnings
        tx_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user.id,
            Transaction.type == TransactionType.DEPOSIT_REWARD.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
        )
        total_earnings = (await self.session.execute(tx_stmt)).scalar() or Decimal("0")

        # Pending withdrawals
        pending_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user.id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.PENDING.value,
        )
        pending_withdrawals = (await self.session.execute(pending_stmt)).scalar() or Decimal("0")

        # Completed withdrawals
        completed_stmt = select(func.sum(Transaction.amount)).where(
            Transaction.user_id == user.id,
            Transaction.type == TransactionType.WITHDRAWAL.value,
            Transaction.status == TransactionStatus.CONFIRMED.value,
        )
        total_withdrawals = (await self.session.execute(completed_stmt)).scalar() or Decimal("0")

        # PLEX calculation
        total_investment = user.total_deposited_usdt + bonus_balance
        plex_daily = int(total_investment * 10)
        plex_balance = getattr(user, 'plex_balance', 0) or 0

        return {
            "success": True,
            "user": {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": f"@{user.username}" if user.username else None,
                "phone": getattr(user, 'phone', None),
                "email": getattr(user, 'email', None),
                "wallet": user.masked_wallet if user.wallet_address else None,
                "is_banned": user.is_banned,
                "created_at": (
                    user.created_at.strftime("%d.%m.%Y %H:%M")
                    if user.created_at else None
                ),
            },
            "finances": {
                "balance": float(balance),
                "deposit_usdt": float(user.total_deposited_usdt),
                "bonus_balance": float(bonus_balance),
                "bonus_roi": float(bonus_roi),
                "total_earnings": float(total_earnings),
                "pending_withdrawals": float(pending_withdrawals),
                "total_withdrawals": float(total_withdrawals),
            },
            "plex": {
                "balance": plex_balance,
                "daily_required": plex_daily,
                "days_remaining": int(plex_balance / plex_daily) if plex_daily > 0 else 0,
            },
            "activity": {
                "is_active_depositor": user.is_active_depositor,
                "deposit_tx_count": user.deposit_tx_count,
                "last_deposit_scan": (
                    user.last_deposit_scan_at.strftime("%d.%m.%Y %H:%M")
                    if user.last_deposit_scan_at else None
                ),
            },
        }
