#!/usr/bin/env python3
"""
Full History Sync Script.

Syncs ALL transactions for the system wallet from the first block
to the current block. Uses NodeReal for high rate limits.

This is a one-time operation to backfill the blockchain_tx_cache table.
After this, the scheduler will keep it updated in real-time.
"""

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import func, select, text
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


class FullHistorySync:
    """Syncs full transaction history for system wallet."""

    def __init__(
        self,
        session: AsyncSession,
        w3: Web3,
        system_wallet: str,
    ):
        self.session = session
        self.w3 = w3
        self.system_wallet = system_wallet.lower()
        
        # Token addresses
        self.usdt_address = settings.usdt_contract_address.lower()
        self.plex_address = settings.auth_plex_token_address.lower()
        
        # Scan settings - NodeReal can handle larger chunks
        self.chunk_size = 5000  # 5000 blocks per request
        
        # Statistics
        self.stats = {
            "usdt_incoming": 0,
            "usdt_outgoing": 0,
            "plex_incoming": 0,
            "plex_outgoing": 0,
            "total_cached": 0,
            "duplicates_skipped": 0,
        }

    async def find_first_transaction_block(self) -> int:
        """
        Find the block of the first transaction involving system wallet.
        
        Uses binary search on BscScan API or estimates from current block.
        For BSC, we can estimate based on wallet age.
        """
        # For now, let's use a reasonable starting point
        # BSC launched around block 0 in Aug 2020
        # We can start from a more recent block if wallet is newer
        
        # Check if we have any cached transactions already
        result = await self.session.execute(
            select(func.min(BlockchainTxCache.block_number))
        )
        min_cached = result.scalar()
        
        if min_cached and min_cached > 0:
            logger.info(f"Found cached transactions starting from block {min_cached}")
            # We might have gaps, so scan from earlier
            return max(0, min_cached - 100000)
        
        # Default: start from ~30 days ago on BSC (~850,000 blocks)
        current_block = self.w3.eth.block_number
        # BSC produces ~1 block per 3 seconds = ~28,800 blocks/day
        # Let's scan last 60 days = ~1.7M blocks
        days_back = 60
        blocks_back = days_back * 28800
        
        start_block = max(0, current_block - blocks_back)
        logger.info(f"Starting sync from block {start_block} ({days_back} days back)")
        
        return start_block

    async def get_latest_cached_block(self, token_type: str) -> int:
        """Get the latest block we have cached for a token type."""
        result = await self.session.execute(
            select(func.max(BlockchainTxCache.block_number))
            .where(BlockchainTxCache.token_type == token_type)
        )
        return result.scalar() or 0

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
            # Check for duplicate
            if await self.tx_exists(tx_hash):
                self.stats["duplicates_skipped"] += 1
                return False

            # Try to get block timestamp
            block_timestamp = None
            try:
                block = self.w3.eth.get_block(block_number)
                block_timestamp = datetime.fromtimestamp(block["timestamp"], tz=UTC)
            except Exception:
                pass

            # Determine user_id by matching wallet addresses
            user_id = None
            user_wallet = from_address if direction == "incoming" else to_address
            
            from app.repositories.user_repository import UserRepository
            user_repo = UserRepository(self.session)
            user = await user_repo.get_by_wallet(user_wallet)
            if user:
                user_id = user.id

            tx = BlockchainTxCache(
                tx_hash=tx_hash,
                block_number=block_number,
                block_timestamp=block_timestamp,
                from_address=from_address.lower(),
                to_address=to_address.lower(),
                token_type=token_type,
                token_address=token_address.lower(),
                amount=amount,
                amount_raw=str(int(amount * Decimal(10 ** (USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS)))),
                direction=direction,
                status="confirmed",
                user_id=user_id,
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
            logger.error(f"Error caching transaction {tx_hash}: {e}")
            return False

    async def scan_token(
        self,
        token_type: str,
        token_address: str,
        from_block: int,
        to_block: int,
    ) -> int:
        """
        Scan all Transfer events for a token.
        
        Args:
            token_type: USDT or PLEX
            token_address: Token contract address
            from_block: Starting block
            to_block: Ending block
            
        Returns:
            Number of transactions cached
        """
        logger.info(f"Scanning {token_type}: blocks {from_block} to {to_block}")
        
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        
        decimals = USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS
        total_cached = 0
        current_block = from_block
        
        while current_block < to_block:
            chunk_end = min(current_block + self.chunk_size, to_block)
            
            try:
                # Get incoming transfers (to system wallet)
                incoming_logs = contract.events.Transfer.get_logs(
                    fromBlock=current_block,
                    toBlock=chunk_end,
                    argument_filters={"to": Web3.to_checksum_address(self.system_wallet)}
                )
                
                # Get outgoing transfers (from system wallet)
                outgoing_logs = contract.events.Transfer.get_logs(
                    fromBlock=current_block,
                    toBlock=chunk_end,
                    argument_filters={"from": Web3.to_checksum_address(self.system_wallet)}
                )
                
                # Process incoming
                for log in incoming_logs:
                    args = log.get("args", {})
                    tx_hash = log["transactionHash"].hex()
                    amount = Decimal(args.get("value", 0)) / Decimal(10 ** decimals)
                    
                    cached = await self.cache_transaction(
                        tx_hash=tx_hash,
                        block_number=log["blockNumber"],
                        from_address=args.get("from", ""),
                        to_address=args.get("to", ""),
                        amount=amount,
                        token_type=token_type,
                        token_address=token_address,
                        direction="incoming",
                    )
                    if cached:
                        total_cached += 1
                
                # Process outgoing
                for log in outgoing_logs:
                    args = log.get("args", {})
                    tx_hash = log["transactionHash"].hex()
                    amount = Decimal(args.get("value", 0)) / Decimal(10 ** decimals)
                    
                    cached = await self.cache_transaction(
                        tx_hash=tx_hash,
                        block_number=log["blockNumber"],
                        from_address=args.get("from", ""),
                        to_address=args.get("to", ""),
                        amount=amount,
                        token_type=token_type,
                        token_address=token_address,
                        direction="outgoing",
                    )
                    if cached:
                        total_cached += 1
                
                # Commit every chunk to save progress
                await self.session.commit()
                
                progress = (chunk_end - from_block) / (to_block - from_block) * 100
                logger.info(
                    f"[{token_type}] Block {current_block}-{chunk_end}: "
                    f"in={len(incoming_logs)}, out={len(outgoing_logs)} | "
                    f"Progress: {progress:.1f}%"
                )
                
            except Exception as e:
                logger.error(f"Error scanning chunk {current_block}-{chunk_end}: {e}")
                # Continue with next chunk
                
            current_block = chunk_end + 1
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.1)
        
        return total_cached

    async def run_full_sync(self) -> dict:
        """
        Run full history sync for all tokens.
        
        Returns:
            Statistics dictionary
        """
        logger.info("=" * 60)
        logger.info("STARTING FULL HISTORY SYNC")
        logger.info(f"System Wallet: {self.system_wallet}")
        logger.info("=" * 60)
        
        current_block = self.w3.eth.block_number
        logger.info(f"Current block: {current_block}")
        
        # Find starting point
        start_block = await self.find_first_transaction_block()
        
        # Scan USDT
        logger.info("\n" + "=" * 40)
        logger.info("PHASE 1: Scanning USDT transfers...")
        logger.info("=" * 40)
        
        usdt_cached = await self.scan_token(
            token_type="USDT",
            token_address=self.usdt_address,
            from_block=start_block,
            to_block=current_block,
        )
        
        # Scan PLEX
        logger.info("\n" + "=" * 40)
        logger.info("PHASE 2: Scanning PLEX transfers...")
        logger.info("=" * 40)
        
        plex_cached = await self.scan_token(
            token_type="PLEX",
            token_address=self.plex_address,
            from_block=start_block,
            to_block=current_block,
        )
        
        # Final commit
        await self.session.commit()
        
        logger.info("\n" + "=" * 60)
        logger.info("FULL HISTORY SYNC COMPLETE")
        logger.info("=" * 60)
        logger.info(f"USDT: {self.stats['usdt_incoming']} incoming, {self.stats['usdt_outgoing']} outgoing")
        logger.info(f"PLEX: {self.stats['plex_incoming']} incoming, {self.stats['plex_outgoing']} outgoing")
        logger.info(f"Total cached: {self.stats['total_cached']}")
        logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        
        return self.stats


async def main():
    """Run full history sync."""
    logger.info("Initializing Full History Sync...")
    
    # Create database engine with NodeReal RPC
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
    
    # Use NodeReal for high-volume scanning
    nodereal_url = settings.rpc_nodereal_http or settings.rpc_url
    logger.info(f"Using RPC: {nodereal_url[:50]}...")
    
    w3 = Web3(Web3.HTTPProvider(nodereal_url))
    
    if not w3.is_connected():
        logger.error("Failed to connect to RPC")
        return
    
    logger.info(f"Connected to BSC, current block: {w3.eth.block_number}")
    
    async with session_maker() as session:
        syncer = FullHistorySync(
            session=session,
            w3=w3,
            system_wallet=settings.system_wallet_address,
        )
        
        stats = await syncer.run_full_sync()
        
    logger.info("Full history sync completed!")
    return stats


if __name__ == "__main__":
    asyncio.run(main())
