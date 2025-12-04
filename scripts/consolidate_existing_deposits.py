"""
Script to consolidate existing user deposits into single deposits.

This script should be run ONCE after the 20251203_000003 migration.

For each user with deposits:
1. Sum all confirmed USDT deposits
2. Create one consolidated deposit with total amount
3. Mark old deposits as archived (status = 'consolidated')
4. Create PLEX payment requirement for consolidated deposit

Usage:
    python scripts/consolidate_existing_deposits.py
"""

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.models.deposit import Deposit
from app.models.plex_payment import PlexPaymentRequirement
from app.models.user import User
from bot.constants.rules import PLEX_PER_DOLLAR_DAILY


async def consolidate_user_deposits(
    session: AsyncSession,
    user: User,
) -> dict:
    """
    Consolidate all deposits for a single user.

    Args:
        session: Database session
        user: User to consolidate deposits for

    Returns:
        Dict with consolidation results
    """
    # Get all confirmed deposits for user
    result = await session.execute(
        select(Deposit).where(
            Deposit.user_id == user.id,
            Deposit.status == "confirmed",
            not Deposit.is_consolidated,
        )
    )
    deposits = list(result.scalars().all())

    if not deposits:
        return {
            "user_id": user.id,
            "status": "skipped",
            "reason": "no deposits to consolidate",
        }

    # Calculate totals
    total_amount = sum(d.amount for d in deposits)
    total_roi_cap = sum(d.roi_cap_amount for d in deposits)
    total_roi_paid = sum(d.roi_paid_amount for d in deposits)
    tx_hashes = [d.tx_hash for d in deposits if d.tx_hash]

    logger.info(
        f"Consolidating {len(deposits)} deposits for user {user.id}: "
        f"total={total_amount} USDT"
    )

    # Create consolidated deposit
    now = datetime.now(UTC)
    consolidated_deposit = Deposit(
        user_id=user.id,
        level=1,  # Consolidated deposits are level 1
        amount=total_amount,
        tx_hash=None,  # No single tx hash
        block_number=None,
        wallet_address=user.wallet_address,
        status="confirmed",
        deposit_version_id=None,  # No version for consolidated
        roi_cap_amount=total_roi_cap,
        roi_paid_amount=total_roi_paid,
        is_roi_completed=total_roi_paid >= total_roi_cap,
        created_at=now,
        confirmed_at=now,
        is_consolidated=True,
        consolidated_at=now,
        consolidated_tx_hashes=tx_hashes,
        plex_cycle_start=now,  # Start 24h cycle from now
    )
    session.add(consolidated_deposit)
    await session.flush()

    # Create PLEX payment requirement for consolidated deposit
    daily_plex = total_amount * Decimal(str(PLEX_PER_DOLLAR_DAILY))

    plex_payment = PlexPaymentRequirement(
        user_id=user.id,
        deposit_id=consolidated_deposit.id,
        daily_plex_required=daily_plex,
        next_payment_due=now,  # Due immediately (needs to pay first)
        warning_due=now,  # Warning if not paid
        block_due=now,  # Will block if not paid
        status="active",
        is_work_active=False,  # Not active until first payment
    )
    session.add(plex_payment)

    # Archive old deposits by setting status to 'consolidated'
    deposit_ids = [d.id for d in deposits]
    for deposit in deposits:
        deposit.status = "consolidated"

    # Delete old PLEX payment requirements for these deposits
    stmt = delete(PlexPaymentRequirement).where(
        PlexPaymentRequirement.deposit_id.in_(deposit_ids)
    )
    await session.execute(stmt)

    # Update user
    user.deposits_consolidated = True
    user.total_deposited_usdt = total_amount

    await session.flush()

    return {
        "user_id": user.id,
        "status": "success",
        "deposits_consolidated": len(deposits),
        "total_amount": float(total_amount),
        "consolidated_deposit_id": consolidated_deposit.id,
        "daily_plex_required": float(daily_plex),
    }


async def run_consolidation() -> None:
    """Run the consolidation process for all users."""
    logger.info("Starting deposit consolidation...")

    # Create database connection
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )

    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    results = {
        "total_users": 0,
        "consolidated": 0,
        "skipped": 0,
        "errors": 0,
        "details": [],
    }

    try:
        async with session_maker() as session:
            # Get all users who haven't been consolidated yet
            result = await session.execute(
                select(User).where(
                    not User.deposits_consolidated,
                    User.is_active,
                )
            )
            users = list(result.scalars().all())

            results["total_users"] = len(users)
            logger.info(f"Found {len(users)} users to process")

            for user in users:
                try:
                    consolidation_result = await consolidate_user_deposits(
                        session, user
                    )
                    results["details"].append(consolidation_result)

                    if consolidation_result["status"] == "success":
                        results["consolidated"] += 1
                    else:
                        results["skipped"] += 1

                except Exception as e:
                    logger.error(
                        f"Error consolidating deposits for user {user.id}: {e}"
                    )
                    results["errors"] += 1
                    results["details"].append({
                        "user_id": user.id,
                        "status": "error",
                        "error": str(e),
                    })

            # Commit all changes
            await session.commit()

    except Exception as e:
        await session.rollback()
        logger.exception(f"Consolidation failed: {e}")
        raise
    finally:
        await engine.dispose()

    # Print summary
    logger.info("=" * 50)
    logger.info("CONSOLIDATION COMPLETE")
    logger.info("=" * 50)
    logger.info(f"Total users processed: {results['total_users']}")
    logger.info(f"Consolidated: {results['consolidated']}")
    logger.info(f"Skipped: {results['skipped']}")
    logger.info(f"Errors: {results['errors']}")
    logger.info("=" * 50)

    # Print details for consolidated users
    for detail in results["details"]:
        if detail["status"] == "success":
            logger.info(
                f"User {detail['user_id']}: "
                f"consolidated {detail['deposits_consolidated']} deposits, "
                f"total {detail['total_amount']} USDT, "
                f"daily PLEX: {detail['daily_plex_required']}"
            )


if __name__ == "__main__":
    asyncio.run(run_consolidation())
