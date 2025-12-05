"""
Referral query management module.

Handles querying referrals and referral relationships.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.referral import Referral
from app.repositories.referral_repository import ReferralRepository


class ReferralQueryManager:
    """Manages referral query operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize query manager."""
        self.session = session
        self.referral_repo = ReferralRepository(session)

    async def get_referrals_by_level(
        self, user_id: int, level: int, page: int = 1, limit: int = 10
    ) -> dict:
        """
        Get user's referrals by level.

        Args:
            user_id: User ID
            level: Referral level (1-3)
            page: Page number
            limit: Items per page

        Returns:
            Dict with referrals, total, page, pages
        """
        offset = (page - 1) * limit

        # Get referrals with pagination, eager load referral users to avoid N+1
        stmt = (
            select(Referral)
            .options(selectinload(Referral.referral))
            .where(Referral.referrer_id == user_id, Referral.level == level)
            .order_by(Referral.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        relationships = list(result.scalars().all())

        # Get total count using SQL COUNT (avoid loading all records)
        count_stmt = select(func.count(Referral.id)).where(
            Referral.referrer_id == user_id, Referral.level == level
        )
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        # Build referrals list (users already loaded via eager loading)
        referrals = []
        for rel in relationships:
            user = rel.referral  # Already loaded via selectinload

            if user:
                referrals.append({
                    "user": user,
                    "earned": rel.total_earned,
                    "joined_at": rel.created_at,
                })

        pages = (total + limit - 1) // limit

        return {
            "referrals": referrals,
            "total": total,
            "page": page,
            "pages": pages,
        }

    async def get_my_referrers(self, user_id: int) -> dict:
        """
        Get who invited this user (their referrer chain).

        Shows the user's position in the referral structure.

        Args:
            user_id: User ID

        Returns:
            Dict with referrer info
        """
        # Get all relationships where this user is the referral
        stmt = (
            select(Referral)
            .options(selectinload(Referral.referrer))
            .where(Referral.referral_id == user_id)
            .order_by(Referral.level)
        )

        result = await self.session.execute(stmt)
        relationships = list(result.scalars().all())

        if not relationships:
            return {
                "has_referrer": False,
                "referrers": [],
                "direct_referrer": None,
            }

        referrers = []
        direct_referrer = None

        for rel in relationships:
            referrer_user = rel.referrer
            if referrer_user:
                referrer_info = {
                    "level": rel.level,
                    "user_id": referrer_user.id,
                    "telegram_id": referrer_user.telegram_id,
                    "username": referrer_user.username,
                    "you_earned_them": rel.total_earned,
                }
                referrers.append(referrer_info)

                if rel.level == 1:
                    direct_referrer = referrer_info

        return {
            "has_referrer": bool(direct_referrer),
            "referrers": referrers,
            "direct_referrer": direct_referrer,
        }
