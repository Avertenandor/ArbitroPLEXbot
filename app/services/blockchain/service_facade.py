"""
Blockchain service - Main coordinator.

This module provides the main BlockchainService class that coordinates
all blockchain operations by delegating to specialized managers:
- SyncProviderManager: RPC provider management with failover
- WalletManager: Wallet initialization and validation
- GasManager: Gas price optimization
- BalanceManager: Token balance checking
- TransactionManager: Transaction sending and monitoring
- PaymentVerifier: Payment verification and deposit scanning

Full Web3.py implementation for BSC blockchain operations
(USDT transfers, monitoring) with Dual-Core engine (QuickNode + NodeReal).
"""

import asyncio
import warnings
from decimal import Decimal
from typing import Any

# Suppress eth_utils network warnings about invalid ChainId
warnings.filterwarnings(
    "ignore",
    message=".*does not have a valid ChainId.*",
    category=UserWarning,
    module="eth_utils.network",
)
warnings.filterwarnings(
    "ignore",
    message=".*does not have a valid ChainId.*",
    category=UserWarning,
)

from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3
from web3.exceptions import Web3Exception

from app.config.settings import Settings
from app.utils.security import mask_address

# Import specialized managers from blockchain subdirectory
from app.services.blockchain.async_executor import AsyncBlockchainExecutor
from app.services.blockchain.balance_operations import BalanceManager
from app.services.blockchain.block_operations import BlockOperations
from app.services.blockchain.core_constants import USDT_ABI
from app.services.blockchain.gas_operations import GasManager
from app.services.blockchain.payment_verification import PaymentVerifier
from app.services.blockchain.rpc_rate_limiter import RPCRateLimiter
from app.services.blockchain.sync_provider_management import SyncProviderManager
from app.services.blockchain.transaction_operations import TransactionManager
from app.services.blockchain.wallet_operations import WalletManager


class BlockchainService:
    """
    Blockchain service for BSC/USDT operations.

    Full Web3.py implementation with:
    - Dual-Core Engine (QuickNode + NodeReal)
    - Automatic Failover
    - Smart Gas Management
    - USDT contract interaction
    - Transaction sending
    - Balance checking
    - Event monitoring

    This class acts as a coordinator, delegating operations to specialized managers.
    """

    def __init__(
        self,
        settings: Settings,
        session_factory: Any | None = None,
    ) -> None:
        """
        Initialize blockchain service.

        Args:
            settings: Application settings
            session_factory: Async session factory for DB access (optional)
        """
        self.settings = settings
        self.session_factory = session_factory

        self.usdt_contract_address = to_checksum_address(settings.usdt_contract_address)
        self.system_wallet_address = settings.system_wallet_address

        # Initialize RPC rate limiter
        self.rpc_limiter = RPCRateLimiter(max_concurrent=10, max_rps=25)

        # Initialize Provider Manager
        self.provider_manager = SyncProviderManager(settings, session_factory)

        # Initialize Async Executor
        self.async_executor = AsyncBlockchainExecutor(
            self.provider_manager,
            self.rpc_limiter,
            max_workers=4
        )

        # Initialize Wallet Manager
        self.wallet_manager = WalletManager(settings)

        # Initialize Gas Manager
        self.gas_manager = GasManager(self.usdt_contract_address)

        # Initialize Balance Manager
        self.balance_manager = BalanceManager(
            self.usdt_contract_address,
            settings.auth_plex_token_address,
        )

        # Initialize Transaction Manager
        self.transaction_manager = TransactionManager(
            self.usdt_contract_address,
            self.wallet_manager.wallet_account,
            self.wallet_manager.wallet_address,
            self.gas_manager,
            session_factory,
        )

        # Initialize Payment Verifier
        self.payment_verifier = PaymentVerifier(
            self.usdt_contract_address,
            settings.auth_plex_token_address,
            settings.auth_system_wallet_address,
        )

        # Initialize Block Operations
        self.block_operations = BlockOperations(
            self.provider_manager,
            self.rpc_limiter,
            self.async_executor._executor,
        )

        logger.success(
            f"BlockchainService initialized successfully\n"
            f"  Active Provider: {self.provider_manager.active_provider_name}\n"
            f"  Providers: {list(self.provider_manager.providers.keys())}\n"
            f"  USDT Contract: {self.usdt_contract_address}\n"
            f"  Wallet: {mask_address(self.wallet_address) if self.wallet_address else 'Not configured'}"
        )

    # ========== Properties for backward compatibility ==========

    @property
    def wallet_address(self) -> str | None:
        """Get wallet address."""
        return self.wallet_manager.wallet_address

    @property
    def wallet_account(self):
        """Get wallet account."""
        return self.wallet_manager.wallet_account

    @property
    def wallet_private_key(self) -> str:
        """Get wallet private key."""
        return self.wallet_manager.wallet_private_key

    @property
    def providers(self) -> dict[str, Web3]:
        """Get providers dict."""
        return self.provider_manager.providers

    @property
    def active_provider_name(self) -> str:
        """Get active provider name."""
        return self.provider_manager.active_provider_name

    @active_provider_name.setter
    def active_provider_name(self, value: str) -> None:
        """Set active provider name."""
        self.provider_manager.active_provider_name = value

    @property
    def is_auto_switch_enabled(self) -> bool:
        """Get auto-switch enabled status."""
        return self.provider_manager.is_auto_switch_enabled

    @property
    def web3(self) -> Web3:
        """Backward compatibility property."""
        return self.get_active_web3()

    @property
    def usdt_contract(self):
        """Get USDT contract on active provider."""
        w3 = self.get_active_web3()
        return w3.eth.contract(address=self.usdt_contract_address, abi=USDT_ABI)

    # ========== Core Methods ==========

    def get_active_web3(self) -> Web3:
        """Get the currently active Web3 instance."""
        return self.provider_manager.get_active_web3()

    def get_optimal_gas_price(self, w3: Web3) -> int:
        """
        Calculate optimal gas price with Smart Gas strategy.

        Args:
            w3: Web3 instance

        Returns:
            Gas price in Wei
        """
        return self.gas_manager.get_optimal_gas_price(w3)

    # ========== Provider Management Methods ==========

    async def force_refresh_settings(self) -> None:
        """Force update settings from DB."""
        await self.provider_manager.force_refresh_settings()

    async def get_providers_status(self) -> dict[str, Any]:
        """Get status of all providers."""
        return await self.provider_manager.get_providers_status()

    def get_rpc_stats(self) -> dict[str, Any]:
        """Get RPC rate limiter statistics."""
        return self.rpc_limiter.get_stats()

    # ========== Wallet Methods ==========

    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate wallet address format.

        Args:
            address: Wallet address to validate

        Returns:
            True if address is valid
        """
        return await self.wallet_manager.validate_wallet_address(address)

    # ========== Balance Methods ==========

    async def get_usdt_balance(self, address: str) -> Decimal | None:
        """
        Get USDT balance for address.

        Args:
            address: Wallet address

        Returns:
            USDT balance or None on error
        """
        try:
            def _get_bal(w3: Web3):
                return asyncio.run(
                    self.balance_manager.get_usdt_balance(w3, address)
                )

            return await self.async_executor.run_with_failover(_get_bal)
        except Exception as e:
            logger.error(f"Get USDT balance failed: {e}")
            return None

    async def get_plex_balance(self, address: str) -> Decimal | None:
        """
        Get PLEX token balance for address.

        Args:
            address: Wallet address

        Returns:
            PLEX balance or None on error
        """
        try:
            def _get_bal(w3: Web3):
                return asyncio.run(
                    self.balance_manager.get_plex_balance(w3, address)
                )

            return await self.async_executor.run_with_failover(_get_bal)
        except Exception as e:
            logger.error(f"Get PLEX balance failed: {e}")
            return None

    async def get_native_balance(self, address: str) -> Decimal | None:
        """
        Get Native Token (BNB) balance.

        Args:
            address: Wallet address

        Returns:
            BNB balance or None on error
        """
        try:
            def _get_bal(w3: Web3):
                return asyncio.run(
                    self.balance_manager.get_native_balance(w3, address)
                )

            return await self.async_executor.run_with_failover(_get_bal)
        except Exception as e:
            logger.error(f"Get BNB balance failed: {e}")
            return None

    # ========== Gas Methods ==========

    async def estimate_gas_fee(self, to_address: str, amount: Decimal) -> Decimal | None:
        """
        Estimate gas fee for USDT transfer.

        Args:
            to_address: Recipient wallet address
            amount: Amount in USDT (Decimal)

        Returns:
            Estimated gas fee in BNB or None
        """
        try:
            def _est_gas(w3: Web3):
                return asyncio.run(
                    self.gas_manager.estimate_gas_fee(
                        w3, to_address, amount, self.wallet_address
                    )
                )

            return await self.async_executor.run_with_failover(_est_gas)
        except Exception:
            return None

    # ========== Transaction Methods ==========

    async def send_payment(self, to_address: str, amount: Decimal) -> dict[str, Any]:
        """
        Send USDT payment.

        Args:
            to_address: Recipient wallet address
            amount: Amount in USDT (Decimal for precision)

        Returns:
            Dict with success, tx_hash, error
        """
        if not await self.validate_wallet_address(to_address):
            return {"success": False, "error": f"Invalid address: {to_address}"}

        def _send(w3: Web3):
            return asyncio.run(
                self.transaction_manager.send_usdt_payment(
                    w3, to_address, amount, self.async_executor._executor
                )
            )

        try:
            return await self.async_executor.run_with_failover(_send)
        except Exception as e:
            logger.error(f"Failed to send payment: {e}")
            return {"success": False, "error": str(e)}

    async def send_native_token(self, to_address: str, amount: Decimal) -> dict[str, Any]:
        """
        Send native token (BNB) to address.

        Args:
            to_address: Recipient wallet address
            amount: Amount in BNB (Decimal for precision)

        Returns:
            Dict with success, tx_hash, error
        """
        if not await self.validate_wallet_address(to_address):
            return {"success": False, "error": f"Invalid address: {to_address}"}

        def _send(w3: Web3):
            return asyncio.run(
                self.transaction_manager.send_native_token(
                    w3, to_address, amount, self.async_executor._executor
                )
            )

        try:
            return await self.async_executor.run_with_failover(_send)
        except Exception as e:
            logger.error(f"Failed to send BNB: {e}")
            return {"success": False, "error": str(e)}

    async def check_transaction_status(self, tx_hash: str) -> dict[str, Any]:
        """
        Check transaction status.

        Args:
            tx_hash: Transaction hash

        Returns:
            Dict with status, confirmations, block_number
        """
        try:
            def _check(w3: Web3):
                return self.transaction_manager.check_transaction_status_sync(w3, tx_hash)

            return await self.async_executor.run_with_failover(_check)
        except (TimeoutError, Web3Exception) as e:
            logger.warning(f"Failed to check transaction status: {e}")
            return {"status": "unknown", "confirmations": 0}

    async def get_transaction_details(self, tx_hash: str) -> dict[str, Any] | None:
        """
        Get transaction details.

        Args:
            tx_hash: Transaction hash

        Returns:
            Dict with transaction details or None on error
        """
        try:
            def _fetch(w3: Web3):
                return self.transaction_manager.fetch_transaction_details_sync(w3, tx_hash)

            return await self.async_executor.run_with_failover(_fetch)
        except (TimeoutError, Web3Exception) as e:
            logger.warning(f"Failed to get transaction details: {e}")
            return None

    # ========== Payment Verification Methods ==========

    async def verify_plex_payment(
        self,
        sender_address: str,
        amount_plex: float | None = None,
        lookback_blocks: int = 200,  # ~10 minutes on BSC (3 sec/block)
    ) -> dict[str, Any]:
        """
        Verify if user paid PLEX tokens to system wallet.

        Args:
            sender_address: User's wallet address
            amount_plex: Required PLEX amount (uses default from settings if None)
            lookback_blocks: Number of blocks to scan back

        Returns:
            Dict with success, tx_hash, amount, block, or error
        """
        target_amount = amount_plex or self.settings.auth_price_plex

        def _verify(w3: Web3):
            return self.payment_verifier.verify_plex_payment_sync(
                w3, sender_address, target_amount, lookback_blocks
            )

        try:
            return await self.async_executor.run_with_failover(_verify)
        except Exception as e:
            logger.error(f"[PLEX Verify] Error: {e}")
            return {"success": False, "error": str(e)}

    async def get_user_usdt_deposits(
        self,
        user_wallet: str,
        max_blocks: int = 100000,
    ) -> dict:
        """
        Scan all USDT Transfer events from user wallet to system wallet.

        Used to detect user's total deposit amount from blockchain history.

        Args:
            user_wallet: User's wallet address
            max_blocks: Maximum number of blocks to scan back

        Returns:
            Dict with total_amount, tx_count, transactions, success, error
        """
        def _scan(w3: Web3):
            return self.payment_verifier.scan_usdt_deposits_sync(
                w3, user_wallet, max_blocks
            )

        try:
            return await self.async_executor.run_with_failover(_scan)
        except Exception as e:
            logger.error(f"Deposit scan failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_amount': Decimal("0"),
                'tx_count': 0,
                'transactions': [],
            }

    # ========== Block Operations ==========

    async def get_block_number(self) -> int:
        """
        Get current block number.

        Returns:
            Current block number
        """
        return await self.block_operations.get_block_number()

    # ========== Cleanup Methods ==========

    def close(self) -> None:
        """Clean up resources and clear sensitive data."""
        # Clean up async executor
        if hasattr(self, 'async_executor') and self.async_executor:
            self.async_executor.cleanup()

        # Clean up wallet manager
        if hasattr(self, 'wallet_manager'):
            self.wallet_manager.cleanup()
