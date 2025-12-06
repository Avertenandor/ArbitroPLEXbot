"""
Blockchain Indexer Service.

Full indexing of blockchain transactions for system and user wallets.
Provides real-time monitoring of new blocks and instant access to cached data.

Key features:
- Initial full scan of system wallet history
- Real-time monitoring of new blocks
- Automatic indexing of user wallets on registration
- Zero RPC calls for historical data queries
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from app.config.settings import settings
from app.models.blockchain_tx_cache import BlockchainTxCache
from app.repositories.blockchain_tx_cache_repository import (
    BlockchainTxCacheRepository,
)
from app.repositories.user_repository import UserRepository


# Token decimals
USDT_DECIMALS = 18
PLEX_DECIMALS = 18

# Minimal ERC20 ABI for Transfer events
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


def mask_address(address: str) -> str:
    """Mask address for logging."""
    if not address or len(address) < 10:
        return address
    return f"{address[:6]}...{address[-4:]}"


class BlockchainIndexerService:
    """
    Complete blockchain indexer for transaction history.

    Maintains a full cache of all transactions involving:
    - System wallet (all incoming/outgoing)
    - Each user's wallet (relevant to system)

    After initial indexing, only monitors new blocks.
    """

    def __init__(self, session: AsyncSession, w3: Web3):
        """
        Initialize indexer.

        Args:
            session: Database session
            w3: Web3 instance
        """
        self.session = session
        self.w3 = w3
        self.cache_repo = BlockchainTxCacheRepository(session)
        self.user_repo = UserRepository(session)

        # Configuration
        sys_wallet = settings.system_wallet_address
        self.system_wallet = sys_wallet.lower() if sys_wallet else None

        usdt_addr = settings.usdt_contract_address
        self.usdt_address = usdt_addr.lower() if usdt_addr else None

        plex_addr = settings.auth_plex_token_address
        self.plex_address = plex_addr.lower() if plex_addr else None

        # Indexing settings
        self.chunk_size = 2000  # Blocks per chunk (safe for QuickNode)
        self.initial_scan_blocks = 500000  # ~17 days on BSC

    async def get_last_indexed_block(self, token_type: str) -> int:
        """Get the last block we have indexed for a token type."""
        return await self.cache_repo.get_latest_block(token_type)

    async def full_index_system_wallet(
        self,
        token_type: str = "USDT",
        from_block: int | None = None,
    ) -> dict:
        """
        Full index of system wallet transactions.

        Scans entire history and caches all transactions.
        Should be run ONCE at system startup or when cache is empty.

        Args:
            token_type: Token to index (USDT, PLEX)
            from_block: Starting block (default: latest - initial_scan_blocks)

        Returns:
            Dict with indexing stats
        """
        if not self.system_wallet:
            return {"success": False, "error": "System wallet not configured"}

        token_address = (
            self.usdt_address if token_type == "USDT" else self.plex_address
        )
        if not token_address:
            return {"success": False, "error": f"{token_type} address not configured"}

        try:
            latest_block = self.w3.eth.block_number

            # Determine starting block
            if from_block is None:
                last_indexed = await self.get_last_indexed_block(token_type)
                if last_indexed > 0:
                    from_block = last_indexed + 1
                    logger.info(
                        f"[Indexer] Resuming {token_type} from block {from_block}"
                    )
                else:
                    from_block = max(0, latest_block - self.initial_scan_blocks)
                    logger.info(
                        f"[Indexer] Initial {token_type} index from {from_block}"
                    )

            if from_block >= latest_block:
                return {
                    "success": True,
                    "message": "Already up to date",
                    "indexed": 0,
                    "from_block": from_block,
                    "to_block": latest_block,
                }

            total_blocks = latest_block - from_block
            logger.info(
                f"[Indexer] Indexing {token_type} for system wallet: "
                f"{total_blocks} blocks ({from_block} -> {latest_block})"
            )

            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )

            decimals = USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS
            total_indexed = 0
            chunks_processed = 0

            current_block = from_block
            while current_block < latest_block:
                chunk_end = min(current_block + self.chunk_size, latest_block)

                try:
                    # Get incoming transfers (to system)
                    incoming = contract.events.Transfer.get_logs(
                        fromBlock=current_block,
                        toBlock=chunk_end,
                        argument_filters={
                            "to": Web3.to_checksum_address(self.system_wallet)
                        }
                    )

                    # Get outgoing transfers (from system)
                    outgoing = contract.events.Transfer.get_logs(
                        fromBlock=current_block,
                        toBlock=chunk_end,
                        argument_filters={
                            "from": Web3.to_checksum_address(self.system_wallet)
                        }
                    )

                    # Cache all transfers
                    for log in incoming:
                        cached = await self._cache_transfer(
                            log, token_type, token_address, decimals, "incoming"
                        )
                        if cached:
                            total_indexed += 1

                    for log in outgoing:
                        cached = await self._cache_transfer(
                            log, token_type, token_address, decimals, "outgoing"
                        )
                        if cached:
                            total_indexed += 1

                    chunks_processed += 1

                    # Progress log every 10 chunks
                    if chunks_processed % 10 == 0:
                        progress = (chunk_end - from_block) / total_blocks * 100
                        logger.info(
                            f"[Indexer] {token_type} progress: "
                            f"{progress:.1f}% ({total_indexed} txs cached)"
                        )

                except Exception as chunk_error:
                    logger.warning(
                        f"[Indexer] Chunk {current_block}-{chunk_end} error: "
                        f"{chunk_error}"
                    )

                current_block = chunk_end

            await self.session.commit()

            logger.success(
                f"[Indexer] {token_type} indexing complete: "
                f"{total_indexed} transactions cached"
            )

            return {
                "success": True,
                "token_type": token_type,
                "indexed": total_indexed,
                "from_block": from_block,
                "to_block": latest_block,
                "chunks_processed": chunks_processed,
            }

        except Exception as e:
            logger.error(f"[Indexer] Full index failed: {e}")
            return {"success": False, "error": str(e)}

    async def monitor_new_blocks(self) -> dict:
        """
        Monitor and index new blocks since last indexed.

        Should be called frequently (every 10-30 seconds).
        Only processes NEW blocks, so very fast and cheap.

        Returns:
            Dict with monitoring results
        """
        results = {"usdt": 0, "plex": 0, "errors": []}

        if not self.system_wallet:
            return {"success": False, "error": "System wallet not configured"}

        try:
            latest_block = self.w3.eth.block_number

            # Monitor USDT
            if self.usdt_address:
                try:
                    last_usdt = await self.get_last_indexed_block("USDT")
                    if last_usdt > 0 and last_usdt < latest_block:
                        result = await self._index_block_range(
                            token_type="USDT",
                            token_address=self.usdt_address,
                            from_block=last_usdt + 1,
                            to_block=latest_block,
                        )
                        results["usdt"] = result.get("indexed", 0)
                except Exception as e:
                    results["errors"].append(f"USDT: {e}")

            # Monitor PLEX
            if self.plex_address:
                try:
                    last_plex = await self.get_last_indexed_block("PLEX")
                    if last_plex > 0 and last_plex < latest_block:
                        result = await self._index_block_range(
                            token_type="PLEX",
                            token_address=self.plex_address,
                            from_block=last_plex + 1,
                            to_block=latest_block,
                        )
                        results["plex"] = result.get("indexed", 0)
                except Exception as e:
                    results["errors"].append(f"PLEX: {e}")

            await self.session.commit()

            new_txs = results["usdt"] + results["plex"]
            if new_txs > 0:
                logger.info(
                    f"[Indexer] New transactions: USDT={results['usdt']}, "
                    f"PLEX={results['plex']}"
                )

            results["success"] = True
            results["latest_block"] = latest_block

        except Exception as e:
            logger.error(f"[Indexer] Monitor error: {e}")
            results["success"] = False
            results["error"] = str(e)

        return results

    async def index_user_wallet(
        self,
        wallet_address: str,
        user_id: int | None = None,
    ) -> dict:
        """
        Index all transactions between a user wallet and system.

        Called when user registers or adds a wallet.

        Args:
            wallet_address: User's wallet address
            user_id: Optional user ID to link transactions

        Returns:
            Dict with indexing results
        """
        if not self.system_wallet:
            return {"success": False, "error": "System wallet not configured"}

        user_wallet = wallet_address.lower()
        results = {"usdt": 0, "plex": 0}

        try:
            latest_block = self.w3.eth.block_number
            from_block = max(0, latest_block - self.initial_scan_blocks)

            # Index USDT transfers user <-> system
            if self.usdt_address:
                usdt_result = await self._index_user_token(
                    user_wallet=user_wallet,
                    token_type="USDT",
                    token_address=self.usdt_address,
                    from_block=from_block,
                    to_block=latest_block,
                    user_id=user_id,
                )
                results["usdt"] = usdt_result.get("indexed", 0)

            # Index PLEX transfers user <-> system
            if self.plex_address:
                plex_result = await self._index_user_token(
                    user_wallet=user_wallet,
                    token_type="PLEX",
                    token_address=self.plex_address,
                    from_block=from_block,
                    to_block=latest_block,
                    user_id=user_id,
                )
                results["plex"] = plex_result.get("indexed", 0)

            await self.session.commit()

            total = results["usdt"] + results["plex"]
            logger.info(
                f"[Indexer] User wallet {mask_address(user_wallet)}: "
                f"{total} transactions indexed"
            )

            results["success"] = True

        except Exception as e:
            logger.error(f"[Indexer] User wallet index failed: {e}")
            results["success"] = False
            results["error"] = str(e)

        return results

    async def _index_block_range(
        self,
        token_type: str,
        token_address: str,
        from_block: int,
        to_block: int,
    ) -> dict:
        """Index a specific block range for system wallet."""
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        decimals = USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS
        indexed = 0

        # Process in chunks
        current = from_block
        while current < to_block:
            chunk_end = min(current + self.chunk_size, to_block)

            incoming = contract.events.Transfer.get_logs(
                fromBlock=current,
                toBlock=chunk_end,
                argument_filters={
                    "to": Web3.to_checksum_address(self.system_wallet)
                }
            )

            outgoing = contract.events.Transfer.get_logs(
                fromBlock=current,
                toBlock=chunk_end,
                argument_filters={
                    "from": Web3.to_checksum_address(self.system_wallet)
                }
            )

            for log in incoming:
                if await self._cache_transfer(
                    log, token_type, token_address, decimals, "incoming"
                ):
                    indexed += 1

            for log in outgoing:
                if await self._cache_transfer(
                    log, token_type, token_address, decimals, "outgoing"
                ):
                    indexed += 1

            current = chunk_end

        return {"indexed": indexed, "to_block": to_block}

    async def _index_user_token(
        self,
        user_wallet: str,
        token_type: str,
        token_address: str,
        from_block: int,
        to_block: int,
        user_id: int | None = None,
    ) -> dict:
        """Index user's transactions with system for a token."""
        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )
        decimals = USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS
        indexed = 0

        # User -> System (deposits/PLEX payments)
        current = from_block
        while current < to_block:
            chunk_end = min(current + self.chunk_size, to_block)

            try:
                logs = contract.events.Transfer.get_logs(
                    fromBlock=current,
                    toBlock=chunk_end,
                    argument_filters={
                        "from": Web3.to_checksum_address(user_wallet),
                        "to": Web3.to_checksum_address(self.system_wallet),
                    }
                )

                for log in logs:
                    if await self._cache_transfer(
                        log, token_type, token_address, decimals,
                        "incoming", user_id=user_id
                    ):
                        indexed += 1

            except Exception as e:
                logger.warning(f"[Indexer] User chunk error: {e}")

            current = chunk_end

        # System -> User (withdrawals/payouts)
        current = from_block
        while current < to_block:
            chunk_end = min(current + self.chunk_size, to_block)

            try:
                logs = contract.events.Transfer.get_logs(
                    fromBlock=current,
                    toBlock=chunk_end,
                    argument_filters={
                        "from": Web3.to_checksum_address(self.system_wallet),
                        "to": Web3.to_checksum_address(user_wallet),
                    }
                )

                for log in logs:
                    if await self._cache_transfer(
                        log, token_type, token_address, decimals,
                        "outgoing", user_id=user_id
                    ):
                        indexed += 1

            except Exception as e:
                logger.warning(f"[Indexer] User chunk error: {e}")

            current = chunk_end

        return {"indexed": indexed}

    async def _cache_transfer(
        self,
        log: dict,
        token_type: str,
        token_address: str,
        decimals: int,
        direction: str,
        user_id: int | None = None,
    ) -> bool:
        """Cache a single transfer log."""
        try:
            tx_hash = log["transactionHash"].hex()

            # Check if already cached
            if await self.cache_repo.tx_exists(tx_hash):
                return False

            args = log.get("args", {})
            from_addr = args.get("from", "").lower()
            to_addr = args.get("to", "").lower()
            value = args.get("value", 0)
            amount = Decimal(value) / Decimal(10 ** decimals)

            # Try to find user by wallet if not provided
            if user_id is None:
                if direction == "incoming":
                    user = await self.user_repo.find_by_wallet_address(from_addr)
                else:
                    user = await self.user_repo.find_by_wallet_address(to_addr)
                if user:
                    user_id = user.id

            await self.cache_repo.cache_transaction(
                tx_hash=tx_hash,
                block_number=log["blockNumber"],
                from_address=from_addr,
                to_address=to_addr,
                token_type=token_type,
                token_address=token_address,
                amount=amount,
                amount_raw=str(value),
                direction=direction,
                user_id=user_id,
            )

            return True

        except Exception as e:
            logger.debug(f"[Indexer] Cache error: {e}")
            return False

    # ============== QUERY METHODS (FROM CACHE) ==============

    async def get_user_total_deposits(
        self,
        wallet_address: str,
        token_type: str = "USDT",
    ) -> Decimal:
        """
        Get user's total deposits from cache.

        Zero RPC calls - pure database query.
        """
        if not self.system_wallet:
            return Decimal("0")

        return await self.cache_repo.get_total_deposits(
            user_wallet=wallet_address.lower(),
            system_wallet=self.system_wallet,
            token_type=token_type,
        )

    async def get_user_deposit_transactions(
        self,
        wallet_address: str,
        token_type: str = "USDT",
    ) -> list[BlockchainTxCache]:
        """
        Get user's deposit transactions from cache.

        Zero RPC calls - pure database query.
        """
        if not self.system_wallet:
            return []

        return await self.cache_repo.get_user_deposits(
            user_wallet=wallet_address.lower(),
            system_wallet=self.system_wallet,
            token_type=token_type,
        )

    async def get_system_incoming(
        self,
        token_type: str = "USDT",
        limit: int = 100,
    ) -> list[BlockchainTxCache]:
        """Get all incoming transactions to system wallet."""
        if not self.system_wallet:
            return []

        return await self.cache_repo.get_incoming_for_system(
            system_wallet=self.system_wallet,
            token_type=token_type,
        )

    async def get_system_outgoing(
        self,
        token_type: str = "USDT",
        limit: int = 100,
    ) -> list[BlockchainTxCache]:
        """Get all outgoing transactions from system wallet."""
        if not self.system_wallet:
            return []

        return await self.cache_repo.get_outgoing_from_system(
            system_wallet=self.system_wallet,
            token_type=token_type,
        )

    async def is_tx_indexed(self, tx_hash: str) -> bool:
        """Check if a transaction is already indexed."""
        return await self.cache_repo.tx_exists(tx_hash)

    async def get_cache_stats(self) -> dict:
        """Get statistics about cached transactions."""
        if not self.system_wallet:
            return {"error": "System wallet not configured"}

        usdt_in = await self.cache_repo.get_incoming_for_system(
            self.system_wallet, "USDT"
        )
        usdt_out = await self.cache_repo.get_outgoing_from_system(
            self.system_wallet, "USDT"
        )
        plex_in = await self.cache_repo.get_incoming_for_system(
            self.system_wallet, "PLEX"
        )
        plex_out = await self.cache_repo.get_outgoing_from_system(
            self.system_wallet, "PLEX"
        )

        last_usdt = await self.get_last_indexed_block("USDT")
        last_plex = await self.get_last_indexed_block("PLEX")
        latest = self.w3.eth.block_number

        return {
            "system_wallet": mask_address(self.system_wallet),
            "usdt": {
                "incoming_count": len(usdt_in),
                "outgoing_count": len(usdt_out),
                "incoming_total": sum(tx.amount for tx in usdt_in),
                "outgoing_total": sum(tx.amount for tx in usdt_out),
                "last_indexed_block": last_usdt,
            },
            "plex": {
                "incoming_count": len(plex_in),
                "outgoing_count": len(plex_out),
                "incoming_total": sum(tx.amount for tx in plex_in),
                "outgoing_total": sum(tx.amount for tx in plex_out),
                "last_indexed_block": last_plex,
            },
            "latest_block": latest,
            "blocks_behind_usdt": latest - last_usdt if last_usdt else "Not indexed",
            "blocks_behind_plex": latest - last_plex if last_plex else "Not indexed",
        }
