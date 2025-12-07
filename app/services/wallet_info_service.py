"""
Wallet info service.

Provides comprehensive wallet information:
- Token balances (PLEX, USDT, BNB)
- Transaction history from BSCScan API
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
    - BSCScan API for transaction history
    """
    
    # BSCScan API endpoint
    BSCSCAN_API_URL = "https://api.bscscan.com/api"
    
    # Rate limiting for BSCScan
    REQUEST_DELAY = 0.25  # 4 requests per second (free tier limit is 5/sec)
    
    def __init__(self) -> None:
        """Initialize wallet info service."""
        self.api_key = getattr(settings, 'bscscan_api_key', None) or ""
        self._last_request_time = 0.0
    
    async def _rate_limit(self) -> None:
        """Apply rate limiting for BSCScan API calls."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        if elapsed < self.REQUEST_DELAY:
            await asyncio.sleep(self.REQUEST_DELAY - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()
    
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
    
    async def _fetch_bscscan(
        self,
        module: str,
        action: str,
        address: str,
        **kwargs: Any,
    ) -> dict | None:
        """
        Fetch data from BSCScan API.
        
        Args:
            module: API module (account, contract, etc.)
            action: API action
            address: Wallet address
            **kwargs: Additional parameters
            
        Returns:
            API response or None on error
        """
        await self._rate_limit()
        
        params = {
            "module": module,
            "action": action,
            "address": address,
            "apikey": self.api_key,
            **kwargs,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BSCSCAN_API_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("status") == "1":
                            return data
                        else:
                            # No transactions or error
                            logger.debug(f"BSCScan API: {data.get('message', 'No result')}")
                            return None
                    else:
                        logger.warning(f"BSCScan API error: HTTP {response.status}")
                        return None
        except Exception as e:
            logger.error(f"BSCScan API request failed: {e}")
            return None
    
    async def get_bnb_transactions(
        self,
        wallet_address: str,
        limit: int = 20,
    ) -> list[TokenTransaction]:
        """
        Get BNB (native) transaction history.
        
        Args:
            wallet_address: Wallet address
            limit: Max transactions to return
            
        Returns:
            List of TokenTransaction
        """
        data = await self._fetch_bscscan(
            module="account",
            action="txlist",
            address=wallet_address,
            startblock=0,
            endblock=99999999,
            page=1,
            offset=limit,
            sort="desc",
        )
        
        if not data:
            return []
        
        transactions = []
        wallet_lower = wallet_address.lower()
        
        for tx in data.get("result", [])[:limit]:
            try:
                # Only include successful transactions with value
                if tx.get("isError") == "1" or tx.get("value") == "0":
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
                
                value = Decimal(tx.get("value", "0")) / Decimal(10**18)
                
                transactions.append(TokenTransaction(
                    tx_hash=tx.get("hash", ""),
                    block_number=int(tx.get("blockNumber", 0)),
                    timestamp=datetime.fromtimestamp(int(tx.get("timeStamp", 0)), tz=UTC),
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
        Get BEP-20 token transaction history.
        
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
        data = await self._fetch_bscscan(
            module="account",
            action="tokentx",
            address=wallet_address,
            contractaddress=contract_address,
            page=1,
            offset=limit,
            sort="desc",
        )
        
        if not data:
            return []
        
        transactions = []
        wallet_lower = wallet_address.lower()
        
        for tx in data.get("result", [])[:limit]:
            try:
                from_addr = tx.get("from", "").lower()
                to_addr = tx.get("to", "").lower()
                
                # Determine direction
                if to_addr == wallet_lower:
                    direction = TX_TYPE_TRANSFER_IN
                elif from_addr == wallet_lower:
                    direction = TX_TYPE_TRANSFER_OUT
                else:
                    continue
                
                value = Decimal(tx.get("value", "0")) / Decimal(10**decimals)
                
                transactions.append(TokenTransaction(
                    tx_hash=tx.get("hash", ""),
                    block_number=int(tx.get("blockNumber", 0)),
                    timestamp=datetime.fromtimestamp(int(tx.get("timeStamp", 0)), tz=UTC),
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
