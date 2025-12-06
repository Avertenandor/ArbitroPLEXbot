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


@dramatiq.actor(max_retries=2, time_limit=120_000)  # 2 min timeout
def sync_blockchain_cache() -> None:
    """
    Sync new blocks to local transaction cache.
    
    Runs every minute to keep cache up-to-date.
    """
    logger.debug("Starting blockchain cache sync...")
    try:
        asyncio.run(_sync_cache_async())
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
        from app.config.database import async_session_maker
        from app.services.blockchain_realtime_sync_service import BlockchainRealtimeSyncService
        
        # Use QuickNode for real-time monitoring (lower latency)
        rpc_url = settings.rpc_quicknode_http or settings.rpc_url
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not w3.is_connected():
            logger.error("[RT Sync] Failed to connect to RPC")
            return
        
        async with async_session_maker() as session:
            sync_service = BlockchainRealtimeSyncService(session, w3)
            results = await sync_service.sync_all_tokens()
            
            total = sum(results.values())
            if total > 0:
                logger.info(f"[RT Sync] Cached {total} new transactions: {results}")
    
    except Exception as e:
        logger.error(f"[RT Sync] Error: {e}")
        raise
