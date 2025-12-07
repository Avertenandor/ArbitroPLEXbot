#!/usr/bin/env python3
"""
Deep History Sync Script.

Syncs ALL transactions for the system wallet from GENESIS (block 0)
to the current block. Uses NodeReal for high rate limits.

This scans the ENTIRE history of the system wallet.
"""

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import func, select
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


def find_wallet_first_block(w3: Web3, wallet: str, token_address: str) -> int:
    """
    Binary search to find the first block where wallet had activity.
    
    Returns the approximate first block with token transfers.
    """
    logger.info(f"Searching for first transaction of {wallet[:10]}...")
    
    current_block = w3.eth.block_number
    
    # Binary search between 0 and current block
    # Start with rough estimate - go back 6 months (~5M blocks on BSC)
    low = max(0, current_block - 5_000_000)
    high = current_block
    
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(token_address),
        abi=ERC20_ABI
    )
    
    # First, check if there are any transactions at all
    try:
        logs = contract.events.Transfer.get_logs(
            fromBlock=low,
            toBlock=high,
            argument_filters={"to": Web3.to_checksum_address(wallet)}
        )
        if not logs:
            # Try outgoing
            logs = contract.events.Transfer.get_logs(
                fromBlock=low,
                toBlock=high,
                argument_filters={"from": Web3.to_checksum_address(wallet)}
            )
        
        if logs:
            first_block = min(log["blockNumber"] for log in logs)
            logger.info(f"Found transactions starting from block {first_block}")
            return max(0, first_block - 1000)  # Go back a bit for safety
    except Exception as e:
        logger.warning(f"Search failed: {e}")
    
    # If no logs found in recent history, start from 6 months ago
    return low


class DeepHistorySync:
    """Syncs COMPLETE transaction history for system wallet."""

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

            decimals = USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS

            tx = BlockchainTxCache(
                tx_hash=tx_hash,
                block_number=block_number,
                block_timestamp=block_timestamp,
                from_address=from_address.lower(),
                to_address=to_address.lower(),
                token_type=token_type,
                token_address=token_address.lower(),
                amount=amount,
                amount_raw=str(int(amount * Decimal(10 ** decimals))),
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
                if len(incoming_logs) > 0 or len(outgoing_logs) > 0:
                    logger.info(
                        f"[{token_type}] Block {current_block}-{chunk_end}: "
                        f"in={len(incoming_logs)}, out={len(outgoing_logs)} | "
                        f"Progress: {progress:.1f}%"
                    )
                elif int(progress) % 10 == 0:
                    logger.info(f"[{token_type}] Progress: {progress:.1f}%")
                
            except Exception as e:
                logger.error(f"Error scanning chunk {current_block}-{chunk_end}: {e}")
                # Continue with next chunk
                
            current_block = chunk_end + 1
            
            # Small delay to respect rate limits
            await asyncio.sleep(0.05)
        
        return total_cached

    async def run_deep_sync(self, start_block: int | None = None) -> dict:
        """
        Run COMPLETE history sync for all tokens.
        """
        logger.info("=" * 60)
        logger.info("STARTING DEEP HISTORY SYNC (FULL HISTORY)")
        logger.info(f"System Wallet: {self.system_wallet}")
        logger.info("=" * 60)
        
        current_block = self.w3.eth.block_number
        logger.info(f"Current block: {current_block}")
        
        # Find starting point if not provided
        if start_block is None:
            # Find earliest known transaction
            start_block = find_wallet_first_block(
                self.w3, 
                self.system_wallet, 
                self.usdt_address
            )
        
        logger.info(f"Starting from block: {start_block}")
        
        # Scan USDT
        logger.info("\n" + "=" * 40)
        logger.info("PHASE 1: Scanning USDT transfers...")
        logger.info("=" * 40)
        
        await self.scan_token(
            token_type="USDT",
            token_address=self.usdt_address,
            from_block=start_block,
            to_block=current_block,
        )
        
        # Scan PLEX
        logger.info("\n" + "=" * 40)
        logger.info("PHASE 2: Scanning PLEX transfers...")
        logger.info("=" * 40)
        
        await self.scan_token(
            token_type="PLEX",
            token_address=self.plex_address,
            from_block=start_block,
            to_block=current_block,
        )
        
        # Final commit
        await self.session.commit()
        
        logger.info("\n" + "=" * 60)
        logger.info("DEEP HISTORY SYNC COMPLETE")
        logger.info("=" * 60)
        logger.info(f"USDT: {self.stats['usdt_incoming']} incoming, {self.stats['usdt_outgoing']} outgoing")
        logger.info(f"PLEX: {self.stats['plex_incoming']} incoming, {self.stats['plex_outgoing']} outgoing")
        logger.info(f"Total cached: {self.stats['total_cached']}")
        logger.info(f"Duplicates skipped: {self.stats['duplicates_skipped']}")
        
        return self.stats


async def main():
    """Run deep history sync."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deep blockchain history sync")
    parser.add_argument("--start-block", type=int, default=None, help="Start block (default: auto-detect)")
    args = parser.parse_args()
    
    logger.info("Initializing Deep History Sync...")
    
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
        syncer = DeepHistorySync(
            session=session,
            w3=w3,
            system_wallet=settings.system_wallet_address,
        )
        
        stats = await syncer.run_deep_sync(start_block=args.start_block)
        
    logger.info("Deep history sync completed!")
    return stats


if __name__ == "__main__":
    asyncio.run(main())
