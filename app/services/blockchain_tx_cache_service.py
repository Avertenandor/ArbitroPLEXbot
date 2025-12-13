"""
Blockchain Transaction Cache Service.

Provides intelligent caching of blockchain transactions:
- Scans blockchain only for new blocks
- Uses cached data for historical queries
- Automatically links transactions to users
"""

from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from app.config.operational_constants import MAX_BLOCKS_PER_SCAN
from app.config.settings import settings
from app.models.blockchain_tx_cache import BlockchainTxCache
from app.repositories.blockchain_tx_cache_repository import BlockchainTxCacheRepository
from app.repositories.user_repository import UserRepository
from app.utils.security import mask_address


# Token decimals
USDT_DECIMALS = 18
PLEX_DECIMALS = 18

# ERC20 Transfer event signature
TRANSFER_EVENT_SIGNATURE = Web3.keccak(text="Transfer(address,address,uint256)").hex()

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


class BlockchainTxCacheService:
    """
    Service for caching and retrieving blockchain transactions.

    Key features:
    - Incremental scanning (only new blocks)
    - Automatic user linking by wallet address
    - Fast historical queries from cache
    - Reduces RPC calls by 90%+
    """

    def __init__(
        self,
        session: AsyncSession,
        w3: Web3 | None = None,
    ):
        """
        Initialize cache service.

        Args:
            session: Database session
            w3: Web3 instance (optional, will be created if not provided)
        """
        self.session = session
        self.repo = BlockchainTxCacheRepository(session)
        self.user_repo = UserRepository(session)
        self.w3 = w3

        # Configuration
        sys_wallet = settings.system_wallet_address
        self.system_wallet = sys_wallet.lower() if sys_wallet else None

        usdt_addr = settings.usdt_contract_address
        self.usdt_address = usdt_addr.lower() if usdt_addr else None

        plex_addr = settings.auth_plex_token_address
        self.plex_address = plex_addr.lower() if plex_addr else None

        # Scan settings
        self.chunk_size = 2000  # Blocks per scan chunk
        self.max_blocks_per_scan = MAX_BLOCKS_PER_SCAN

    async def get_cached_deposits(
        self,
        user_wallet: str,
        token_type: str = "USDT",
    ) -> dict:
        """
        Get user's deposits from cache.

        Args:
            user_wallet: User's wallet address
            token_type: Token type (USDT, PLEX)

        Returns:
            Dict with total_amount, tx_count, transactions, success
        """
        if not self.system_wallet:
            return {
                "success": False,
                "error": "System wallet not configured",
                "total_amount": Decimal("0"),
                "tx_count": 0,
                "transactions": [],
            }

        try:
            deposits = await self.repo.get_user_deposits(
                user_wallet=user_wallet,
                system_wallet=self.system_wallet,
                token_type=token_type,
            )

            transactions = [
                {
                    "tx_hash": tx.tx_hash,
                    "amount": tx.amount,
                    "block": tx.block_number,
                    "timestamp": tx.block_timestamp,
                }
                for tx in deposits
            ]

            total = sum(tx.amount for tx in deposits)

            logger.info(
                f"[TX Cache] Found {len(deposits)} cached deposits "
                f"from {mask_address(user_wallet)}, total: {total} {token_type}"
            )

            return {
                "success": True,
                "total_amount": total,
                "tx_count": len(deposits),
                "transactions": transactions,
                "from_cache": True,
            }

        except Exception as e:
            logger.error(f"[TX Cache] Error getting cached deposits: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_amount": Decimal("0"),
                "tx_count": 0,
                "transactions": [],
            }

    async def is_tx_cached(self, tx_hash: str) -> bool:
        """Check if transaction is already cached."""
        return await self.repo.tx_exists(tx_hash)

    async def get_cached_tx(self, tx_hash: str) -> BlockchainTxCache | None:
        """Get cached transaction by hash."""
        return await self.repo.get_by_tx_hash(tx_hash)

    async def cache_transaction_from_log(
        self,
        log: dict,
        token_type: str,
        token_address: str,
        decimals: int = 18,
    ) -> BlockchainTxCache | None:
        """
        Cache a transaction from blockchain event log.

        Args:
            log: Event log from Web3
            token_type: Token type (USDT, PLEX)
            token_address: Token contract address
            decimals: Token decimals

        Returns:
            Cached transaction or None
        """
        try:
            tx_hash = log["transactionHash"].hex()

            # Check if already cached
            if await self.is_tx_cached(tx_hash):
                return await self.get_cached_tx(tx_hash)

            args = log.get("args", {})
            from_addr = args.get("from", "").lower()
            to_addr = args.get("to", "").lower()
            value = args.get("value", 0)

            amount = Decimal(value) / Decimal(10 ** decimals)

            # Determine direction relative to system wallet
            direction = "internal"
            if self.system_wallet:
                if to_addr == self.system_wallet:
                    direction = "incoming"
                elif from_addr == self.system_wallet:
                    direction = "outgoing"

            # Try to find user by wallet
            user_id = None
            if direction == "incoming":
                user = await self.user_repo.find_by_wallet_address(from_addr)
                if user:
                    user_id = user.id
            elif direction == "outgoing":
                user = await self.user_repo.find_by_wallet_address(to_addr)
                if user:
                    user_id = user.id

            # Cache the transaction
            cached = await self.repo.cache_transaction(
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

            if cached and cached.id:
                logger.debug(
                    f"[TX Cache] Cached {token_type} transfer: "
                    f"{mask_address(from_addr)} -> {mask_address(to_addr)}, "
                    f"amount={amount}, block={log['blockNumber']}"
                )

            return cached

        except Exception as e:
            logger.error(f"[TX Cache] Error caching transaction: {e}")
            return None

    async def scan_and_cache_transfers(
        self,
        w3: Web3,
        token_type: str,
        token_address: str,
        from_block: int | None = None,
        to_block: int | str = "latest",
    ) -> int:
        """
        Scan blockchain for transfers and cache them.

        Only scans blocks newer than what we have cached.

        Args:
            w3: Web3 instance
            token_type: Token type (USDT, PLEX)
            token_address: Token contract address
            from_block: Starting block (auto-detect if None)
            to_block: Ending block

        Returns:
            Number of new transactions cached
        """
        if not self.system_wallet:
            logger.warning("[TX Cache] System wallet not configured, skipping scan")
            return 0

        try:
            # Get latest block we have cached
            if from_block is None:
                cached_block = await self.repo.get_latest_block(token_type)
                # Start from cached block + 1, or go back max_blocks if no cache
                if cached_block > 0:
                    from_block = cached_block + 1
                else:
                    latest = w3.eth.block_number
                    from_block = max(0, latest - self.max_blocks_per_scan)

            # Resolve to_block
            if to_block == "latest":
                to_block = w3.eth.block_number

            # Limit scan range
            blocks_to_scan = to_block - from_block
            if blocks_to_scan <= 0:
                logger.debug(f"[TX Cache] {token_type}: No new blocks to scan")
                return 0

            if blocks_to_scan > self.max_blocks_per_scan:
                to_block = from_block + self.max_blocks_per_scan
                blocks_to_scan = self.max_blocks_per_scan

            logger.info(
                f"[TX Cache] Scanning {token_type}: blocks {from_block} to {to_block} "
                f"({blocks_to_scan} blocks)"
            )

            # Create contract instance
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=ERC20_ABI
            )

            decimals = USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS
            total_cached = 0

            # Scan in chunks
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

                    # Cache all found transactions
                    for log in incoming_logs + outgoing_logs:
                        cached = await self.cache_transaction_from_log(
                            log=log,
                            token_type=token_type,
                            token_address=token_address,
                            decimals=decimals,
                        )
                        if cached:
                            total_cached += 1

                    logger.debug(
                        f"[TX Cache] Chunk {current_block}-{chunk_end}: "
                        f"{len(incoming_logs)} incoming, {len(outgoing_logs)} outgoing"
                    )

                except Exception as chunk_error:
                    logger.warning(
                        f"[TX Cache] Chunk {current_block}-{chunk_end} failed: {chunk_error}"
                    )

                current_block = chunk_end

            # Commit changes
            await self.session.commit()

            logger.info(
                f"[TX Cache] Scan complete for {token_type}: "
                f"cached {total_cached} new transactions"
            )

            return total_cached

        except Exception as e:
            logger.error(f"[TX Cache] Scan failed for {token_type}: {e}")
            return 0

    async def scan_all_tokens(self, w3: Web3) -> dict:
        """
        Scan and cache transactions for all supported tokens.

        Args:
            w3: Web3 instance

        Returns:
            Dict with scan results per token
        """
        results = {}

        # Scan USDT
        if self.usdt_address:
            results["USDT"] = await self.scan_and_cache_transfers(
                w3=w3,
                token_type="USDT",
                token_address=self.usdt_address,
            )
        else:
            results["USDT"] = 0
            logger.warning("[TX Cache] USDT address not configured")

        # Scan PLEX
        if self.plex_address:
            results["PLEX"] = await self.scan_and_cache_transfers(
                w3=w3,
                token_type="PLEX",
                token_address=self.plex_address,
            )
        else:
            results["PLEX"] = 0
            logger.warning("[TX Cache] PLEX address not configured")

        return results

    async def verify_deposit_from_cache(
        self,
        user_wallet: str,
        min_amount: Decimal,
        token_type: str = "USDT",
    ) -> dict:
        """
        Verify deposit using cache first, then blockchain if needed.

        Args:
            user_wallet: User's wallet address
            min_amount: Minimum required amount
            token_type: Token type

        Returns:
            Dict with success, total_amount, transactions
        """
        # First check cache
        cached = await self.get_cached_deposits(user_wallet, token_type)

        if cached["success"] and cached["total_amount"] >= min_amount:
            logger.info(
                f"[TX Cache] Deposit verified from cache: "
                f"{cached['total_amount']} >= {min_amount} {token_type}"
            )
            return cached

        # If not enough in cache and we have Web3, scan blockchain
        if self.w3 and cached["total_amount"] < min_amount:
            logger.info(
                f"[TX Cache] Cache insufficient ({cached['total_amount']} < {min_amount}), "
                f"scanning blockchain..."
            )

            token_address = self.usdt_address if token_type == "USDT" else self.plex_address
            if token_address:
                await self.scan_and_cache_transfers(
                    w3=self.w3,
                    token_type=token_type,
                    token_address=token_address,
                )

                # Re-check cache after scan
                cached = await self.get_cached_deposits(user_wallet, token_type)

        return cached

    async def get_system_wallet_stats(self) -> dict:
        """
        Get statistics for system wallet transactions.

        Returns:
            Dict with incoming/outgoing counts and totals
        """
        if not self.system_wallet:
            return {"error": "System wallet not configured"}

        zero = Decimal("0")
        stats = {
            "system_wallet": self.system_wallet,
            "usdt": {
                "incoming": 0, "outgoing": 0,
                "total_in": zero, "total_out": zero,
            },
            "plex": {
                "incoming": 0, "outgoing": 0,
                "total_in": zero, "total_out": zero,
            },
        }

        # USDT stats
        usdt_incoming = await self.repo.get_incoming_for_system(
            self.system_wallet, "USDT"
        )
        usdt_outgoing = await self.repo.get_outgoing_from_system(
            self.system_wallet, "USDT"
        )
        stats["usdt"]["incoming"] = len(usdt_incoming)
        stats["usdt"]["outgoing"] = len(usdt_outgoing)
        stats["usdt"]["total_in"] = sum(tx.amount for tx in usdt_incoming)
        stats["usdt"]["total_out"] = sum(tx.amount for tx in usdt_outgoing)

        # PLEX stats
        plex_incoming = await self.repo.get_incoming_for_system(
            self.system_wallet, "PLEX"
        )
        plex_outgoing = await self.repo.get_outgoing_from_system(
            self.system_wallet, "PLEX"
        )
        stats["plex"]["incoming"] = len(plex_incoming)
        stats["plex"]["outgoing"] = len(plex_outgoing)
        stats["plex"]["total_in"] = sum(tx.amount for tx in plex_incoming)
        stats["plex"]["total_out"] = sum(tx.amount for tx in plex_outgoing)

        return stats

    async def link_unprocessed_to_users(self) -> int:
        """
        Link unprocessed transactions to users by wallet address.

        Returns:
            Number of transactions linked
        """
        unprocessed = await self.repo.get_unprocessed(limit=100)
        linked = 0

        for tx in unprocessed:
            # Try to find user by from_address (for incoming)
            if tx.direction == "incoming" and not tx.user_id:
                user = await self.user_repo.find_by_wallet_address(tx.from_address)
                if user:
                    tx.user_id = user.id
                    linked += 1

            # Try to find user by to_address (for outgoing)
            elif tx.direction == "outgoing" and not tx.user_id:
                user = await self.user_repo.find_by_wallet_address(tx.to_address)
                if user:
                    tx.user_id = user.id
                    linked += 1

        if linked > 0:
            await self.session.commit()
            logger.info(f"[TX Cache] Linked {linked} transactions to users")

        return linked
