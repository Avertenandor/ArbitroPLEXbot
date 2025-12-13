"""
PLEX Payment Monitor Task.

Monitors PLEX payment requirements:
- Checks all active deposits with PlexPaymentRequirement
- Scans blockchain for PLEX payments
- Sends warnings (after 25h without payment)
- Blocks deposits (after 49h without payment)

Runs every hour via scheduler.
"""

import dramatiq
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config.operational_constants import (
    DRAMATIQ_TIME_LIMIT_LONG,
    DRAMATIQ_TIME_LIMIT_SHORT,
)
from app.config.settings import settings
from app.services.blockchain.singleton import get_blockchain_service
from app.services.deposit.plex.monitor import PlexPaymentMonitor
from app.utils.distributed_lock import get_distributed_lock
from jobs.async_runner import run_async


@dramatiq.actor(max_retries=2, time_limit=DRAMATIQ_TIME_LIMIT_LONG)  # 10 min timeout
def monitor_plex_payments() -> dict:
    """
    Периодическая проверка PLEX платежей.

    Логика:
    1. Получить все активные депозиты с PlexPaymentRequirement
    2. Для каждого проверить:
       - Прошло ли 24 часа с последнего платежа?
       - Есть ли PLEX транзакция от пользователя?
    3. Если платёж найден - отметить получение
    4. Если нет платежа:
       - 24-25h: ожидание
       - 25-49h: предупреждение
       - 49h+: блокировка депозита

    Returns:
        {
            "checked": int,      # Всего проверено
            "paid": int,         # Оплачено
            "warnings_sent": int,# Предупреждений отправлено
            "blocked": int,      # Заблокировано
            "errors": int        # Ошибок
        }
    """
    logger.info("Starting PLEX payment monitoring...")

    try:
        result = run_async(_monitor_plex_payments_async())
        logger.info(f"PLEX payment monitoring complete: {result}")
        return result
    except Exception as e:
        logger.exception(f"PLEX payment monitoring failed: {e}")
        return {
            "checked": 0,
            "paid": 0,
            "warnings_sent": 0,
            "blocked": 0,
            "errors": 1,
        }


async def _monitor_plex_payments_async() -> dict:
    """Async implementation of PLEX payment monitoring."""
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
        "checked": 0,
        "paid": 0,
        "warnings_sent": 0,
        "blocked": 0,
        "errors": 0,
    }

    try:
        async with local_session_maker() as session:
            # Use distributed lock to prevent concurrent monitoring
            lock = get_distributed_lock(session=session)

            async with lock.lock(
                "plex_payment_monitoring",
                timeout=300,
                blocking=False,
            ) as acquired:
                if not acquired:
                    logger.warning(
                        "PLEX payment monitoring already running, skipping"
                    )
                    return stats

                # Get blockchain service
                blockchain = get_blockchain_service()

                # Create monitor instance
                monitor = PlexPaymentMonitor(session, blockchain)

                # Process all pending payments
                result = await monitor.process_pending_payments()

                # Update stats
                stats["checked"] = result.get("checked", 0)
                stats["paid"] = result.get("paid", 0)
                stats["warnings_sent"] = result.get("warnings_sent", 0)
                stats["blocked"] = result.get("blocked", 0)

                # Commit changes
                await session.commit()

                logger.info(f"PLEX monitoring stats: {stats}")

    except Exception as e:
        logger.exception(f"PLEX payment monitoring error: {e}")
        stats["errors"] = 1
        raise
    finally:
        await local_engine.dispose()

    return stats


@dramatiq.actor(max_retries=1, time_limit=DRAMATIQ_TIME_LIMIT_SHORT)  # 1 min timeout
def check_single_user_plex(user_id: int, deposit_id: int) -> dict:
    """
    Check PLEX payment for a single user deposit.

    Can be called on-demand (e.g., after deposit creation or manual check).

    Args:
        user_id: ID пользователя
        deposit_id: ID депозита

    Returns:
        {
            "status": str,       # paid/pending/warning/overdue
            "required": Decimal, # Требуемая сумма
            "received": Decimal, # Полученная сумма
            "tx_hash": str,      # Хэш транзакции (если найден)
            "hours_overdue": int # Часов просрочки
        }
    """
    logger.info(f"Checking PLEX payment for user {user_id}, deposit {deposit_id}")

    try:
        result = run_async(_check_single_user_async(user_id, deposit_id))
        logger.info(f"PLEX check result: {result}")
        return result
    except Exception as e:
        logger.exception(f"PLEX check failed for user {user_id}: {e}")
        return {
            "status": "error",
            "required": 0,
            "received": 0,
            "tx_hash": None,
            "hours_overdue": 0,
        }


async def _check_single_user_async(user_id: int, deposit_id: int) -> dict:
    """Check PLEX payment for single user deposit."""
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
            # Get blockchain service
            blockchain = get_blockchain_service()

            # Create monitor instance
            monitor = PlexPaymentMonitor(session, blockchain)

            # Check payment
            result = await monitor.check_user_plex_payment(
                user_id=user_id,
                deposit_id=deposit_id,
            )

            # Commit any changes (e.g., if payment was found and marked)
            await session.commit()

            return result
    finally:
        await local_engine.dispose()
