"""
Blockchain Real-Time Sync Task.

Syncs new blockchain transactions to local cache every minute.
This keeps the blockchain_tx_cache table up-to-date for instant lookups.
"""

import asyncio

import dramatiq
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from web3 import Web3

from app.config.settings import settings


@dramatiq.actor(max_retries=2, time_limit=120_000)  # 2 min timeout
def sync_blockchain_cache() -> None:
    """
    Sync new blocks to local transaction cache.
    
    Runs every 30 seconds to keep cache up-to-date.
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
        from app.services.blockchain_realtime_sync_service import BlockchainRealtimeSyncService
        
        # Create local engine (isolated from main app)
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
        
        # Use QuickNode for real-time monitoring (lower latency)
        rpc_url = settings.rpc_quicknode_http or settings.rpc_url
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        if not w3.is_connected():
            logger.error("[RT Sync] Failed to connect to RPC")
            return
        
        try:
            async with local_session_maker() as session:
                sync_service = BlockchainRealtimeSyncService(session, w3)
                results = await sync_service.sync_all_tokens()
                
                total = sum(results.values())
                if total > 0:
                    logger.info(f"[RT Sync] Cached {total} new transactions: {results}")
        finally:
            await local_engine.dispose()
    
    except Exception as e:
        logger.error(f"[RT Sync] Error: {e}")
        raise
