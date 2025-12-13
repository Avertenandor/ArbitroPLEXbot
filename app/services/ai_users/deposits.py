"""
AI Users Service - User deposits and statistics.
"""
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bonus_credit import BonusCredit
from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.ai.commons import find_user_by_identifier, verify_admin
from app.utils.formatters import format_user_identifier


class DepositsMixin:
    """Mixin for user deposits and statistics operations."""

    session: AsyncSession
    admin_telegram_id: int | None
    user_repo: UserRepository

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        return await verify_admin(self.session, self.admin_telegram_id)

    async def _find_user(self, identifier: str) -> tuple[User | None, str | None]:
        return await find_user_by_identifier(self.session, identifier, self.user_repo)

    async def get_user_deposits(self, user_identifier: str) -> dict[str, Any]:
        """Get user's deposits and bonuses."""
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        # Get blockchain deposits
        deposit_stmt = select(Deposit).where(
            Deposit.user_id == user.id
        ).order_by(Deposit.created_at.desc())
        deposits = list((await self.session.execute(deposit_stmt)).scalars().all())

        deposits_list = [{
            "id": d.id,
            "level": d.level,
            "amount": float(d.amount),
            "status": d.status,
            "created": d.created_at.strftime("%d.%m.%Y") if d.created_at else None,
        } for d in deposits]

        # Get bonus credits
        bonus_stmt = select(BonusCredit).where(
            BonusCredit.user_id == user.id
        ).order_by(BonusCredit.created_at.desc())
        bonuses = list((await self.session.execute(bonus_stmt)).scalars().all())

        bonuses_list = [{
            "id": b.id,
            "amount": float(b.amount),
            "roi_paid": float(b.roi_paid_amount or 0),
            "roi_cap": float(b.roi_cap_amount or 0),
            "is_active": b.is_active,
            "reason": b.reason,
            "created": b.created_at.strftime("%d.%m.%Y") if b.created_at else None,
        } for b in bonuses]

        total_deposits = sum(
            d.amount for d in deposits if d.status == TransactionStatus.CONFIRMED.value
        )
        total_bonuses = sum(b.amount for b in bonuses if b.is_active)

        return {
            "success": True,
            "user": format_user_identifier(user),
            "summary": {
                "total_deposits": float(total_deposits),
                "total_bonuses": float(total_bonuses),
                "total_investment": float(total_deposits + total_bonuses),
                "plex_daily": int((total_deposits + total_bonuses) * 10),
            },
            "deposits": deposits_list,
            "bonuses": bonuses_list,
            "message": f"📊 Депозиты пользователя @{user.username or user.telegram_id}"
        }

    async def get_users_stats(self) -> dict[str, Any]:
        """Get overall users statistics."""
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Total users
        total_users = (await self.session.execute(
            select(func.count(User.id))
        )).scalar() or 0

        # Verified users (with wallet)
        verified_users = (await self.session.execute(
            select(func.count(User.id)).where(User.wallet_address.isnot(None))
        )).scalar() or 0

        # Active depositors
        active_depositors = (await self.session.execute(
            select(func.count(User.id)).where(User.total_deposited_usdt >= 30)
        )).scalar() or 0

        # Banned users
        banned_users = (await self.session.execute(
            select(func.count(User.id)).where(User.is_banned == True)
        )).scalar() or 0

        # Total deposits
        total_deposits = (await self.session.execute(
            select(func.sum(User.total_deposited_usdt))
        )).scalar() or Decimal("0")

        # Total bonuses
        total_bonuses = (await self.session.execute(
            select(func.sum(User.bonus_balance)).where(User.bonus_balance > 0)
        )).scalar() or Decimal("0")

        # Users with bonuses
        users_with_bonus = (await self.session.execute(
            select(func.count(User.id)).where(User.bonus_balance > 0)
        )).scalar() or 0

        return {
            "success": True,
            "stats": {
                "total_users": total_users,
                "verified_users": verified_users,
                "active_depositors": active_depositors,
                "banned_users": banned_users,
                "users_with_bonus": users_with_bonus,
            },
            "finances": {
                "total_deposits": float(total_deposits),
                "total_bonuses": float(total_bonuses),
                "total_investment": float(total_deposits + total_bonuses),
            },
            "message": "📊 Статистика пользователей"
        }
