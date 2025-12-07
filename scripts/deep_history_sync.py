#!/usr/bin/env python3
"""
Deep History Sync Script.

Syncs ALL transactions for the system wallet from the VERY FIRST block
to the current block using NodeReal (high limits).

Uses BSCScan API to find the first transaction, then scans everything.
"""

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from web3 import Web3

from app.config.settings import settings
from app.models.blockchain_tx_cache import BlockchainTxCache


# Token decimals
USDT_DECIMALS = 18
PLEX_DECIMALS = 9

# ERC20 Transfer event signature
ERC20_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "from", "type": "address"},
            {"indexed": True, "name": "to", "type": "address"},
            {"indexed": False, "name": "value", "type": "uint256"},
        ],
        "name": "Transfer",
        "type": "event",
    }
]


class DeepHistorySync:
    """Deep sync of all transactions for system wallet."""

    def __init__(
        self,
        session: AsyncSession,
        w3: Web3,
        system_wallet: str,
    ):
        self.session = session
        self.w3 = w3
        self.system_wallet = system_wallet.lower()
        self.system_wallet_checksum = Web3.to_checksum_address(system_wallet)
        
        # Token addresses
        self.usdt_address = settings.usdt_contract_address
        self.plex_address = settings.auth_plex_token_address
        
        # NodeReal can handle 5000 blocks per request
        self.chunk_size = 5000
        
        # Statistics
        self.stats = {
            "usdt_incoming": 0,
            "usdt_outgoing": 0,
            "plex_incoming": 0,
            "plex_outgoing": 0,
            "total_cached": 0,
            "duplicates_skipped": 0,
            "errors": 0,
        }

    async def find_first_transaction_block_bscscan(self) -> int:
        """Find first transaction block using BSCScan API."""
        logger.info("Finding first transaction block via BSCScan API...")
        
        try:
            async with httpx.AsyncClient() as client:
                # Get first normal transaction
                url = f"https://api.bscscan.com/api?module=account&action=txlist&address={self.system_wallet}&startblock=0&endblock=99999999&page=1&offset=1&sort=asc"
                resp = await client.get(url, timeout=30)
                data = resp.json()
                
                if data.get("status") == "1" and data.get("result"):
                    first_block = int(data["result"][0]["blockNumber"])
                    logger.info(f"BSCScan: First transaction at block {first_block}")
                    return first_block
        except Exception as e:
            logger.warning(f"BSCScan API failed: {e}")
        
        # Fallback: estimate ~1 year back
        current = self.w3.eth.block_number
        one_year_blocks = 365 * 24 * 60 * 20  # ~1 block per 3 sec
        return max(1, current - one_year_blocks)

    async def tx_exists(self, tx_hash: str) -> bool:
        """Check if transaction is already cached."""
        result = await self.session.execute(
            select(BlockchainTxCache.id)
            .where(BlockchainTxCache.tx_hash == tx_hash)
            .limit(1)
        )
        return result.scalar() is not None

    async def cache_transaction(
        self,
        tx_hash: str,
        block_number: int,
        from_address: str,
        to_address: str,
        amount: Decimal,
        token_type: str,
        token_address: str,
        direction: str,
    ) -> bool:
        """Cache a single transaction."""
        try:
            if await self.tx_exists(tx_hash):
                self.stats["duplicates_skipped"] += 1
                return False

            tx = BlockchainTxCache(
                tx_hash=tx_hash,
                block_number=block_number,
                from_address=from_address.lower(),
                to_address=to_address.lower(),
                token_type=token_type,
                token_address=token_address.lower(),
                amount=amount,
                amount_raw=str(int(amount * Decimal(10 ** (USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS)))),
                direction=direction,
                status="confirmed",
                is_processed=False,
            )

            self.session.add(tx)
            self.stats["total_cached"] += 1
            
            if direction == "incoming":
                if token_type == "USDT":
                    self.stats["usdt_incoming"] += 1
                else:
                    self.stats["plex_incoming"] += 1
            else:
                if token_type == "USDT":
                    self.stats["usdt_outgoing"] += 1
                else:
                    self.stats["plex_outgoing"] += 1

            return True

        except Exception as e:
            logger.error(f"Error caching tx {tx_hash}: {e}")
            self.stats["errors"] += 1
            return False

    def scan_token_chunk_sync(
        self,
        contract,
        from_block: int,
        to_block: int,
    ) -> tuple:
        """Synchronous scan of a block range for a token."""
        try:
            incoming = contract.events.Transfer.get_logs(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters={"to": self.system_wallet_checksum}
            )
        except Exception as e:
            logger.warning(f"Incoming scan failed {from_block}-{to_block}: {e}")
            incoming = []
            
        try:
            outgoing = contract.events.Transfer.get_logs(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters={"from": self.system_wallet_checksum}
            )
        except Exception as e:
            logger.warning(f"Outgoing scan failed {from_block}-{to_block}: {e}")
            outgoing = []
            
        return incoming, outgoing

    async def scan_token(
        self,
        token_type: str,
        token_address: str,
        from_block: int,
        to_block: int,
    ) -> int:
        """Scan all Transfer events for a token from NodeReal."""
        logger.info(f"[{token_type}] Scanning blocks {from_block:,} to {to_block:,} ({to_block - from_block:,} blocks)")
        
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        decimals = USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS
        total_cached = 0
        current_block = from_block
        total_blocks = to_block - from_block
        
        while current_block <= to_block:
            chunk_end = min(current_block + self.chunk_size - 1, to_block)
            
            try:
                # Run sync web3 call in executor
                loop = asyncio.get_event_loop()
                incoming, outgoing = await loop.run_in_executor(
                    None,
                    self.scan_token_chunk_sync,
                    contract,
                    current_block,
                    chunk_end,
                )
                
                # Process incoming
                for log in incoming:
                    args = log.get("args", {})
                    tx_hash = log["transactionHash"].hex()
                    amount = Decimal(args.get("value", 0)) / Decimal(10 ** decimals)
                    
                    if await self.cache_transaction(
                        tx_hash=tx_hash,
                        block_number=log["blockNumber"],
                        from_address=args.get("from", ""),
                        to_address=args.get("to", ""),
                        amount=amount,
                        token_type=token_type,
                        token_address=token_address,
                        direction="incoming",
                    ):
                        total_cached += 1
                
                # Process outgoing
                for log in outgoing:
                    args = log.get("args", {})
                    tx_hash = log["transactionHash"].hex()
                    amount = Decimal(args.get("value", 0)) / Decimal(10 ** decimals)
                    
                    if await self.cache_transaction(
                        tx_hash=tx_hash,
                        block_number=log["blockNumber"],
                        from_address=args.get("from", ""),
                        to_address=args.get("to", ""),
                        amount=amount,
                        token_type=token_type,
                        token_address=token_address,
                        direction="outgoing",
                    ):
                        total_cached += 1
                
                # Commit every chunk
                await self.session.commit()
                
                # Progress
                progress = (chunk_end - from_block) / total_blocks * 100 if total_blocks > 0 else 100
                if len(incoming) > 0 or len(outgoing) > 0:
                    logger.info(
                        f"[{token_type}] {current_block:,}-{chunk_end:,}: "
                        f"in={len(incoming)}, out={len(outgoing)} | {progress:.1f}%"
                    )
                elif int(progress) % 10 == 0:
                    logger.debug(f"[{token_type}] Progress: {progress:.1f}%")
                
            except Exception as e:
                logger.error(f"[{token_type}] Chunk {current_block:,}-{chunk_end:,} error: {e}")
                self.stats["errors"] += 1
                
            current_block = chunk_end + 1
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.05)
        
        return total_cached

    async def run(self) -> dict:
        """Run deep history sync."""
        logger.info("=" * 70)
        logger.info("DEEP HISTORY SYNC - FULL BLOCKCHAIN SCAN")
        logger.info(f"System Wallet: {self.system_wallet}")
        logger.info(f"Using NodeReal RPC for high-volume scanning")
        logger.info("=" * 70)
        
        current_block = self.w3.eth.block_number
        logger.info(f"Current block: {current_block:,}")
        
        # Find first transaction
        first_block = await self.find_first_transaction_block_bscscan()
        logger.info(f"Starting from block: {first_block:,}")
        
        total_blocks = current_block - first_block
        logger.info(f"Total blocks to scan: {total_blocks:,}")
        
        # Scan USDT
        logger.info("\n" + "=" * 50)
        logger.info("PHASE 1: USDT TRANSFERS")
        logger.info("=" * 50)
        
        await self.scan_token(
            token_type="USDT",
            token_address=self.usdt_address,
            from_block=first_block,
            to_block=current_block,
        )
        
        # Scan PLEX
        logger.info("\n" + "=" * 50)
        logger.info("PHASE 2: PLEX TRANSFERS")
        logger.info("=" * 50)
        
        await self.scan_token(
            token_type="PLEX",
            token_address=self.plex_address,
            from_block=first_block,
            to_block=current_block,
        )
        
        # Final commit
        await self.session.commit()
        
        logger.info("\n" + "=" * 70)
        logger.info("DEEP HISTORY SYNC COMPLETE")
        logger.info("=" * 70)
        logger.info(f"USDT: {self.stats['usdt_incoming']} incoming, {self.stats['usdt_outgoing']} outgoing")
        logger.info(f"PLEX: {self.stats['plex_incoming']} incoming, {self.stats['plex_outgoing']} outgoing")
        logger.info(f"Total cached: {self.stats['total_cached']}")
        logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        logger.info(f"Errors: {self.stats['errors']}")
        
        return self.stats


async def main():
    """Run deep history sync using NodeReal."""
    logger.info("Initializing Deep History Sync with NodeReal...")
    
    # Create database engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        poolclass=NullPool,
    )
    
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Use NodeReal for scanning (high limits)
    nodereal_url = settings.rpc_nodereal_http
    if not nodereal_url:
        logger.error("NodeReal RPC not configured! Set RPC_NODEREAL_HTTP in .env")
        return
    
    logger.info(f"NodeReal RPC: {nodereal_url[:60]}...")
    
    w3 = Web3(Web3.HTTPProvider(nodereal_url, request_kwargs={"timeout": 60}))
    
    if not w3.is_connected():
        logger.error("Failed to connect to NodeReal RPC!")
        return
    
    logger.info(f"Connected! Current block: {w3.eth.block_number:,}")
    
    async with session_maker() as session:
        syncer = DeepHistorySync(
            session=session,
            w3=w3,
            system_wallet=settings.system_wallet_address,
        )
        
        stats = await syncer.run()
        
    await engine.dispose()
    logger.info("Deep history sync completed!")
    return stats


if __name__ == "__main__":
    asyncio.run(main())
