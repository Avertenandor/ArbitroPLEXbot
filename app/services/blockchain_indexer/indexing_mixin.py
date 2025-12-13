"""
Blockchain Indexer Indexing Mixin.

Provides indexing methods for blockchain transactions.
"""

from decimal import Decimal

from loguru import logger
from web3 import Web3

from app.utils.security import mask_address

from .constants import ERC20_ABI, PLEX_DECIMALS, USDT_DECIMALS


class IndexingMixin:
    """Mixin providing indexing functionality."""

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
            Dict with indexing stats including:
            - success: Whether indexing succeeded
            - token_type: Token that was indexed
            - indexed: Number of transactions indexed
            - from_block: Starting block number
            - to_block: Ending block number
            - chunks_processed: Number of block chunks processed
        """
        if not self.system_wallet:
            return {"success": False, "error": "System wallet not configured"}

        token_address = (
            self.usdt_address if token_type == "USDT" else self.plex_address
        )
        if not token_address:
            return {
                "success": False,
                "error": f"{token_type} address not configured"
            }

        try:
            latest_block = self.w3.eth.block_number

            # Determine starting block
            if from_block is None:
                last_indexed = await self.get_last_indexed_block(token_type)
                if last_indexed > 0:
                    from_block = last_indexed + 1
                    logger.info(
                        f"[Indexer] Resuming {token_type} "
                        f"from block {from_block}"
                    )
                else:
                    from_block = max(
                        0,
                        latest_block - self.initial_scan_blocks
                    )
                    logger.info(
                        f"[Indexer] Initial {token_type} "
                        f"index from {from_block}"
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

            decimals = (
                USDT_DECIMALS if token_type == "USDT" else PLEX_DECIMALS
            )
            total_indexed = 0
            chunks_processed = 0

            current_block = from_block
            while current_block < latest_block:
                chunk_end = min(
                    current_block + self.chunk_size,
                    latest_block
                )

                try:
                    # Get incoming transfers (to system)
                    incoming = contract.events.Transfer.get_logs(
                        fromBlock=current_block,
                        toBlock=chunk_end,
                        argument_filters={
                            "to": Web3.to_checksum_address(
                                self.system_wallet
                            )
                        }
                    )

                    # Get outgoing transfers (from system)
                    outgoing = contract.events.Transfer.get_logs(
                        fromBlock=current_block,
                        toBlock=chunk_end,
                        argument_filters={
                            "from": Web3.to_checksum_address(
                                self.system_wallet
                            )
                        }
                    )

                    # Cache all transfers
                    for log in incoming:
                        cached = await self._cache_transfer(
                            log,
                            token_type,
                            token_address,
                            decimals,
                            "incoming"
                        )
                        if cached:
                            total_indexed += 1

                    for log in outgoing:
                        cached = await self._cache_transfer(
                            log,
                            token_type,
                            token_address,
                            decimals,
                            "outgoing"
                        )
                        if cached:
                            total_indexed += 1

                    chunks_processed += 1

                    # Progress log every 10 chunks
                    if chunks_processed % 10 == 0:
                        progress = (
                            (chunk_end - from_block) / total_blocks * 100
                        )
                        logger.info(
                            f"[Indexer] {token_type} progress: "
                            f"{progress:.1f}% ({total_indexed} txs cached)"
                        )

                except Exception as chunk_error:
                    logger.warning(
                        f"[Indexer] Chunk {current_block}-{chunk_end} "
                        f"error: {chunk_error}"
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
            Dict with indexing results including:
            - success: Whether indexing succeeded
            - usdt: Number of USDT transactions indexed
            - plex: Number of PLEX transactions indexed
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
        """
        Index a specific block range for system wallet.

        Args:
            token_type: Token type (USDT or PLEX)
            token_address: Token contract address
            from_block: Starting block number
            to_block: Ending block number

        Returns:
            Dict with number of transactions indexed and last block
        """
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
        """
        Index user's transactions with system for a token.

        Args:
            user_wallet: User's wallet address
            token_type: Token type (USDT or PLEX)
            token_address: Token contract address
            from_block: Starting block number
            to_block: Ending block number
            user_id: Optional user ID to link transactions

        Returns:
            Dict with number of transactions indexed
        """
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
                        log,
                        token_type,
                        token_address,
                        decimals,
                        "incoming",
                        user_id=user_id
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
                        log,
                        token_type,
                        token_address,
                        decimals,
                        "outgoing",
                        user_id=user_id
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
        """
        Cache a single transfer log.

        Args:
            log: Transfer event log
            token_type: Token type (USDT or PLEX)
            token_address: Token contract address
            decimals: Token decimals for amount conversion
            direction: Transfer direction (incoming or outgoing)
            user_id: Optional user ID to link transaction

        Returns:
            True if transaction was cached, False if already exists
        """
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
                    user = await self.user_repo.find_by_wallet_address(
                        from_addr
                    )
                else:
                    user = await self.user_repo.find_by_wallet_address(
                        to_addr
                    )
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
