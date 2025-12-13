"""
Blockchain Real-Time Sync Task.

Syncs new blockchain transactions to local cache every minute.
This keeps the blockchain_tx_cache table up-to-date for instant lookups.
"""

import asyncio

import dramatiq
from loguru import logger
from web3 import Web3

from app.config.settings import settings
from jobs.async_runner import run_async
from jobs.utils.database import task_engine, task_session_maker


@dramatiq.actor(max_retries=2, time_limit=120_000)  # 2 min timeout
def sync_blockchain_cache() -> None:
    """
    Sync new blocks to local transaction cache.

    Runs every 30 seconds to keep cache up-to-date.
    """
    logger.debug("Starting blockchain cache sync...")
    try:
        run_async(_sync_cache_async())
        logger.debug("Blockchain cache sync complete")
    except Exception as e:
        logger.warning(f"Blockchain cache sync failed: {e}")


async def _sync_cache_async() -> None:
    """Async implementation of cache sync."""

    # Check maintenance mode
    if settings.blockchain_maintenance_mode:
        logger.warning("Blockchain maintenance mode active. Skipping cache sync.")
        return

    try:
        from app.services.blockchain_realtime_sync_service import BlockchainRealtimeSyncService

        # Use QuickNode for real-time monitoring (lower latency)
        rpc_url = settings.rpc_quicknode_http or settings.rpc_url
        w3 = Web3(Web3.HTTPProvider(rpc_url))

        if not w3.is_connected():
            logger.error("[RT Sync] Failed to connect to RPC")
            return

        try:
            async with task_session_maker() as session:
                sync_service = BlockchainRealtimeSyncService(session, w3)
                results = await sync_service.sync_all_tokens()

                total = sum(results.values())
                if total > 0:
                    logger.info(f"[RT Sync] Cached {total} new transactions: {results}")

                    # Sync user deposits if new USDT transactions found
                    if results.get("USDT", 0) > 0:
                        await _sync_user_deposits(task_session_maker)
        finally:
            await task_engine.dispose()

    except asyncio.CancelledError:
        logger.info("[RT Sync] Task cancelled")
        raise
    except Exception as e:
        logger.exception(f"[RT Sync] Task failed: {e}")
        raise


async def _sync_user_deposits(session_maker) -> None:
    """Sync users' total_deposited_usdt with cache after new transactions."""
    from decimal import Decimal

    from sqlalchemy import func, select

    from app.models.blockchain_tx_cache import BlockchainTxCache
    from app.models.user import User

    MINIMUM_DEPOSIT = Decimal("70")

    try:
        async with session_maker() as session:
            users_result = await session.execute(select(User).where(User.wallet_address.isnot(None)))
            users = users_result.scalars().all()

            for user in users:
                wallet = user.wallet_address.lower()

                sum_query = select(func.coalesce(func.sum(BlockchainTxCache.amount), 0)).where(
                    func.lower(BlockchainTxCache.from_address) == wallet,
                    BlockchainTxCache.token_type == "USDT",
                    BlockchainTxCache.direction == "incoming",
                )
                result = await session.execute(sum_query)
                cache_total = result.scalar() or Decimal("0")

                old_total = user.total_deposited_usdt or Decimal("0")

                if old_total != cache_total:
                    user.total_deposited_usdt = cache_total
                    user.is_active_depositor = cache_total >= MINIMUM_DEPOSIT
                    logger.info(f"[User Sync] {user.username}: {old_total} -> {cache_total} USDT")

            await session.commit()
    except Exception as e:
        logger.warning(f"[User Sync] Error: {e}")
