"""
Blockchain Transaction Cache repository.

Data access layer for cached blockchain transactions.
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.blockchain_tx_cache import BlockchainTxCache
from app.repositories.base import BaseRepository


class BlockchainTxCacheRepository(BaseRepository[BlockchainTxCache]):
    """Repository for blockchain transaction cache."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository."""
        super().__init__(BlockchainTxCache, session)

    async def get_by_tx_hash(self, tx_hash: str) -> BlockchainTxCache | None:
        """
        Get cached transaction by hash.

        Args:
            tx_hash: Transaction hash (with or without 0x prefix)

        Returns:
            Cached transaction or None
        """
        # Normalize hash
        normalized = tx_hash.lower()
        if not normalized.startswith("0x"):
            normalized = f"0x{normalized}"

        return await self.get_by(tx_hash=normalized)

    async def tx_exists(self, tx_hash: str) -> bool:
        """
        Check if transaction is already cached.

        Args:
            tx_hash: Transaction hash

        Returns:
            True if cached
        """
        return await self.get_by_tx_hash(tx_hash) is not None

    async def get_by_address(
        self,
        address: str,
        token_type: str | None = None,
        direction: str | None = None,
        limit: int = 100,
    ) -> list[BlockchainTxCache]:
        """
        Get transactions involving an address.

        Args:
            address: Wallet address
            token_type: Filter by token (USDT, PLEX, BNB)
            direction: Filter by direction (incoming, outgoing)
            limit: Max results

        Returns:
            List of cached transactions
        """
        addr = address.lower()

        conditions = [
            or_(
                BlockchainTxCache.from_address == addr,
                BlockchainTxCache.to_address == addr,
            )
        ]

        if token_type:
            conditions.append(BlockchainTxCache.token_type == token_type.upper())
        if direction:
            conditions.append(BlockchainTxCache.direction == direction)

        query = (
            select(BlockchainTxCache)
            .where(and_(*conditions))
            .order_by(BlockchainTxCache.block_number.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_user_deposits(
        self,
        user_wallet: str,
        system_wallet: str,
        token_type: str = "USDT",
    ) -> list[BlockchainTxCache]:
        """
        Get all deposits from user to system wallet.

        Args:
            user_wallet: User's wallet address
            system_wallet: System wallet address
            token_type: Token type (default USDT)

        Returns:
            List of deposit transactions
        """
        query = (
            select(BlockchainTxCache)
            .where(
                and_(
                    BlockchainTxCache.from_address == user_wallet.lower(),
                    BlockchainTxCache.to_address == system_wallet.lower(),
                    BlockchainTxCache.token_type == token_type.upper(),
                    BlockchainTxCache.direction == "incoming",
                )
            )
            .order_by(BlockchainTxCache.block_number.asc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_deposits(
        self,
        user_wallet: str,
        system_wallet: str,
        token_type: str = "USDT",
    ) -> Decimal:
        """
        Get total deposited amount from user.

        Args:
            user_wallet: User's wallet address
            system_wallet: System wallet address
            token_type: Token type

        Returns:
            Total amount deposited
        """
        query = (
            select(func.coalesce(func.sum(BlockchainTxCache.amount), 0))
            .where(
                and_(
                    BlockchainTxCache.from_address == user_wallet.lower(),
                    BlockchainTxCache.to_address == system_wallet.lower(),
                    BlockchainTxCache.token_type == token_type.upper(),
                    BlockchainTxCache.direction == "incoming",
                )
            )
        )

        result = await self.session.execute(query)
        total = result.scalar()
        return Decimal(str(total)) if total else Decimal("0")

    async def get_unprocessed(
        self,
        direction: str | None = None,
        token_type: str | None = None,
        limit: int = 50,
    ) -> list[BlockchainTxCache]:
        """
        Get unprocessed transactions.

        Args:
            direction: Filter by direction
            token_type: Filter by token
            limit: Max results

        Returns:
            List of unprocessed transactions
        """
        conditions = [BlockchainTxCache.is_processed == False]  # noqa: E712

        if direction:
            conditions.append(BlockchainTxCache.direction == direction)
        if token_type:
            conditions.append(BlockchainTxCache.token_type == token_type.upper())

        query = (
            select(BlockchainTxCache)
            .where(and_(*conditions))
            .order_by(BlockchainTxCache.block_number.asc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def mark_processed(
        self,
        tx_id: int,
        notes: str | None = None,
        user_id: int | None = None,
        deposit_id: int | None = None,
        withdrawal_id: int | None = None,
    ) -> bool:
        """
        Mark transaction as processed.

        Args:
            tx_id: Transaction cache ID
            notes: Processing notes
            user_id: Link to user
            deposit_id: Link to deposit
            withdrawal_id: Link to withdrawal

        Returns:
            True if updated
        """
        tx = await self.get_by_id(tx_id)
        if not tx:
            return False

        tx.is_processed = True
        tx.processed_at = datetime.now(UTC)
        tx.processing_notes = notes

        if user_id:
            tx.user_id = user_id
        if deposit_id:
            tx.deposit_id = deposit_id
        if withdrawal_id:
            tx.withdrawal_id = withdrawal_id

        return True

    async def get_latest_block(self, token_type: str) -> int:
        """
        Get the latest block number we have cached for a token type.

        Args:
            token_type: Token type (USDT, PLEX)

        Returns:
            Latest block number or 0
        """
        query = (
            select(func.max(BlockchainTxCache.block_number))
            .where(BlockchainTxCache.token_type == token_type.upper())
        )

        result = await self.session.execute(query)
        block = result.scalar()
        return block if block else 0

    async def cache_transaction(
        self,
        tx_hash: str,
        block_number: int,
        from_address: str,
        to_address: str,
        token_type: str,
        amount: Decimal,
        direction: str,
        token_address: str | None = None,
        amount_raw: str | None = None,
        block_timestamp: datetime | None = None,
        user_id: int | None = None,
    ) -> BlockchainTxCache | None:
        """
        Cache a new transaction (or return existing if duplicate).

        Args:
            tx_hash: Transaction hash
            block_number: Block number
            from_address: Sender address
            to_address: Receiver address
            token_type: Token type (USDT, PLEX, BNB)
            amount: Amount transferred
            direction: Direction (incoming, outgoing)
            token_address: Token contract address
            amount_raw: Raw wei amount
            block_timestamp: Block timestamp
            user_id: Optional user ID

        Returns:
            Cached transaction or None if duplicate
        """
        # Check if already cached
        existing = await self.get_by_tx_hash(tx_hash)
        if existing:
            return existing

        # Create new cache entry
        tx = BlockchainTxCache(
            tx_hash=tx_hash.lower(),
            block_number=block_number,
            from_address=from_address.lower(),
            to_address=to_address.lower(),
            token_type=token_type.upper(),
            token_address=token_address.lower() if token_address else None,
            amount=amount,
            amount_raw=amount_raw,
            direction=direction,
            block_timestamp=block_timestamp,
            user_id=user_id,
            status="confirmed",
            is_processed=False,
        )

        self.session.add(tx)
        return tx

    async def get_incoming_for_system(
        self,
        system_wallet: str,
        token_type: str,
        from_block: int | None = None,
    ) -> list[BlockchainTxCache]:
        """
        Get all incoming transactions to system wallet.

        Args:
            system_wallet: System wallet address
            token_type: Token type
            from_block: Optional starting block

        Returns:
            List of incoming transactions
        """
        conditions = [
            BlockchainTxCache.to_address == system_wallet.lower(),
            BlockchainTxCache.token_type == token_type.upper(),
            BlockchainTxCache.direction == "incoming",
        ]

        if from_block:
            conditions.append(BlockchainTxCache.block_number >= from_block)

        query = (
            select(BlockchainTxCache)
            .where(and_(*conditions))
            .order_by(BlockchainTxCache.block_number.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_outgoing_from_system(
        self,
        system_wallet: str,
        token_type: str,
        from_block: int | None = None,
    ) -> list[BlockchainTxCache]:
        """
        Get all outgoing transactions from system wallet.

        Args:
            system_wallet: System wallet address
            token_type: Token type
            from_block: Optional starting block

        Returns:
            List of outgoing transactions
        """
        conditions = [
            BlockchainTxCache.from_address == system_wallet.lower(),
            BlockchainTxCache.token_type == token_type.upper(),
            BlockchainTxCache.direction == "outgoing",
        ]

        if from_block:
            conditions.append(BlockchainTxCache.block_number >= from_block)

        query = (
            select(BlockchainTxCache)
            .where(and_(*conditions))
            .order_by(BlockchainTxCache.block_number.desc())
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())
