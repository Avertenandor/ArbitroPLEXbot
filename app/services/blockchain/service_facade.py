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

import warnings
from typing import Any

from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3

from app.config.settings import Settings
from app.services.blockchain.async_executor import AsyncBlockchainExecutor
from app.services.blockchain.balance_operations import BalanceManager
from app.services.blockchain.block_operations import BlockOperations
from app.services.blockchain.core_constants import USDT_ABI
from app.services.blockchain.facade_helpers import BlockchainServiceMixin
from app.services.blockchain.gas_operations import GasManager
from app.services.blockchain.payment_verification import PaymentVerifier
from app.services.blockchain.rpc_rate_limiter import RPCRateLimiter
from app.services.blockchain.sync_provider_management import (
    SyncProviderManager,
)
from app.services.blockchain.transaction_operations import TransactionManager
from app.services.blockchain.wallet_operations import WalletManager
from app.utils.security import mask_address


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


class BlockchainService(BlockchainServiceMixin):
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

    This class acts as a coordinator, delegating operations to
    specialized managers.
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

        self.usdt_contract_address = to_checksum_address(
            settings.usdt_contract_address
        )
        self.system_wallet_address = settings.system_wallet_address

        # Initialize RPC rate limiter
        self.rpc_limiter = RPCRateLimiter(max_concurrent=10, max_rps=25)

        # Initialize Provider Manager
        self.provider_manager = SyncProviderManager(
            settings, session_factory
        )

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
        # NOTE: Using system_wallet_address for USDT deposits
        # (not auth_system_wallet_address)
        # auth_system_wallet_address is for PLEX authentication payments
        # system_wallet_address is the address shown to users for USDT
        self.payment_verifier = PaymentVerifier(
            self.usdt_contract_address,
            settings.auth_plex_token_address,
            settings.system_wallet_address,  # Fixed: use deposit wallet
        )

        # Initialize Block Operations
        self.block_operations = BlockOperations(
            self.provider_manager,
            self.rpc_limiter,
            self.async_executor._executor,
        )

        # Log wallet configuration for diagnostics
        if (settings.system_wallet_address !=
                settings.auth_system_wallet_address):
            logger.warning(
                f"⚠️ Different wallet addresses configured:\n"
                f"  USDT Deposits (system_wallet): "
                f"{settings.system_wallet_address}\n"
                f"  PLEX Auth (auth_system_wallet): "
                f"{settings.auth_system_wallet_address}\n"
                f"  Make sure users are sending USDT to: "
                f"{settings.system_wallet_address}"
            )

        wallet_display = (
            mask_address(self.wallet_address)
            if self.wallet_address
            else 'Not configured'
        )

        logger.success(
            f"BlockchainService initialized successfully\n"
            f"  Active Provider: "
            f"{self.provider_manager.active_provider_name}\n"
            f"  Providers: "
            f"{list(self.provider_manager.providers.keys())}\n"
            f"  USDT Contract: {self.usdt_contract_address}\n"
            f"  USDT Deposit Wallet: {settings.system_wallet_address}\n"
            f"  PLEX Auth Wallet: {settings.auth_system_wallet_address}\n"
            f"  Payout Wallet: {wallet_display}"
        )

    # ========== Properties for backward compatibility ==========

    @property
    def wallet_address(self) -> str | None:
        """Get wallet address."""
        return self.wallet_manager.wallet_address

    @property
    def wallet_account(self) -> Any:
        """Get wallet account (LocalAccount)."""
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
    def usdt_contract(self) -> Any:
        """Get USDT contract on active provider."""
        w3 = self.get_active_web3()
        return w3.eth.contract(
            address=self.usdt_contract_address, abi=USDT_ABI
        )

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

    # ========== Cleanup Methods ==========

    def close(self) -> None:
        """Clean up resources and clear sensitive data."""
        # Clean up async executor
        if hasattr(self, 'async_executor') and self.async_executor:
            self.async_executor.cleanup()

        # Clean up wallet manager
        if hasattr(self, 'wallet_manager'):
            self.wallet_manager.cleanup()
