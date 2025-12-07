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

from app.config.settings import settings
from app.services.blockchain_service import get_blockchain_service
from app.utils.security import mask_address


# Transaction types for display
TX_TYPE_TRANSFER_IN = "in"
TX_TYPE_TRANSFER_OUT = "out"

# Token contract addresses
USDT_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"
PLEX_CONTRACT = "0xdf179b6cadbc61ffd86a3d2e55f6d6e083ade6c1"


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
        return f"https://bscscan.com/tx/{self.tx_hash}"
    
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
    - NodeReal Enhanced API for transaction history
    """
    
    def __init__(self) -> None:
        """Initialize wallet info service."""
        # Use NodeReal Enhanced API endpoint
        self.nodereal_url = getattr(settings, 'nodereal_api_url', None) or settings.rpc_url
        self._last_request_time = 0.0
    
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
            logger.error(f"Failed to get wallet balances for {mask_address(wallet_address)}: {e}")
            return None
    
    async def _nodereal_rpc_call(self, method: str, params: list) -> Any:
        """
        Make NodeReal Enhanced API JSON-RPC call.
        
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
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.nodereal_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"Content-Type": "application/json"},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "error" in data:
                            logger.debug(f"NodeReal RPC error: {data['error']}")
                            return None
                        return data.get("result")
                    else:
                        logger.warning(f"NodeReal API error: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"NodeReal RPC request failed: {e}")
            return None
    
    async def get_bnb_transactions(
        self,
        wallet_address: str,
        limit: int = 20,
    ) -> list[TokenTransaction]:
        """
        Get BNB (native) transaction history using eth_getTransactionsByAddress.
        
        Note: This is a NodeReal Enhanced API method.
        If not available, returns empty list.
        
        Args:
            wallet_address: Wallet address
            limit: Max transactions to return
            
        Returns:
            List of TokenTransaction
        """
        # Try NodeReal Enhanced API method
        result = await self._nodereal_rpc_call(
            "nr_getTransactionsByAddress",
            [wallet_address, "0x0", "latest", {"order": "desc", "pageSize": hex(limit)}]
        )
        
        if not result:
            # Fallback: return empty (transactions feature not available)
            logger.debug("BNB transactions not available via RPC")
            return []
        
        transactions = []
        wallet_lower = wallet_address.lower()
        
        for tx in result.get("transactions", [])[:limit]:
            try:
                value_hex = tx.get("value", "0x0")
                value_wei = int(value_hex, 16) if value_hex else 0
                
                if value_wei == 0:
                    continue
                
                from_addr = tx.get("from", "").lower()
                to_addr = tx.get("to", "").lower()
                
                # Determine direction
                if to_addr == wallet_lower:
                    direction = TX_TYPE_TRANSFER_IN
                elif from_addr == wallet_lower:
                    direction = TX_TYPE_TRANSFER_OUT
                else:
                    continue
                
                value = Decimal(value_wei) / Decimal(10**18)
                block_hex = tx.get("blockNumber", "0x0")
                block_num = int(block_hex, 16) if block_hex else 0
                
                # Get timestamp from block (approximate)
                timestamp_hex = tx.get("timestamp", "0x0")
                timestamp = int(timestamp_hex, 16) if timestamp_hex else 0
                
                transactions.append(TokenTransaction(
                    tx_hash=tx.get("hash", ""),
                    block_number=block_num,
                    timestamp=datetime.fromtimestamp(timestamp, tz=UTC) if timestamp else datetime.now(UTC),
                    from_address=tx.get("from", ""),
                    to_address=tx.get("to", ""),
                    value=value,
                    token_symbol="BNB",
                    token_name="BNB",
                    direction=direction,
                ))
            except Exception as e:
                logger.debug(f"Failed to parse BNB tx: {e}")
                continue
        
        return transactions
    
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
        Get BEP-20 token transaction history using nr_getTokenTransfers.
        
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
        # Try NodeReal Enhanced API for token transfers
        result = await self._nodereal_rpc_call(
            "nr_getTokenTransfers",
            [wallet_address, contract_address, "0x0", "latest", {"pageSize": hex(limit)}]
        )
        
        if not result:
            logger.debug(f"{token_symbol} transactions not available via RPC")
            return []
        
        transactions = []
        wallet_lower = wallet_address.lower()
        
        for tx in result.get("transfers", [])[:limit]:
            try:
                value_hex = tx.get("value", "0x0")
                value_raw = int(value_hex, 16) if value_hex else 0
                
                from_addr = tx.get("from", "").lower()
                to_addr = tx.get("to", "").lower()
                
                # Determine direction
                if to_addr == wallet_lower:
                    direction = TX_TYPE_TRANSFER_IN
                elif from_addr == wallet_lower:
                    direction = TX_TYPE_TRANSFER_OUT
                else:
                    continue
                
                value = Decimal(value_raw) / Decimal(10**decimals)
                block_hex = tx.get("blockNumber", "0x0")
                block_num = int(block_hex, 16) if block_hex else 0
                
                timestamp_hex = tx.get("timestamp", "0x0")
                timestamp = int(timestamp_hex, 16) if timestamp_hex else 0
                
                transactions.append(TokenTransaction(
                    tx_hash=tx.get("transactionHash", tx.get("hash", "")),
                    block_number=block_num,
                    timestamp=datetime.fromtimestamp(timestamp, tz=UTC) if timestamp else datetime.now(UTC),
                    from_address=tx.get("from", ""),
                    to_address=tx.get("to", ""),
                    value=value,
                    token_symbol=token_symbol,
                    token_name=token_name,
                    direction=direction,
                ))
            except Exception as e:
                logger.debug(f"Failed to parse {token_symbol} tx: {e}")
                continue
        
        return transactions
    
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
            contract_address=PLEX_CONTRACT,
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
        # Fetch all in parallel
        bnb_task = self.get_bnb_transactions(wallet_address, limit_per_token)
        usdt_task = self.get_usdt_transactions(wallet_address, limit_per_token)
        plex_task = self.get_plex_transactions(wallet_address, limit_per_token)
        
        bnb_txs, usdt_txs, plex_txs = await asyncio.gather(
            bnb_task, usdt_task, plex_task,
            return_exceptions=True
        )
        
        return {
            "BNB": bnb_txs if isinstance(bnb_txs, list) else [],
            "USDT": usdt_txs if isinstance(usdt_txs, list) else [],
            "PLEX": plex_txs if isinstance(plex_txs, list) else [],
        }
