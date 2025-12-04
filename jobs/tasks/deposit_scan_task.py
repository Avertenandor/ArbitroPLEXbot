"""
Deposit Scan Task.

Periodically scans blockchain for user deposits (USDT transfers to system wallet).
Runs every hour via scheduler.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import dramatiq
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.models.user import User
from app.services.deposit_scan_service import DepositScanService


@dramatiq.actor(max_retries=2, time_limit=600_000)  # 10 min timeout
def scan_all_user_deposits() -> None:
    """
    Scan deposits for all active users with wallet addresses.

    Runs every hour to keep deposit data up-to-date.
    Scans users who haven't been scanned in the last hour.
    """
    logger.info("Starting periodic deposit scan...")

    try:
        asyncio.run(_scan_all_deposits_async())
        logger.info("Periodic deposit scan complete")
    except Exception as e:
        logger.exception(f"Periodic deposit scan failed: {e}")


async def _scan_all_deposits_async() -> None:
    """Async implementation of deposit scanning."""
    # Create local engine (for isolated task)
    local_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )

    local_session_maker = async_sessionmaker(
        local_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    try:
        async with local_session_maker() as session:
            # Get users with wallets who haven't been scanned recently
            one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

            stmt = select(User).where(
                User.wallet_address.isnot(None),
                User.wallet_address != "",
                User.is_active,
                not User.is_banned,
            ).where(
                # Scan if never scanned or last scan > 1 hour ago
                (User.last_deposit_scan_at.is_(None)) |
                (User.last_deposit_scan_at < one_hour_ago)
            ).limit(100)  # Process in batches

            result = await session.execute(stmt)
            users = result.scalars().all()

            if not users:
                logger.info("No users need deposit scanning")
                return

            logger.info(f"Scanning deposits for {len(users)} users")

            deposit_service = DepositScanService(session)

            scanned = 0
            errors = 0
            updated = 0

            for user in users:
                try:
                    scan_result = await deposit_service.scan_user_deposits(user.id)

                    if scan_result.get("success"):
                        scanned += 1
                        if scan_result.get("tx_count", 0) > 0:
                            updated += 1
                    else:
                        errors += 1
                        logger.warning(
                            f"Deposit scan failed for user {user.id}: "
                            f"{scan_result.get('error')}"
                        )

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

                except Exception as e:
                    errors += 1
                    logger.error(f"Error scanning user {user.id}: {e}")

            # Commit all changes
            await session.commit()

            logger.info(
                f"Deposit scan completed: "
                f"scanned={scanned}, updated={updated}, errors={errors}"
            )

    except Exception as e:
        logger.exception(f"Deposit scan error: {e}")
        raise
    finally:
        await local_engine.dispose()


@dramatiq.actor(max_retries=1, time_limit=60_000)  # 1 min timeout
def scan_single_user_deposits(user_id: int) -> None:
    """
    Scan deposits for a single user.

    Can be called on-demand (e.g., after authorization).
    """
    logger.info(f"Scanning deposits for user {user_id}")

    try:
        asyncio.run(_scan_single_user_async(user_id))
    except Exception as e:
        logger.exception(f"Deposit scan failed for user {user_id}: {e}")


async def _scan_single_user_async(user_id: int) -> None:
    """Scan deposits for single user."""
    local_engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )

    local_session_maker = async_sessionmaker(
        local_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    try:
        async with local_session_maker() as session:
            deposit_service = DepositScanService(session)
            result = await deposit_service.scan_user_deposits(user_id)

            if result.get("success"):
                await session.commit()
                logger.info(
                    f"Deposit scan for user {user_id}: "
                    f"total={result.get('total_amount')} USDT, "
                    f"active={result.get('is_active')}"
                )
            else:
                logger.warning(
                    f"Deposit scan failed for user {user_id}: "
                    f"{result.get('error')}"
                )
    finally:
        await local_engine.dispose()
