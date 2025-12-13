"""
Initialize PLEX payment requirements for existing deposits.

This script creates PlexPaymentRequirement records for all confirmed deposits
that don't have them yet.
"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy import select

from app.config.business_constants import PLEX_PER_DOLLAR_DAILY
from app.config.database import async_session_maker
from app.models.deposit import Deposit
from app.models.plex_payment import PlexPaymentRequirement


async def init_plex_requirements():
    """Create PLEX payment requirements for existing deposits."""
    async with async_session_maker() as session:
        # Get all confirmed deposits without PLEX requirements
        stmt = (
            select(Deposit)
            .outerjoin(PlexPaymentRequirement, Deposit.id == PlexPaymentRequirement.deposit_id)
            .where(Deposit.status == "confirmed", PlexPaymentRequirement.id.is_(None))
        )
        result = await session.execute(stmt)
        deposits = result.scalars().all()

        logger.info(f"Found {len(deposits)} deposits without PLEX requirements")

        created_count = 0
        for deposit in deposits:
            try:
                daily_plex = deposit.amount * Decimal(str(PLEX_PER_DOLLAR_DAILY))
                now = datetime.now(UTC)

                # Calculate due times
                next_payment_due = now  # Already due
                warning_due = now  # Already due (24h passed since deposit)
                block_due = now  # Already due (48h passed since deposit)

                plex_req = PlexPaymentRequirement(
                    user_id=deposit.user_id,
                    deposit_id=deposit.id,
                    daily_plex_required=daily_plex,
                    next_payment_due=next_payment_due,
                    warning_due=warning_due,
                    block_due=block_due,
                    status="active",
                    total_plex_paid=Decimal("0"),
                    days_paid=0,
                    consecutive_days_paid=0,
                    warning_count=0,
                    is_work_active=True,
                    created_at=now,
                    updated_at=now,
                )
                session.add(plex_req)
                created_count += 1
                logger.info(
                    f"Created PLEX requirement for deposit {deposit.id}: {daily_plex} PLEX/day (user {deposit.user_id})"
                )
            except Exception as e:
                logger.error(f"Failed to create PLEX requirement for deposit {deposit.id}: {e}")

        await session.commit()
        logger.success(f"Created {created_count} PLEX payment requirements")


if __name__ == "__main__":
    asyncio.run(init_plex_requirements())
