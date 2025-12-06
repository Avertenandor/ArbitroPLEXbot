"""
Incoming transfer monitor task.

Scans blockchain for all incoming transfers to system wallet.
Runs frequently (e.g. every minute) to catch deposits without explicit user action.
"""

import asyncio
from decimal import Decimal

import dramatiq
from loguru import logger

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # type: ignore

from app.config.settings import settings
from app.services.blockchain_service import get_blockchain_service
from app.services.incoming_deposit_service import IncomingDepositService
from app.utils.distributed_lock import DistributedLock


@dramatiq.actor(max_retries=3, time_limit=300_000)
def monitor_incoming_transfers() -> None:
    """
    Monitor blockchain for ANY incoming transfer to system wallet.
    """
    logger.info("Starting incoming transfer monitoring...")
    try:
        asyncio.run(_monitor_incoming_async())
        logger.info("Incoming transfer monitoring complete")
    except Exception as e:
        logger.exception(f"Incoming transfer monitoring failed: {e}")


async def _monitor_incoming_async() -> None:
    """Async implementation."""

    # Check if maintenance mode is active
    if settings.blockchain_maintenance_mode:
        logger.warning("Blockchain maintenance mode active. Skipping incoming monitor.")
        return

    # Create Redis client for distributed locks
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

    # Use distributed lock to prevent concurrent incoming transfer monitoring
    lock = DistributedLock(redis_client=redis_client)

    async with lock.lock("incoming_transfer_monitoring", timeout=300):
        try:
            # Use global engine and session maker
            from app.config.database import async_session_maker

            async with async_session_maker() as session:
                blockchain = get_blockchain_service()
                service = IncomingDepositService(session, redis_client=redis_client)

                # Use Redis to track last scanned block for idempotency
                last_block_key = "incoming_transfer:last_block"
                last_scanned = None

                if redis_client:
                    try:
                        last_scanned = await redis_client.get(last_block_key)
                    except Exception as e:
                        logger.warning(f"Failed to get last_scanned_block from Redis: {e}")

                current_block = await blockchain.get_block_number()

                # Determine scan range
                if last_scanned:
                    from_block = int(last_scanned) + 1
                    logger.info(f"Resuming from block {from_block}")
                else:
                    # First run or Redis unavailable: scan last 50 blocks
                    from_block = current_block - 50
                    logger.info(f"Starting fresh scan from block {from_block}")

                to_block = current_block

                logger.info(f"Scanning blocks {from_block} to {to_block} for incoming USDT...")

                # Get transfer events using sync Web3 in executor
                import asyncio
                from concurrent.futures import ThreadPoolExecutor
                from web3 import Web3
                
                w3 = blockchain.get_active_web3()
                
                # Create USDT contract for event parsing
                from app.services.blockchain.constants import USDT_ABI
                usdt_contract = w3.eth.contract(
                    address=Web3.to_checksum_address(blockchain.usdt_contract_address),
                    abi=USDT_ABI
                )
                
                # Scan in chunks to avoid RPC limits
                chunk_size = 2000
                all_logs = []
                current_start = from_block
                
                while current_start <= to_block:
                    current_end = min(current_start + chunk_size, to_block)
                    
                    try:
                        # Get Transfer events TO system wallet
                        with ThreadPoolExecutor() as executor:
                            logs = await asyncio.get_event_loop().run_in_executor(
                                executor,
                                lambda: usdt_contract.events.Transfer.get_logs(
                                    fromBlock=current_start,
                                    toBlock=current_end,
                                    argument_filters={
                                        "to": Web3.to_checksum_address(settings.system_wallet_address)
                                    }
                                )
                            )
                        all_logs.extend(logs)
                    except Exception as chunk_error:
                        logger.warning(f"Chunk {current_start}-{current_end} failed: {chunk_error}")
                    
                    current_start = current_end + 1

                logger.info(f"Found {len(all_logs)} transfer events")

                for log in all_logs:
                    try:
                        tx_hash = log["transactionHash"].hex()
                        block_number = log["blockNumber"]

                        # Parse event args (from contract.events.Transfer.get_logs format)
                        args = log.get("args", {})
                        from_address = args.get("from") or args.get("src")
                        to_address = args.get("to") or args.get("dst")
                        value = args.get("value") or args.get("wad", 0)
                        
                        # Convert to checksum addresses
                        from_address = w3.to_checksum_address(from_address)
                        to_address = w3.to_checksum_address(to_address)

                        # USDT on BSC has 18 decimals
                        amount = Decimal(value) / Decimal(10 ** 18)

                        await service.process_incoming_transfer(
                            tx_hash=tx_hash,
                            from_address=from_address,
                            to_address=to_address,
                            amount=amount,
                            block_number=block_number
                        )

                    except Exception as e:
                        logger.error(f"Error processing log {log}: {e}")

                # Update last scanned block in Redis for next run
                if redis_client:
                    try:
                        await redis_client.set(last_block_key, str(to_block))
                        logger.debug(f"Updated last_scanned_block to {to_block}")
                    except Exception as e:
                        logger.warning(f"Failed to update last_scanned_block in Redis: {e}")

        finally:
            if redis_client:
                await redis_client.close()
