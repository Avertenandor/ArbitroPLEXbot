"""
Deposit monitoring task.

Monitors blockchain for deposit confirmations and updates deposit status.
Runs every minute to check pending deposits.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import dramatiq
from aiogram import Bot
from loguru import logger

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.config.settings import settings
from app.models.enums import TransactionStatus
from app.repositories.deposit_repository import DepositRepository
from app.services.blockchain_service import get_blockchain_service
from app.services.deposit_service import DepositService
from app.services.notification_service import NotificationService
from app.utils.distributed_lock import DistributedLock


@dramatiq.actor(max_retries=3, time_limit=300_000)  # 5 min timeout
def monitor_deposits() -> None:
    """
    Monitor pending deposits for blockchain confirmations.

    Checks all pending deposits against blockchain, confirms deposits
    with sufficient confirmations (e.g., 12 blocks on BSC).
    """
    logger.info("Starting deposit monitoring...")

    try:
        # Run async code
        asyncio.run(_monitor_deposits_async())
        logger.info("Deposit monitoring complete")

    except Exception as e:
        logger.exception(f"Deposit monitoring failed: {e}")


async def _search_and_confirm_deposit(
    deposit, blockchain_service, deposit_repo, deposit_service
):
    """Search blockchain for deposit and confirm if found."""
    if not deposit.user or not deposit.user.wallet_address:
        return None

    try:
        found_tx = await blockchain_service.search_blockchain_for_deposit(
            user_wallet=deposit.user.wallet_address,
            expected_amount=deposit.amount,
            from_block=0,
            to_block="latest",
            tolerance_percent=0.05,
        )

        if found_tx:
            await deposit_repo.update(deposit.id, tx_hash=found_tx["tx_hash"])
            await deposit_service.confirm_deposit(deposit.id, found_tx["block_number"])

        return found_tx
    except Exception as e:
        logger.warning(
            f"Error searching blockchain for deposit {deposit.id}: {e}",
            extra={"deposit_id": deposit.id},
        )
        return None


async def _notify_recovery_confirmed(notification_service, bot, deposit, found_tx):
    """Send notification for recovery deposit confirmation."""
    if not deposit.user:
        return

    notification_message = (
        f"✅ Депозит подтверждён после восстановления сети!\n\n"
        f"Ваш депозит уровня {deposit.level} "
        f"({deposit.amount} USDT) был найден в блокчейне "
        f"и подтверждён.\n\n"
        f"Транзакция: {found_tx['tx_hash']}"
    )
    await notification_service.send_notification(
        bot, deposit.user.telegram_id, notification_message, critical=True
    )


async def _notify_deposit_confirmed(notification_service, bot, deposit, found_tx):
    """Send notification for confirmed deposit."""
    if not deposit.user:
        return

    notification_message = (
        f"✅ Депозит подтверждён!\n\n"
        f"Ваш депозит уровня {deposit.level} "
        f"({deposit.amount} USDT) был найден в блокчейне и подтверждён.\n\n"
        f"Транзакция: {found_tx['tx_hash']}"
    )
    await notification_service.send_notification(
        bot, deposit.user.telegram_id, notification_message, critical=True
    )


async def _notify_deposit_expired(notification_service, bot, deposit):
    """Send notification for expired deposit."""
    if not deposit.user:
        return

    notification_message = (
        f"⚠️ Депозит не был подтверждён в течение 24 часов.\n\n"
        f"Ваш запрос на депозит уровня {deposit.level} "
        f"({deposit.amount} USDT) создан более 24 часов назад.\n\n"
        f"Транзакция не была найдена в блокчейне.\n\n"
        f"Если вы уже отправили средства, свяжитесь с поддержкой.\n\n"
        f"Если средства НЕ были отправлены, вы можете создать новый депозит."
    )
    await notification_service.send_notification(
        bot, deposit.user.telegram_id, notification_message, critical=False
    )


async def _process_single_recovery_deposit(
    deposit, blockchain_service, deposit_repo, deposit_service, notification_service, bot
):
    """Process a single recovery deposit."""
    found_tx = await _search_and_confirm_deposit(
        deposit, blockchain_service, deposit_repo, deposit_service
    )

    if found_tx:
        logger.info(
            f"R11-2: Found recovery deposit {deposit.id} "
            f"in blockchain: tx_hash={found_tx['tx_hash']}"
        )
        await _notify_recovery_confirmed(notification_service, bot, deposit, found_tx)
        return "confirmed"

    # Not found - keep as PENDING with new timeout
    await deposit_repo.update(deposit.id, status=TransactionStatus.PENDING.value)
    logger.info(
        f"R11-2: Recovery deposit {deposit.id} not found, converted to PENDING status"
    )
    return "pending"


async def _process_recovery_deposits(
    session, deposit_repo, deposit_service, blockchain_service, notification_service, bot
):
    """Process deposits with PENDING_NETWORK_RECOVERY status."""
    if settings.blockchain_maintenance_mode:
        return 0, 0

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.deposit import Deposit as DepositModel

    recovery_stmt = (
        select(DepositModel)
        .options(selectinload(DepositModel.user))
        .where(
            DepositModel.status == TransactionStatus.PENDING_NETWORK_RECOVERY.value
        )
    )
    recovery_result = await session.execute(recovery_stmt)
    recovery_deposits = list(recovery_result.scalars().unique().all())

    if not recovery_deposits:
        return 0, 0

    logger.info(
        f"R11-2: Processing {len(recovery_deposits)} deposits "
        "waiting for network recovery"
    )

    recovery_confirmed = 0
    recovery_still_pending = 0

    for deposit in recovery_deposits:
        try:
            result = await _process_single_recovery_deposit(
                deposit,
                blockchain_service,
                deposit_repo,
                deposit_service,
                notification_service,
                bot,
            )
            if result == "confirmed":
                recovery_confirmed += 1
            elif result == "pending":
                recovery_still_pending += 1
        except Exception as e:
            logger.error(
                f"R11-2: Error processing recovery deposit {deposit.id}: {e}",
                extra={"deposit_id": deposit.id},
                exc_info=True,
            )

    if recovery_confirmed > 0 or recovery_still_pending > 0:
        await session.commit()
        logger.info(
            f"R11-2: Recovery processing complete: "
            f"{recovery_confirmed} confirmed, "
            f"{recovery_still_pending} converted to PENDING"
        )

    return recovery_confirmed, recovery_still_pending


async def _process_single_expired_deposit(
    deposit,
    blockchain_service,
    deposit_repo,
    deposit_service,
    notification_service,
    bot,
):
    """Process a single expired deposit."""
    found_tx = await _search_and_confirm_deposit(
        deposit, blockchain_service, deposit_repo, deposit_service
    )

    if found_tx:
        logger.info(
            f"Found expired deposit {deposit.id} in blockchain: "
            f"tx_hash={found_tx['tx_hash']}, block={found_tx['block_number']}"
        )
        await _notify_deposit_confirmed(notification_service, bot, deposit, found_tx)
        return True  # Continue to next deposit

    # Transaction not found - mark as failed
    await deposit_repo.update(deposit.id, status=TransactionStatus.FAILED.value)

    logger.warning(
        f"Deposit {deposit.id} expired (24h timeout, not found in blockchain)",
        extra={
            "deposit_id": deposit.id,
            "user_id": deposit.user_id,
            "level": deposit.level,
            "amount": str(deposit.amount),
            "created_at": deposit.created_at.isoformat(),
        },
    )

    await _notify_deposit_expired(notification_service, bot, deposit)
    return False  # Mark as expired


async def _process_expired_deposits(
    pending_deposits,
    deposit_repo,
    deposit_service,
    blockchain_service,
    notification_service,
    bot,
):
    """Process expired deposits (24 hours without tx_hash)."""
    timeout_threshold = datetime.now(UTC) - timedelta(hours=24)
    pending_without_tx = [
        d
        for d in pending_deposits
        if not d.tx_hash and d.created_at < timeout_threshold
    ]

    expired_count = 0

    for deposit in pending_without_tx:
        try:
            was_confirmed = await _process_single_expired_deposit(
                deposit,
                blockchain_service,
                deposit_repo,
                deposit_service,
                notification_service,
                bot,
            )
            if not was_confirmed:
                expired_count += 1
        except Exception as e:
            logger.error(
                f"Error processing expired deposit {deposit.id}: {e}",
                extra={"deposit_id": deposit.id},
                exc_info=True,
            )

    return expired_count


async def _process_pending_deposits(
    pending_with_tx, blockchain_service, deposit_service
):
    """Process pending deposits with tx_hash."""
    processed = 0
    confirmed = 0
    still_pending = 0

    for deposit in pending_with_tx:
        try:
            tx_status = await blockchain_service.check_transaction_status(
                deposit.tx_hash
            )
            processed += 1

            if (
                tx_status.get("status") == "confirmed"
                and tx_status.get("confirmations", 0) >= 12
            ):
                block_number = tx_status.get("block_number", 0)
                await deposit_service.confirm_deposit(deposit.id, block_number)
                confirmed += 1

                logger.info(
                    f"Deposit {deposit.id} confirmed",
                    extra={
                        "deposit_id": deposit.id,
                        "tx_hash": deposit.tx_hash,
                        "confirmations": tx_status.get("confirmations"),
                    },
                )
            else:
                still_pending += 1

        except Exception as e:
            logger.error(
                f"Error checking deposit {deposit.id}: {e}",
                extra={
                    "deposit_id": deposit.id,
                    "tx_hash": deposit.tx_hash,
                },
            )

    return processed, confirmed, still_pending


async def _monitor_deposits_async() -> None:
    """Async implementation of deposit monitoring."""
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

    async with lock.lock("deposit_monitoring", timeout=300):
        try:
            from app.config.database import async_session_maker

            bot = Bot(token=settings.telegram_bot_token)

            try:
                async with async_session_maker() as session:
                    deposit_repo = DepositRepository(session)
                    deposit_service = DepositService(session)
                    blockchain_service = get_blockchain_service()
                    notification_service = NotificationService(session)

                    # Process recovery deposits
                    await _process_recovery_deposits(
                        session,
                        deposit_repo,
                        deposit_service,
                        blockchain_service,
                        notification_service,
                        bot,
                    )

                    # Get pending deposits
                    from sqlalchemy import select
                    from sqlalchemy.orm import selectinload

                    from app.models.deposit import Deposit as DepositModel

                    stmt = (
                        select(DepositModel)
                        .options(selectinload(DepositModel.user))
                        .where(DepositModel.status == TransactionStatus.PENDING.value)
                    )
                    result = await session.execute(stmt)
                    pending_deposits = list(result.scalars().unique().all())

                    # Process expired deposits
                    expired_count = await _process_expired_deposits(
                        pending_deposits,
                        deposit_repo,
                        deposit_service,
                        blockchain_service,
                        notification_service,
                        bot,
                    )

                    # Filter deposits with tx_hash
                    pending_with_tx = [d for d in pending_deposits if d.tx_hash]

                    if not pending_with_tx:
                        logger.debug("No pending deposits with tx_hash found")
                        await session.commit()
                        return

                    # Process pending deposits with tx_hash
                    processed, confirmed, still_pending = await _process_pending_deposits(
                        pending_with_tx, blockchain_service, deposit_service
                    )

                    await session.commit()

                    logger.info(
                        f"Deposit monitoring stats: "
                        f"{processed} processed, {confirmed} confirmed, "
                        f"{still_pending} still pending, {expired_count} expired"
                    )

            finally:
                await bot.session.close()
        finally:
            if redis_client:
                await redis_client.close()
