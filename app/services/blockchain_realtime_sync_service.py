"""
Blockchain Real-Time Sync Service.

Handles real-time synchronization of blockchain transactions.
Uses incremental polling to keep the cache up-to-date.
"""

from datetime import UTC, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import Web3

from app.config.settings import settings
from app.models.blockchain_sync_state import BlockchainSyncState
from app.models.blockchain_tx_cache import BlockchainTxCache
from app.repositories.user_repository import UserRepository


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


class BlockchainRealtimeSyncService:
    """
    Real-time blockchain synchronization service.

    Features:
    - Incremental sync from last synced block
    - Automatic user linking
    - Fast local lookups
    """

    def __init__(
        self,
        session: AsyncSession,
        w3: Web3 | None = None,
    ):
        """
        Initialize service.

        Args:
            session: Database session
            w3: Web3 instance (optional)
        """
        self.session = session
        self.w3 = w3
        self.user_repo = UserRepository(session)

        # Configuration
        self.system_wallet = settings.system_wallet_address.lower()
        self.usdt_address = settings.usdt_contract_address.lower()
        self.plex_address = settings.auth_plex_token_address.lower()

    async def get_sync_state(self, token_type: str) -> BlockchainSyncState | None:
        """Get sync state for a token type."""
        result = await self.session.execute(
            select(BlockchainSyncState)
            .where(BlockchainSyncState.token_type == token_type)
        )
        return result.scalar_one_or_none()

    async def get_or_create_sync_state(self, token_type: str) -> BlockchainSyncState:
        """Get or create sync state for a token type."""
        state = await self.get_sync_state(token_type)
        if state:
            return state

        state = BlockchainSyncState(
            token_type=token_type,
            first_synced_block=0,
            last_synced_block=0,
            total_transactions=0,
            incoming_count=0,
            outgoing_count=0,
            full_sync_completed=False,
        )
        self.session.add(state)
        await self.session.flush()
        return state

    async def tx_exists(self, tx_hash: str) -> bool:
        """Check if transaction is already cached."""
        result = await self.session.execute(
            select(BlockchainTxCache.id)
            .where(BlockchainTxCache.tx_hash == tx_hash)
            .limit(1)
        )
        return result.scalar() is not None

    async def get_user_deposits_from_cache(
        self,
        user_wallet: str,
        token_type: str = "USDT",
    ) -> dict:
        """
        Get user's deposits from local cache.

        This is the FAST path - no blockchain queries needed!

        Args:
            user_wallet: User's wallet address
            token_type: Token type (USDT, PLEX)

        Returns:
            Dict with total_amount, tx_count, transactions
        """
        try:
            user_wallet_lower = user_wallet.lower()

            result = await self.session.execute(
                select(BlockchainTxCache)
                .where(
                    BlockchainTxCache.from_address == user_wallet_lower,
                    BlockchainTxCache.to_address == self.system_wallet,
                    BlockchainTxCache.token_type == token_type,
                    BlockchainTxCache.direction == "incoming",
                )
                .order_by(BlockchainTxCache.block_number.asc())
            )
            deposits = result.scalars().all()

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
                f"[Cache Lookup] User {user_wallet[:10]}...: "
                f"{len(deposits)} deposits, {total} {token_type}"
            )

            return {
                "success": True,
                "total_amount": total,
                "tx_count": len(deposits),
                "transactions": transactions,
                "from_cache": True,
            }

        except Exception as e:
            logger.error(f"[Cache Lookup] Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_amount": Decimal("0"),
                "tx_count": 0,
                "transactions": [],
            }

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
        block_timestamp: datetime | None = None,
    ) -> BlockchainTxCache | None:
        """Cache a single transaction."""
        try:
            # Check for duplicate
            if await self.tx_exists(tx_hash):
                return None

            # Determine user_id by matching wallet addresses
            user_id = None
            user_wallet = from_address if direction == "incoming" else to_address
            user = await self.user_repo.get_by_wallet_address(user_wallet)
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
            return tx

        except Exception as e:
            logger.error(f"Error caching transaction {tx_hash}: {e}")
            return None

    async def sync_new_blocks(
        self,
        token_type: str,
        token_address: str,
        max_blocks: int = 1000,
    ) -> int:
        """
        Sync new blocks for a token type.

        Args:
            token_type: USDT or PLEX
            token_address: Token contract address
            max_blocks: Maximum blocks to sync in one run

        Returns:
            Number of new transactions cached
        """
        if not self.w3:
            logger.error("[RT Sync] Web3 not initialized")
            return 0

        state = await self.get_or_create_sync_state(token_type)

        current_block = self.w3.eth.block_number
        from_block = (
            state.last_synced_block + 1
            if state.last_synced_block > 0
            else current_block - 100
        )
        to_block = min(from_block + max_blocks, current_block)

        if from_block >= current_block:
            logger.debug(f"[RT Sync] {token_type}: Already synced to current block")
            return 0

        logger.info(f"[RT Sync] {token_type}: Syncing blocks {from_block} to {to_block}")

        contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )

        decimals = USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS
        cached_count = 0
        system_wallet_checksum = Web3.to_checksum_address(
            self.system_wallet
        )

        try:
            # Get incoming transfers
            incoming_logs = contract.events.Transfer.get_logs(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters={"to": system_wallet_checksum}
            )

            # Get outgoing transfers
            outgoing_logs = contract.events.Transfer.get_logs(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters={"from": system_wallet_checksum}
            )

            # Process incoming
            for log in incoming_logs:
                args = log.get("args", {})
                tx_hash = log["transactionHash"].hex()
                amount = Decimal(args.get("value", 0)) / Decimal(10 ** decimals)

                tx = await self.cache_transaction(
                    tx_hash=tx_hash,
                    block_number=log["blockNumber"],
                    from_address=args.get("from", ""),
                    to_address=args.get("to", ""),
                    amount=amount,
                    token_type=token_type,
                    token_address=token_address,
                    direction="incoming",
                )
                if tx:
                    cached_count += 1
                    state.incoming_count += 1

            # Process outgoing
            for log in outgoing_logs:
                args = log.get("args", {})
                tx_hash = log["transactionHash"].hex()
                amount = Decimal(args.get("value", 0)) / Decimal(10 ** decimals)

                tx = await self.cache_transaction(
                    tx_hash=tx_hash,
                    block_number=log["blockNumber"],
                    from_address=args.get("from", ""),
                    to_address=args.get("to", ""),
                    amount=amount,
                    token_type=token_type,
                    token_address=token_address,
                    direction="outgoing",
                )
                if tx:
                    cached_count += 1
                    state.outgoing_count += 1

            # Update sync state
            state.last_synced_block = to_block
            state.total_transactions += cached_count
            state.updated_at = datetime.now(UTC)

            await self.session.commit()

            if cached_count > 0:
                logger.info(
                    f"[RT Sync] {token_type}: Cached {cached_count} transactions "
                    f"(in={len(incoming_logs)}, out={len(outgoing_logs)})"
                )

            return cached_count

        except Exception as e:
            state.last_error = str(e)
            state.error_count += 1
            await self.session.commit()
            logger.error(f"[RT Sync] {token_type}: Error syncing: {e}")
            return 0

    async def sync_all_tokens(self) -> dict:
        """
        Sync all tokens (USDT and PLEX).

        Returns:
            Dict with counts per token
        """
        results = {}

        # Sync USDT
        usdt_count = await self.sync_new_blocks(
            token_type="USDT",
            token_address=self.usdt_address,
        )
        results["USDT"] = usdt_count

        # Sync PLEX
        plex_count = await self.sync_new_blocks(
            token_type="PLEX",
            token_address=self.plex_address,
        )
        results["PLEX"] = plex_count

        return results

    async def link_user_to_transactions(self, user_id: int, wallet_address: str) -> int:
        """
        Link existing cached transactions to a user.

        Called when user registers their wallet.

        Args:
            user_id: User ID
            wallet_address: User's wallet address

        Returns:
            Number of transactions linked
        """
        wallet_lower = wallet_address.lower()

        # Find all transactions from/to this wallet that aren't linked
        result = await self.session.execute(
            select(BlockchainTxCache)
            .where(
                BlockchainTxCache.user_id.is_(None),
                (BlockchainTxCache.from_address == wallet_lower) |
                (BlockchainTxCache.to_address == wallet_lower)
            )
        )
        transactions = result.scalars().all()

        linked = 0
        for tx in transactions:
            tx.user_id = user_id
            linked += 1

        if linked > 0:
            await self.session.commit()
            logger.info(f"[Cache] Linked {linked} transactions to user {user_id}")

        return linked
