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
            from app.config.database import async_engine, async_session_maker

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

                # Get transfer events
                w3 = blockchain.get_active_web3()
                contract = blockchain.usdt_contract

                # Filter for Transfer events to system wallet
                transfer_event_signature = w3.keccak(text="Transfer(address,address,uint256)").hex()
                padded_system_wallet = "0x" + settings.system_wallet_address[2:].lower().zfill(64)

                logs = await blockchain._run_async_failover(
                    lambda w: w.eth.get_logs({
                        "fromBlock": from_block,
                        "toBlock": to_block,
                        "address": blockchain.usdt_contract_address,
                        "topics": [
                            transfer_event_signature,
                            None, # from (any)
                            padded_system_wallet # to (system wallet)
                        ]
                    })
                )

                logger.info(f"Found {len(logs)} transfer events")

                for log in logs:
                    try:
                        tx_hash = log["transactionHash"].hex()
                        block_number = log["blockNumber"]

                        # Parse event
                        from_hex = log["topics"][1].hex()
                        from_address = "0x" + from_hex[26:] # Last 40 chars (20 bytes)
                        from_address = w3.to_checksum_address(from_address)

                        # Extract value
                        value_hex = log["data"].hex()
                        value_wei = int(value_hex, 16)
                        amount = Decimal(value_wei) / Decimal(10 ** 18) # USDT 18 decimals

                        # Verify 'to' address just in case
                        to_hex = log["topics"][2].hex()
                        to_addr_extracted = "0x" + to_hex[26:]
                        to_addr_checksum = w3.to_checksum_address(to_addr_extracted)

                        await service.process_incoming_transfer(
                            tx_hash=tx_hash,
                            from_address=from_address,
                            to_address=to_addr_checksum,
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

