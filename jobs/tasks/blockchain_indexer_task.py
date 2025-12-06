"""
Blockchain Indexer Background Task.

Maintains real-time indexing of blockchain transactions:
1. Initial full index at startup (if needed)
2. Continuous monitoring of new blocks every 30 seconds
3. Automatic user wallet indexing

This ensures the system always has complete transaction history
with minimal RPC calls after initial indexing.
"""

from loguru import logger

from app.config.database import async_session_maker
from app.services.blockchain_indexer_service import BlockchainIndexerService


async def run_blockchain_indexer() -> dict:
    """
    Main indexer task - monitors new blocks.

    Should run every 30 seconds for near real-time updates.
    Very cheap after initial indexing (typically 0-5 new txs per run).

    Returns:
        Dict with indexing results
    """
    results = {
        "success": False,
        "usdt": 0,
        "plex": 0,
        "errors": [],
    }

    try:
        async with async_session_maker() as session:
            # Get Web3 instance
            from app.services.blockchain_service import get_blockchain_service

            blockchain_service = get_blockchain_service()
            w3 = blockchain_service.w3

            if not w3:
                logger.warning("[Indexer Task] Web3 not available")
                results["errors"].append("Web3 not available")
                return results

            indexer = BlockchainIndexerService(session, w3)

            # Check if initial indexing is needed
            last_usdt = await indexer.get_last_indexed_block("USDT")
            last_plex = await indexer.get_last_indexed_block("PLEX")

            if last_usdt == 0:
                logger.info("[Indexer Task] Starting initial USDT indexing...")
                usdt_result = await indexer.full_index_system_wallet("USDT")
                results["usdt"] = usdt_result.get("indexed", 0)
                if not usdt_result.get("success"):
                    results["errors"].append(usdt_result.get("error", "USDT failed"))
            else:
                # Just monitor new blocks
                monitor_result = await indexer.monitor_new_blocks()
                results["usdt"] = monitor_result.get("usdt", 0)
                results["plex"] = monitor_result.get("plex", 0)
                if monitor_result.get("errors"):
                    results["errors"].extend(monitor_result["errors"])

            # Check PLEX initial indexing
            if last_plex == 0:
                logger.info("[Indexer Task] Starting initial PLEX indexing...")
                plex_result = await indexer.full_index_system_wallet("PLEX")
                results["plex"] = plex_result.get("indexed", 0)
                if not plex_result.get("success"):
                    results["errors"].append(plex_result.get("error", "PLEX failed"))

            results["success"] = len(results["errors"]) == 0

            total = results["usdt"] + results["plex"]
            if total > 0:
                logger.info(
                    f"[Indexer Task] Indexed {total} new transactions "
                    f"(USDT={results['usdt']}, PLEX={results['plex']})"
                )

    except Exception as e:
        logger.error(f"[Indexer Task] Failed: {e}")
        results["errors"].append(str(e))

    return results


async def index_user_on_registration(
    wallet_address: str,
    user_id: int,
) -> dict:
    """
    Index a user's wallet when they register.

    Called automatically after user provides wallet address.
    Indexes all historical transactions between user and system.

    Args:
        wallet_address: User's wallet address
        user_id: User's database ID

    Returns:
        Dict with indexing results
    """
    logger.info(
        f"[Indexer] Indexing wallet for new user {user_id}: "
        f"{wallet_address[:10]}..."
    )

    try:
        async with async_session_maker() as session:
            from app.services.blockchain_service import get_blockchain_service

            blockchain_service = get_blockchain_service()
            w3 = blockchain_service.w3

            if not w3:
                return {"success": False, "error": "Web3 not available"}

            indexer = BlockchainIndexerService(session, w3)
            result = await indexer.index_user_wallet(
                wallet_address=wallet_address,
                user_id=user_id,
            )

            return result

    except Exception as e:
        logger.error(f"[Indexer] User indexing failed: {e}")
        return {"success": False, "error": str(e)}


async def get_indexer_statistics() -> dict:
    """
    Get current indexer statistics.

    Returns:
        Dict with cache statistics
    """
    try:
        async with async_session_maker() as session:
            from app.services.blockchain_service import get_blockchain_service

            blockchain_service = get_blockchain_service()
            w3 = blockchain_service.w3

            if not w3:
                return {"error": "Web3 not available"}

            indexer = BlockchainIndexerService(session, w3)
            return await indexer.get_cache_stats()

    except Exception as e:
        logger.error(f"[Indexer] Stats failed: {e}")
        return {"error": str(e)}
