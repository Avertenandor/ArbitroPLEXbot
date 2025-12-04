"""
Stuck Transaction Monitor (R7-6).

Monitors withdrawal transactions stuck in PROCESSING status.
Runs every 5 minutes to check for stuck transactions.
"""

import asyncio

import dramatiq
from aiogram import Bot
from loguru import logger

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.config.database import async_session_maker
from app.config.settings import settings
from app.services.blockchain_service import get_blockchain_service
from app.services.notification_service import NotificationService
from app.services.stuck_transaction_service import StuckTransactionService
from app.utils.distributed_lock import DistributedLock


@dramatiq.actor(max_retries=3, time_limit=300_000)  # 5 min timeout
def monitor_stuck_transactions() -> dict:
    """
    Monitor stuck withdrawal transactions.

    R7-6: Checks withdrawals in PROCESSING status older than 15 minutes,
    verifies their status in blockchain, and handles accordingly:
    - Pending: speed-up with higher gas
    - Failed: refund user balance
    - Dropped: retry with new nonce

    Returns:
        Dict with processed, confirmed, failed, pending counts
    """
    logger.info("Starting stuck transaction monitoring...")

    try:
        # Run async code
        result = asyncio.run(_monitor_stuck_transactions_async())

        logger.info(
            f"Stuck transaction monitoring complete: "
            f"{result['processed']} processed, "
            f"{result['confirmed']} confirmed, "
            f"{result['failed']} failed, "
            f"{result['pending']} still pending"
        )

        return result

    except Exception as e:
        logger.exception(f"Stuck transaction monitoring failed: {e}")
        return {
            "processed": 0,
            "confirmed": 0,
            "failed": 0,
            "pending": 0,
            "error": str(e),
        }


async def _load_user_for_withdrawal(session, withdrawal):
    """Load user for a withdrawal transaction."""
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from app.models.user import User

        stmt = (
            select(User)
            .where(User.id == withdrawal.user_id)
            .options(selectinload(User.transactions))
        )

        result_user = await session.execute(stmt)
        return result_user.scalar_one_or_none()
    except Exception as e:
        logger.error(
            f"Error loading user for withdrawal {withdrawal.id}: {e}"
        )
        return None


async def _notify_withdrawal_confirmed(
    notification_service, bot, session, withdrawal
):
    """Notify user about confirmed withdrawal."""
    user = await _load_user_for_withdrawal(session, withdrawal)
    if not user:
        return

    try:
        await notification_service.send_notification(
            bot=bot,
            user_telegram_id=user.telegram_id,
            message=(
                f"✅ Ваш вывод подтвержден!\n\n"
                f"💰 Сумма: {withdrawal.amount} USDT\n"
                f"🔗 TX: {withdrawal.tx_hash}\n\n"
                f"Транзакция успешно обработана в блокчейне."
            ),
            critical=True,
        )
    except Exception as e:
        logger.error(
            f"Error sending notification for transaction {withdrawal.id}: {e}"
        )


async def _notify_withdrawal_failed(
    notification_service, bot, session, withdrawal
):
    """Notify user about failed withdrawal and refund."""
    user = await _load_user_for_withdrawal(session, withdrawal)
    if not user:
        return

    try:
        await notification_service.send_notification(
            bot=bot,
            user_telegram_id=user.telegram_id,
            message=(
                f"⚠️ Транзакция вывода не прошла\n\n"
                f"💰 Сумма: {withdrawal.amount} USDT\n"
                f"🔗 TX: {withdrawal.tx_hash}\n\n"
                f"Средства возвращены на ваш баланс. "
                f"Попробуйте создать новый запрос на вывод."
            ),
            critical=True,
        )
    except Exception as e:
        logger.error(
            f"Error sending notification for failed transaction {withdrawal.id}: {e}"
        )


async def _process_single_stuck_withdrawal(
    withdrawal,
    stuck_service,
    blockchain_service,
    notification_service,
    bot,
    session,
    web3,
):
    """Process a single stuck withdrawal transaction."""
    bs_status = await blockchain_service.check_transaction_status(
        withdrawal.tx_hash
    )

    # Map status to format expected by handle_stuck_transaction
    status_map = {
        "confirmed": "confirmed",
        "failed": "failed",
        "pending": "pending",
        "unknown": "error",
    }

    tx_status = {
        "status": status_map.get(bs_status.get("status"), "error"),
        "error": None,
    }

    # Handle based on status
    result = await stuck_service.handle_stuck_transaction(
        withdrawal, tx_status, web3
    )

    # Notify user based on result action
    if result["action"] == "confirmed":
        await _notify_withdrawal_confirmed(
            notification_service, bot, session, withdrawal
        )
    elif result["action"] == "failed_refunded":
        await _notify_withdrawal_failed(
            notification_service, bot, session, withdrawal
        )

    return result["action"]


async def _process_stuck_withdrawals(
    stuck_withdrawals,
    stuck_service,
    blockchain_service,
    notification_service,
    bot,
    session,
):
    """Process all stuck withdrawals."""
    processed = 0
    confirmed = 0
    failed = 0
    pending = 0

    web3 = blockchain_service.get_active_web3()

    for withdrawal in stuck_withdrawals:
        try:
            action = await _process_single_stuck_withdrawal(
                withdrawal,
                stuck_service,
                blockchain_service,
                notification_service,
                bot,
                session,
                web3,
            )

            processed += 1

            if action == "confirmed":
                confirmed += 1
            elif action == "failed_refunded":
                failed += 1
            elif action in [
                "pending_waiting",
                "pending_speedup_needed",
                "not_found_retry_needed",
            ]:
                pending += 1

        except Exception as e:
            logger.error(
                f"Error processing stuck transaction {withdrawal.id}: {e}",
                extra={"transaction_id": withdrawal.id},
            )

    return processed, confirmed, failed, pending


async def _monitor_stuck_transactions_async() -> dict:
    """Async implementation of stuck transaction monitoring."""
    redis_client = None
    if redis:
        try:
            redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
            )
        except Exception as e:
            logger.warning(f"Failed to create Redis client for lock: {e}")

    lock = DistributedLock(redis_client=redis_client)

    async with lock.lock("stuck_transaction_monitoring", timeout=300):
        try:
            async with async_session_maker() as session:
                stuck_service = StuckTransactionService(session)
                blockchain_service = get_blockchain_service()

                # Get stuck withdrawals (older than 15 minutes)
                stuck_withdrawals = await stuck_service.find_stuck_withdrawals(
                    older_than_minutes=15
                )

                if not stuck_withdrawals:
                    logger.debug("No stuck withdrawals found")
                    return {
                        "processed": 0,
                        "confirmed": 0,
                        "failed": 0,
                        "pending": 0,
                    }

                logger.info(
                    f"Found {len(stuck_withdrawals)} stuck withdrawal(s) to process"
                )

                # Initialize bot for notifications
                bot = Bot(token=settings.telegram_bot_token)
                notification_service = NotificationService(session)

                # Process all stuck withdrawals
                processed, confirmed, failed, pending = await _process_stuck_withdrawals(
                    stuck_withdrawals,
                    stuck_service,
                    blockchain_service,
                    notification_service,
                    bot,
                    session,
                )

                # Check if we have too many stuck transactions (>3)
                if len(stuck_withdrawals) > 3:
                    logger.warning(
                        f"CRITICAL: {len(stuck_withdrawals)} transactions stuck "
                        f"simultaneously - possible systemic issue",
                        extra={"stuck_count": len(stuck_withdrawals)},
                    )

                await bot.session.close()

                return {
                    "processed": processed,
                    "confirmed": confirmed,
                    "failed": failed,
                    "pending": pending,
                    "total_stuck": len(stuck_withdrawals),
                }
        finally:
            if redis_client:
                await redis_client.close()
