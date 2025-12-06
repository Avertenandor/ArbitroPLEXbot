"""
Blockchain Transaction Cache Scanner Task.

Periodically scans blockchain for new transactions
and caches them in the database.

This reduces RPC calls by:
1. Only scanning new blocks (incremental)
2. Using cached data for historical queries
3. Linking transactions to users automatically
"""

from loguru import logger

from app.config.database import async_session_maker
from app.services.blockchain_tx_cache_service import BlockchainTxCacheService


async def scan_and_cache_blockchain_transactions() -> dict:
    """
    Scan blockchain for new transactions and cache them.

    This task should run periodically (e.g., every 5 minutes)
    to keep the cache up to date.

    Returns:
        Dict with scan results
    """
    logger.info("[TX Cache Task] Starting blockchain transaction scan...")

    results = {
        "success": False,
        "usdt_cached": 0,
        "plex_cached": 0,
        "users_linked": 0,
        "error": None,
    }

    try:
        async with async_session_maker() as session:
            # Initialize service
            cache_service = BlockchainTxCacheService(session)

            # Get Web3 instance from blockchain service
            from app.services.blockchain_service import get_blockchain_service

            blockchain_service = get_blockchain_service()
            w3 = blockchain_service.get_active_web3()

            if not w3:
                logger.warning("[TX Cache Task] Web3 not available, skipping scan")
                results["error"] = "Web3 not available"
                return results

            # Scan all tokens
            scan_results = await cache_service.scan_all_tokens(w3)

            results["usdt_cached"] = scan_results.get("USDT", 0)
            results["plex_cached"] = scan_results.get("PLEX", 0)

            # Link unprocessed transactions to users
            linked = await cache_service.link_unprocessed_to_users()
            results["users_linked"] = linked

            results["success"] = True

            logger.info(
                f"[TX Cache Task] Scan complete: "
                f"USDT={results['usdt_cached']}, "
                f"PLEX={results['plex_cached']}, "
                f"linked={results['users_linked']}"
            )

    except Exception as e:
        logger.error(f"[TX Cache Task] Scan failed: {e}")
        results["error"] = str(e)

    return results


async def get_cache_statistics() -> dict:
    """
    Get statistics about cached transactions.

    Returns:
        Dict with cache statistics
    """
    try:
        async with async_session_maker() as session:
            cache_service = BlockchainTxCacheService(session)
            stats = await cache_service.get_system_wallet_stats()
            return stats

    except Exception as e:
        logger.error(f"[TX Cache Task] Stats failed: {e}")
        return {"error": str(e)}
