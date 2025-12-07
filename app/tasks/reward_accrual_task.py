"""
Reward accrual task.

Automatic individual reward calculation for deposits and bonus credits.
Runs periodically to process deposits that are due for accrual.
"""

from __future__ import annotations

from loguru import logger

from app.config.database import async_session_maker
from app.services.bonus_service import BonusService
from app.services.reward_service import RewardService
from app.services.roi_corridor_service import RoiCorridorService


async def run_individual_reward_accrual() -> None:
    """
    Run individual reward accrual for all due deposits and bonus credits.

    This task:
    1. Checks for 'next' session settings and applies them if needed
    2. Processes all deposits where next_accrual_at <= now
    3. Processes all bonus credits where next_accrual_at <= now
    4. Calculates rewards based on corridor settings
    5. Updates deposit/bonus ROI tracking
    6. Sends notifications for completed ROI cycles
    """
    logger.info("Starting individual reward accrual task")

    try:
        async with async_session_maker() as session:
            try:
                corridor_service = RoiCorridorService(session)
                reward_service = RewardService(session)
                bonus_service = BonusService(session)

                # Apply 'next' session settings if any exist
                await corridor_service.apply_next_session_settings()

                # Calculate individual rewards for due deposits
                await reward_service.calculate_individual_rewards()

                # Process bonus credit rewards
                bonus_stats = await bonus_service.process_bonus_rewards()
                if bonus_stats["processed"] > 0:
                    logger.info(
                        f"Bonus rewards: {bonus_stats['processed']} processed, "
                        f"{bonus_stats['total_rewards']} USDT total"
                    )

                logger.info("Individual reward accrual completed successfully")

            except Exception as e:
                logger.error(
                    f"Error in reward accrual: {e}",
                    extra={"error": str(e)},
                )
                await session.rollback()
                raise

    except Exception as e:
        logger.error(
            f"Fatal error in reward accrual task: {e}",
            extra={"error": str(e)},
        )
