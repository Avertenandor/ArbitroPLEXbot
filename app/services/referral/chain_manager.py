"""
Referral chain management module.

Handles referral chain operations including chain retrieval and relationship creation.
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.referral_repository import ReferralRepository
from app.services.referral.config import REFERRAL_DEPTH


class ReferralChainManager:
    """Manages referral chain operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize chain manager."""
        self.session = session
        self.referral_repo = ReferralRepository(session)

    async def get_referral_chain(
        self, user_id: int, depth: int = REFERRAL_DEPTH
    ) -> list[User]:
        """
        Get referral chain (PostgreSQL CTE optimized).

        Uses recursive CTE to efficiently fetch entire referral chain.

        Args:
            user_id: User ID
            depth: Chain depth to retrieve

        Returns:
            List of users from direct referrer to Nth level
        """
        # Use PostgreSQL recursive CTE for efficient chain retrieval
        query = text("""
            WITH RECURSIVE referral_chain AS (
                -- Base case: start with the user
                SELECT
                    u.id,
                    u.telegram_id,
                    u.username,
                    u.wallet_address,
                    u.referrer_id,
                    u.created_at,
                    u.updated_at,
                    u.is_verified,
                    u.earnings_blocked,
                    u.financial_password,
                    0 AS level
                FROM users u
                WHERE u.id = :user_id

                UNION ALL

                -- Recursive case: get referrer of previous level
                SELECT
                    u.id,
                    u.telegram_id,
                    u.username,
                    u.wallet_address,
                    u.referrer_id,
                    u.created_at,
                    u.updated_at,
                    u.is_verified,
                    u.earnings_blocked,
                    u.financial_password,
                    rc.level + 1 AS level
                FROM users u
                INNER JOIN referral_chain rc ON u.id = rc.referrer_id
                WHERE rc.level < :depth
            )
            SELECT *
            FROM referral_chain
            WHERE level > 0
            ORDER BY level ASC
        """)

        result = await self.session.execute(
            query, {"user_id": user_id, "depth": depth}
        )
        rows = result.all()

        # Map rows to User objects
        chain = []
        for row in rows:
            user = User(
                id=row.id,
                telegram_id=row.telegram_id,
                username=row.username,
                wallet_address=row.wallet_address,
                referrer_id=row.referrer_id,
                is_verified=row.is_verified,
                earnings_blocked=row.earnings_blocked,
                financial_password=row.financial_password,
            )
            user.created_at = row.created_at
            user.updated_at = row.updated_at
            chain.append(user)

        logger.debug(
            "Referral chain retrieved",
            extra={
                "user_id": user_id,
                "depth": depth,
                "chain_length": len(chain)
            },
        )

        return chain

    async def create_referral_relationships(
        self, new_user_id: int, direct_referrer_id: int
    ) -> tuple[bool, str | None]:
        """
        Create referral relationships for new user.

        Creates multi-level referral chain (up to REFERRAL_DEPTH levels).

        Args:
            new_user_id: New user ID
            direct_referrer_id: Direct referrer ID

        Returns:
            Tuple of (success, error_message)
        """
        # Self-referral check
        if new_user_id == direct_referrer_id:
            return False, "Нельзя пригласить самого себя"

        # Get direct referrer
        stmt = select(User).where(User.id == direct_referrer_id)
        result = await self.session.execute(stmt)
        direct_referrer = result.scalar_one_or_none()

        if not direct_referrer:
            return False, "Реферер не найден"

        # Get referral chain from direct referrer
        referrers = await self.get_referral_chain(
            direct_referrer_id, REFERRAL_DEPTH
        )

        # Add direct referrer as level 1
        referrers.insert(0, direct_referrer)

        # Check for referral loops
        referrer_ids = [r.id for r in referrers]
        if new_user_id in referrer_ids:
            logger.warning(
                "Referral loop detected",
                extra={
                    "new_user_id": new_user_id,
                    "direct_referrer_id": direct_referrer_id,
                    "chain_ids": referrer_ids,
                },
            )
            return False, "Нельзя создать циклическую реферальную цепочку"

        # Create referral records for each level
        for i, referrer in enumerate(referrers[: REFERRAL_DEPTH]):
            level = i + 1

            # Check if relationship already exists
            existing = await self.referral_repo.find_by(
                referrer_id=referrer.id, referral_id=new_user_id
            )

            if not existing:
                await self.referral_repo.create(
                    referrer_id=referrer.id,
                    referral_id=new_user_id,
                    level=level,
                    total_earned=Decimal("0"),
                )

                logger.debug(
                    "Referral relationship created",
                    extra={
                        "referrer_id": referrer.id,
                        "referral_id": new_user_id,
                        "level": level,
                    },
                )

        await self.session.commit()

        logger.info(
            "Referral chain created",
            extra={
                "new_user_id": new_user_id,
                "direct_referrer_id": direct_referrer_id,
                "levels_created": min(len(referrers), REFERRAL_DEPTH),
            },
        )

        return True, None
