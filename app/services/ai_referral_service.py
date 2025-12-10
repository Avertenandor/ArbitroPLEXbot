"""
AI Referral Service.

Provides referral statistics for AI assistant:
- Platform-wide referral stats
- User referrals list
- Top referrers
"""

from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.repositories.user_repository import UserRepository


class AIReferralService:
    """
    AI-powered referral statistics service.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.user_repo = UserRepository(session)

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials."""
        if not self.admin_telegram_id:
            return None, "❌ Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin or admin.is_blocked:
            return None, "❌ Администратор не найден или заблокирован"

        return admin, None

    async def _find_user(self, identifier: str) -> tuple[User | None, str | None]:
        """Find user by @username or telegram_id."""
        identifier = identifier.strip()

        if identifier.startswith("@"):
            username = identifier[1:]
            user = await self.user_repo.get_by_username(username)
            if user:
                return user, None
            return None, f"❌ Пользователь @{username} не найден"

        if identifier.isdigit():
            telegram_id = int(identifier)
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if user:
                return user, None
            return None, f"❌ Пользователь с ID {telegram_id} не найден"

        return None, "❌ Укажите @username или telegram_id"

    async def get_platform_referral_stats(self) -> dict[str, Any]:
        """
        Get platform-wide referral statistics.
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Users with referrals
        with_refs_stmt = select(func.count(User.id)).where(
            User.referral_count > 0
        )
        with_refs_result = await self.session.execute(with_refs_stmt)
        users_with_refs = with_refs_result.scalar() or 0

        # Total referrals
        total_refs_stmt = select(func.sum(User.referral_count))
        total_refs_result = await self.session.execute(total_refs_stmt)
        total_refs = total_refs_result.scalar() or 0

        # Users who came via referral (have referrer_id)
        referred_stmt = select(func.count(User.id)).where(
            User.referrer_id.isnot(None)
        )
        referred_result = await self.session.execute(referred_stmt)
        referred_users = referred_result.scalar() or 0

        # Total referral earnings
        earnings_stmt = select(func.sum(User.referral_earnings))
        earnings_result = await self.session.execute(earnings_stmt)
        total_earnings = earnings_result.scalar() or Decimal("0")

        return {
            "success": True,
            "stats": {
                "users_with_referrals": users_with_refs,
                "total_referrals": int(total_refs),
                "referred_users": referred_users,
                "total_earnings": float(total_earnings),
            },
            "message": "👥 Реферальная статистика платформы"
        }

    async def get_user_referrals(
        self,
        user_identifier: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Get referrals for a specific user.
        
        Args:
            user_identifier: @username or telegram_id
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        # Get referrals (users with this user as referrer)
        stmt = select(User).where(
            User.referrer_id == user.id
        ).order_by(User.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        referrals = list(result.scalars().all())

        referrals_list = []
        for ref in referrals:
            referrals_list.append({
                "id": ref.id,
                "username": f"@{ref.username}" if ref.username else None,
                "telegram_id": ref.telegram_id,
                "first_name": ref.first_name,
                "total_deposited": float(ref.total_deposited_usdt or 0),
                "is_active": ref.is_active_depositor,
                "created": ref.created_at.strftime("%d.%m.%Y") if ref.created_at else None,
            })

        return {
            "success": True,
            "user": f"@{user.username}" if user.username else f"ID:{user.telegram_id}",
            "referral_count": user.referral_count or 0,
            "referral_earnings": float(user.referral_earnings or 0),
            "referrals": referrals_list,
            "message": "👥 Рефералы пользователя"
        }

    async def get_top_referrers(self, limit: int = 20) -> dict[str, Any]:
        """
        Get top referrers by referral count.
        
        Args:
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        stmt = select(User).where(
            User.referral_count > 0
        ).order_by(User.referral_count.desc()).limit(limit)

        result = await self.session.execute(stmt)
        top_users = list(result.scalars().all())

        if not top_users:
            return {
                "success": True,
                "count": 0,
                "top_referrers": [],
                "message": "ℹ️ Нет пользователей с рефералами"
            }

        top_list = []
        for i, user in enumerate(top_users, 1):
            top_list.append({
                "rank": i,
                "username": f"@{user.username}" if user.username else f"ID:{user.telegram_id}",
                "referral_count": user.referral_count or 0,
                "referral_earnings": float(user.referral_earnings or 0),
                "total_deposited": float(user.total_deposited_usdt or 0),
            })

        return {
            "success": True,
            "count": len(top_list),
            "top_referrers": top_list,
            "message": "🏆 Топ рефереров"
        }

    async def get_top_earners(self, limit: int = 20) -> dict[str, Any]:
        """
        Get top referrers by earnings.
        
        Args:
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        stmt = select(User).where(
            User.referral_earnings > 0
        ).order_by(User.referral_earnings.desc()).limit(limit)

        result = await self.session.execute(stmt)
        top_users = list(result.scalars().all())

        if not top_users:
            return {
                "success": True,
                "count": 0,
                "top_earners": [],
                "message": "ℹ️ Нет пользователей с реферальным заработком"
            }

        top_list = []
        for i, user in enumerate(top_users, 1):
            top_list.append({
                "rank": i,
                "username": f"@{user.username}" if user.username else f"ID:{user.telegram_id}",
                "referral_earnings": float(user.referral_earnings or 0),
                "referral_count": user.referral_count or 0,
            })

        return {
            "success": True,
            "count": len(top_list),
            "top_earners": top_list,
            "message": "💰 Топ по реферальному заработку"
        }
