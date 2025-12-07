"""
Balance Notification Task.

Sends hourly notifications to active users about their arbitrage earnings.
Runs every hour via scheduler.

Notification includes:
- Number of arbitrage operations (generated 180-300 range)
- Amount in work
- User's earnings share
- Partner earnings
- Income from partners
- Available for withdrawal

Only sends to users with:
- Active work status (PLEX paid)
- Confirmed deposits or balance > 0
- Not blocked the bot
- Not banned
"""

import dramatiq
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.settings import settings
from app.services.balance_notification_service import BalanceNotificationService
from app.utils.distributed_lock import get_distributed_lock
from jobs.async_runner import run_async


@dramatiq.actor(max_retries=2, time_limit=600_000)  # 10 min timeout
def send_balance_notifications() -> dict:
    """
    Send hourly balance notifications to all eligible users.

    This task:
    1. Gets all users with active work status and confirmed deposits
    2. For each user, calculates their statistics
    3. Sends a formatted notification with earnings info

    Returns:
        {
            "total": int,    # Total eligible users
            "sent": int,     # Successfully sent
            "failed": int,   # Failed to send
            "blocked": int,  # Users who blocked the bot
        }
    """
    logger.info("Starting hourly balance notifications...")

    try:
        result = run_async(_send_balance_notifications_async())
        logger.info(f"Balance notifications complete: {result}")
        return result
    except Exception as e:
        logger.exception(f"Balance notifications failed: {e}")
        return {
            "total": 0,
            "sent": 0,
            "failed": 0,
            "blocked": 0,
            "error": str(e),
        }


async def _send_balance_notifications_async() -> dict:
    """Async implementation of balance notifications."""
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

    stats = {
        "total": 0,
        "sent": 0,
        "failed": 0,
        "blocked": 0,
    }

    bot = None

    try:
        async with local_session_maker() as session:
            # Use distributed lock to prevent concurrent notifications
            lock = get_distributed_lock(session=session)

            async with lock.lock(
                "balance_notifications",
                timeout=300,
                blocking=False,
            ) as acquired:
                if not acquired:
                    logger.warning(
                        "Balance notifications already running, skipping"
                    )
                    return stats

                # Create bot instance
                bot = Bot(
                    token=settings.telegram_bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
                )

                # Create notification service
                service = BalanceNotificationService(session)

                # Send notifications to all eligible users
                stats = await service.send_notifications_to_all_eligible(bot)

                logger.info(f"Balance notification stats: {stats}")

    except Exception as e:
        logger.exception(f"Balance notification error: {e}")
        stats["error"] = str(e)
        raise
    finally:
        # Close bot session
        if bot:
            await bot.session.close()
        # Dispose engine
        await local_engine.dispose()

    return stats


@dramatiq.actor(max_retries=1, time_limit=60_000)  # 1 min timeout
def send_single_balance_notification(user_id: int) -> dict:
    """
    Send balance notification to a single user (on-demand).

    Can be called manually from admin panel or after specific events.

    Args:
        user_id: Database user ID

    Returns:
        {
            "success": bool,
            "user_id": int,
            "error": str | None,
        }
    """
    logger.info(f"Sending balance notification to user {user_id}")

    try:
        result = run_async(_send_single_notification_async(user_id))
        logger.info(f"Single notification result: {result}")
        return result
    except Exception as e:
        logger.exception(f"Single notification failed for user {user_id}: {e}")
        return {
            "success": False,
            "user_id": user_id,
            "error": str(e),
        }


async def _send_single_notification_async(user_id: int) -> dict:
    """Send notification to single user."""
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

    bot = None

    try:
        async with local_session_maker() as session:
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            from app.models.user import User

            # Get user
            stmt = (
                select(User)
                .where(User.id == user_id)
                .options(selectinload(User.deposits))
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": "User not found",
                }

            # Check if user is eligible
            if user.bot_blocked:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": "User blocked the bot",
                }

            if user.is_banned:
                return {
                    "success": False,
                    "user_id": user_id,
                    "error": "User is banned",
                }

            # Create bot instance
            bot = Bot(
                token=settings.telegram_bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
            )

            # Create service and send
            service = BalanceNotificationService(session)
            success = await service.send_notification_to_user(bot, user)

            if success:
                await session.commit()

            return {
                "success": success,
                "user_id": user_id,
                "error": None if success else "Failed to send",
            }

    finally:
        if bot:
            await bot.session.close()
        await local_engine.dispose()
