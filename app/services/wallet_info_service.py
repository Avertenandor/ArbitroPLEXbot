"""
Wallet info service.

Provides comprehensive wallet information:
- Token balances (PLEX, USDT, BNB)
- Transaction history from NodeReal Enhanced API
- Balance formatting and caching
"""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import aiohttp
from loguru import logger

from app.config.business_constants import PLEX_CONTRACT_ADDRESS
from app.config.settings import settings
from app.services.blockchain.rpc_rate_limiter import RPCRateLimiter
from app.services.blockchain_service import get_blockchain_service
from app.utils.security import mask_address
from app.config.constants import BSCSCAN_TX_URL, RPC_MAX_RPS


# Transaction types for display
TX_TYPE_TRANSFER_IN = "in"
TX_TYPE_TRANSFER_OUT = "out"

# Token contract addresses
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"


@dataclass
class WalletBalance:
    """Wallet balance data."""

    address: str
    bnb_balance: Decimal
    usdt_balance: Decimal
    plex_balance: Decimal
    last_updated: datetime

    @property
    def bnb_formatted(self) -> str:
        """Format BNB balance with 6 decimals."""
        return f"{self.bnb_balance:.6f}"

    @property
    def usdt_formatted(self) -> str:
        """Format USDT balance with 2 decimals."""
        return f"{self.usdt_balance:.2f}"

    @property
    def plex_formatted(self) -> str:
        """Format PLEX balance as integer."""
        return f"{int(self.plex_balance):,}"


@dataclass
class TokenTransaction:
    """Token transaction data."""

    tx_hash: str
    block_number: int
    timestamp: datetime
    from_address: str
    to_address: str
    value: Decimal
    token_symbol: str
    token_name: str
    direction: str  # "in" or "out"

    @property
    def short_hash(self) -> str:
        """Get shortened tx hash for display."""
        return f"{self.tx_hash[:10]}...{self.tx_hash[-8:]}"

    @property
    def bscscan_url(self) -> str:
        """Get BSCScan URL for transaction."""
        return f"{BSCSCAN_TX_URL}/{self.tx_hash}"

    @property
    def formatted_value(self) -> str:
        """Format value based on token."""
        if self.token_symbol == "PLEX":
            return f"{int(self.value):,}"
        elif self.token_symbol == "BNB":
            return f"{self.value:.6f}"
        else:
            return f"{self.value:.2f}"

    @property
    def direction_emoji(self) -> str:
        """Get emoji for direction."""
        return "📥" if self.direction == TX_TYPE_TRANSFER_IN else "📤"


class WalletInfoService:
    """
    Service for retrieving comprehensive wallet information.

    Uses:
    - BlockchainService for balance queries (RPC)
    - eth_getLogs for token transfer history (standard RPC method)
    """

    # ERC-20 Transfer event signature
    TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

    def __init__(self) -> None:
        """Initialize wallet info service."""
        self.rpc_url = settings.rpc_url
        self._session: aiohttp.ClientSession | None = None
        self._rate_limiter = RPCRateLimiter(max_rps=RPC_MAX_RPS)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _rpc_call(self, method: str, params: list) -> Any:
        """
        Make JSON-RPC call with rate limiting.

        Args:
            method: RPC method name
            params: RPC parameters

        Returns:
            Result or None on error
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }

        try:
            async with self._rate_limiter:
                session = await self._get_session()
                async with session.post(
                    self.rpc_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "error" in data:
                            logger.debug(f"RPC error: {data['error']}")
                            return None
                        return data.get("result")
                    else:
                        logger.warning(f"RPC error: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"RPC request failed: {e}")
            return None

    async def get_wallet_balances(self, wallet_address: str) -> WalletBalance | None:
        """
        Get all token balances for wallet.

        Args:
            wallet_address: BSC wallet address

        Returns:
            WalletBalance or None on error
        """
        try:
            blockchain = get_blockchain_service()

            # Get all balances in parallel
            bnb_task = blockchain.get_native_balance(wallet_address)
            usdt_task = blockchain.get_usdt_balance(wallet_address)
            plex_task = blockchain.get_plex_balance(wallet_address)

            bnb, usdt, plex = await asyncio.gather(
                bnb_task, usdt_task, plex_task,
                return_exceptions=True
            )

            # Handle exceptions
            bnb_balance = bnb if isinstance(bnb, Decimal) else Decimal("0")
            usdt_balance = usdt if isinstance(usdt, Decimal) else Decimal("0")
            plex_balance = plex if isinstance(plex, Decimal) else Decimal("0")

            return WalletBalance(
                address=wallet_address,
                bnb_balance=bnb_balance,
                usdt_balance=usdt_balance,
                plex_balance=plex_balance,
                last_updated=datetime.now(UTC),
            )

        except Exception as e:
            error_msg = (
                f"Failed to get wallet balances for "
                f"{mask_address(wallet_address)}: {e}"
            )
            logger.error(error_msg)
            return None

    async def _get_current_block(self) -> int:
        """Get current block number."""
        result = await self._rpc_call("eth_blockNumber", [])
        if result:
            return int(result, 16)
        return 0

    async def get_token_transactions(
        self,
        wallet_address: str,
        contract_address: str,
        token_symbol: str,
        token_name: str,
        decimals: int,
        limit: int = 20,
    ) -> list[TokenTransaction]:
        """
        Get BEP-20 token transaction history using eth_getLogs.

        Args:
            wallet_address: Wallet address
            contract_address: Token contract address
            token_symbol: Token symbol (USDT, PLEX)
            token_name: Token name for display
            decimals: Token decimals
            limit: Max transactions to return

        Returns:
            List of TokenTransaction
        """
        wallet_padded = "0x" + wallet_address.lower()[2:].zfill(64)

        # Get current block
        current_block = await self._get_current_block()
        if current_block == 0:
            return []

        # Search last ~100k blocks (~3-4 days)
        from_block = max(0, current_block - 100000)

        transactions = []

        # Get incoming transfers (to wallet)
        incoming_logs = await self._rpc_call("eth_getLogs", [{
            "fromBlock": hex(from_block),
            "toBlock": "latest",
            "address": contract_address,
            "topics": [self.TRANSFER_TOPIC, None, wallet_padded],
        }])

        if incoming_logs:
            for log in incoming_logs[-limit:]:
                try:
                    tx = self._parse_transfer_log(
                        log, token_symbol, token_name,
                        decimals, TX_TYPE_TRANSFER_IN
                    )
                    if tx:
                        transactions.append(tx)
                except Exception as e:
                    logger.debug(f"Failed to parse incoming tx: {e}")

        # Get outgoing transfers (from wallet)
        outgoing_logs = await self._rpc_call("eth_getLogs", [{
            "fromBlock": hex(from_block),
            "toBlock": "latest",
            "address": contract_address,
            "topics": [self.TRANSFER_TOPIC, wallet_padded, None],
        }])

        if outgoing_logs:
            for log in outgoing_logs[-limit:]:
                try:
                    tx = self._parse_transfer_log(
                        log, token_symbol, token_name,
                        decimals, TX_TYPE_TRANSFER_OUT
                    )
                    if tx:
                        transactions.append(tx)
                except Exception as e:
                    logger.debug(f"Failed to parse outgoing tx: {e}")

        # Sort by block number descending and limit
        transactions.sort(key=lambda x: x.block_number, reverse=True)
        return transactions[:limit]

    def _parse_transfer_log(
        self,
        log: dict,
        token_symbol: str,
        token_name: str,
        decimals: int,
        direction: str,
    ) -> TokenTransaction | None:
        """Parse ERC-20 Transfer event log."""
        try:
            topics = log.get("topics", [])
            if len(topics) < 3:
                return None

            from_addr = "0x" + topics[1][-40:]
            to_addr = "0x" + topics[2][-40:]

            value_hex = log.get("data", "0x0")
            value_raw = int(value_hex, 16) if value_hex else 0
            value = Decimal(value_raw) / Decimal(10**decimals)

            block_hex = log.get("blockNumber", "0x0")
            block_num = int(block_hex, 16) if block_hex else 0

            return TokenTransaction(
                tx_hash=log.get("transactionHash", ""),
                block_number=block_num,
                timestamp=datetime.now(UTC),  # Approximate, would need block timestamp
                from_address=from_addr,
                to_address=to_addr,
                value=value,
                token_symbol=token_symbol,
                token_name=token_name,
                direction=direction,
            )
        except Exception as e:
            logger.debug(f"Failed to parse transfer log: {e}")
            return None

    async def get_bnb_transactions(
        self,
        wallet_address: str,
        limit: int = 20,
    ) -> list[TokenTransaction]:
        """
        Get BNB transactions.

        Note: Native BNB transfers cannot be retrieved via eth_getLogs.
        Returns empty list - use BSCScan API for full BNB history.
        """
        # BNB native transfers are not logged as events
        # Would need to scan all blocks which is too expensive
        return []

    async def get_usdt_transactions(
        self,
        wallet_address: str,
        limit: int = 20,
    ) -> list[TokenTransaction]:
        """Get USDT transaction history."""
        return await self.get_token_transactions(
            wallet_address=wallet_address,
            contract_address=USDT_CONTRACT,
            token_symbol="USDT",
            token_name="Tether USD",
            decimals=18,
            limit=limit,
        )

    async def get_plex_transactions(
        self,
        wallet_address: str,
        limit: int = 20,
    ) -> list[TokenTransaction]:
        """Get PLEX transaction history."""
        return await self.get_token_transactions(
            wallet_address=wallet_address,
            contract_address=PLEX_CONTRACT_ADDRESS,
            token_symbol="PLEX",
            token_name="PLEX Token",
            decimals=9,
            limit=limit,
        )

    async def get_all_transactions(
        self,
        wallet_address: str,
        limit_per_token: int = 20,
    ) -> dict[str, list[TokenTransaction]]:
        """
        Get all transaction types for wallet.

        Args:
            wallet_address: Wallet address
            limit_per_token: Max transactions per token type

        Returns:
            Dict with keys: "BNB", "USDT", "PLEX"
        """
        # Fetch token transfers in parallel
        usdt_task = self.get_usdt_transactions(wallet_address, limit_per_token)
        plex_task = self.get_plex_transactions(wallet_address, limit_per_token)

        usdt_txs, plex_txs = await asyncio.gather(
            usdt_task, plex_task,
            return_exceptions=True
        )

        return {
            "BNB": [],  # Not available via RPC logs
            "USDT": usdt_txs if isinstance(usdt_txs, list) else [],
            "PLEX": plex_txs if isinstance(plex_txs, list) else [],
        }
