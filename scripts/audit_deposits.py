import asyncio
import sys
from enum import StrEnum
from pathlib import Path


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.models.deposit import Deposit
from app.models.deposit_reward import DepositReward
from app.utils.datetime_utils import utc_now


# Configure logger for script
logger.remove()
logger.add(sys.stderr, level="INFO")


# Define Enum locally if not available in model
class DepositStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    ROI_COMPLETED = "roi_completed"
    PENDING_NETWORK_RECOVERY = "pending_network_recovery"


async def audit_deposits():
    logger.info("🚀 Starting deposit audit...")

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

    try:
        async with session_maker() as session:
            # 1. Get all confirmed deposits
            stmt = (
                select(Deposit)
                .options(selectinload(Deposit.user))
                .where(Deposit.status == DepositStatus.CONFIRMED.value)
                .order_by(Deposit.created_at)
            )
            result = await session.execute(stmt)
            deposits = result.scalars().all()

            logger.info(f"Found {len(deposits)} CONFIRMED deposits.")

            for deposit in deposits:
                user = deposit.user

                # Fetch rewards manually since relationship might be missing
                r_stmt = select(DepositReward).where(DepositReward.deposit_id == deposit.id).order_by(DepositReward.calculated_at)
                r_result = await session.execute(r_stmt)
                rewards = r_result.scalars().all()

                total_rewards = sum(r.reward_amount for r in rewards)  # Note: reward_amount, not amount
                last_reward = rewards[-1] if rewards else None

                logger.info(f"\n--- Deposit ID: {deposit.id} ---")
                logger.info(f"User: {user.id} (ID: {user.telegram_id}, Username: @{user.username or 'NoUsername'})")
                logger.info(f"Amount: {deposit.amount} USDT")
                logger.info(f"Level: {deposit.level}")
                logger.info(f"Created At: {deposit.created_at}")
                logger.info(f"Next Accrual At: {deposit.next_accrual_at}")
                logger.info(f"ROI Paid (DB): {deposit.roi_paid_amount}")
                logger.info(f"ROI Paid (Calc): {total_rewards}")
                logger.info(f"ROI Cap: {deposit.roi_cap_amount}")
                logger.info(f"Is Completed: {deposit.is_roi_completed}")

                if last_reward:
                    logger.info(f"Last Reward: {last_reward.reward_amount} at {last_reward.calculated_at}")
                else:
                    logger.info("No rewards yet.")

                # Check for issues
                if deposit.next_accrual_at:
                    now = utc_now()

                    if deposit.next_accrual_at < now:
                        logger.warning(f"ALERT: Next accrual was due at {deposit.next_accrual_at} (Past due!)")

                if deposit.roi_paid_amount >= deposit.roi_cap_amount and not deposit.is_roi_completed:
                    logger.warning("ALERT: ROI Cap reached but not marked completed!")

    except Exception as e:
        logger.exception(f"Audit failed: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(audit_deposits())
