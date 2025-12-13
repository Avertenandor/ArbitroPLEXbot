"""
Blockchain Service - Main Service Class.

Orchestrates all blockchain operations using component services.
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import Any

from loguru import logger

from ..deposit_processor import DepositProcessor
from ..event_monitor import EventMonitor
from ..payment_sender import PaymentSender
from ..provider_manager import ProviderManager
from .balance_operations import BalanceOperations
from .deposit_operations import DepositOperations
from .failover import Failover
from .health_check import HealthCheck
from .payment_operations import PaymentOperations
from .validation import Validation


class BlockchainService:
    """
    Main blockchain service interface.

    Orchestrates:
    - Provider management (HTTP/WebSocket)
    - Event monitoring (USDT transfers)
    - Deposit processing (confirmations)
    - Payment sending (USDT transfers)
    - Balance queries
    - Validation
    - Health checks
    - Failover logic
    """

    def __init__(
        self,
        https_url: str,
        wss_url: str,
        usdt_contract_address: str,
        system_wallet_address: str,
        payout_wallet_address: str,
        payout_wallet_private_key: str | None = None,
        chain_id: int = 56,
        confirmation_blocks: int = 12,
        poll_interval: int = 3,
        session_factory: Any = None,
    ) -> None:
        """
        Initialize blockchain service.

        Args:
            https_url: QuickNode HTTPS URL
            wss_url: QuickNode WebSocket URL
            usdt_contract_address: USDT contract address
            system_wallet_address: System deposit wallet
            payout_wallet_address: Payout wallet
            payout_wallet_private_key: Private key for payouts
            chain_id: BSC chain ID (56=mainnet, 97=testnet)
            confirmation_blocks: Required confirmations
            poll_interval: Event polling interval (seconds)
            session_factory: Session factory for distributed lock (optional)
        """
        self.https_url = https_url
        self.wss_url = wss_url
        self.usdt_contract_address = usdt_contract_address
        self.system_wallet_address = system_wallet_address
        self.payout_wallet_address = payout_wallet_address
        self.chain_id = chain_id
        self.confirmation_blocks = confirmation_blocks

        # Initialize provider manager
        self.provider_manager = ProviderManager(
            https_url=https_url,
            wss_url=wss_url,
            chain_id=chain_id,
        )

        # Component services (initialized after provider connection)
        self._event_monitor: EventMonitor | None = None
        self._deposit_processor: DepositProcessor | None = None
        self._payment_sender: PaymentSender | None = None

        # Operation modules
        self._deposit_operations: DepositOperations | None = None
        self._payment_operations: PaymentOperations | None = None
        self._balance_operations: BalanceOperations | None = None
        self._validation: Validation | None = None
        self._health_check: HealthCheck | None = None
        self._failover: Failover | None = None

        # Store private key (will be used when initializing payment sender)
        self._payout_wallet_private_key = payout_wallet_private_key
        self._poll_interval = poll_interval
        self._session_factory = session_factory

        # Connected state
        self._initialized = False

        logger.info(
            "BlockchainService initialized (not yet connected)\n"
            f"  Chain ID: {chain_id}\n"
            f"  System Wallet: {system_wallet_address}\n"
            f"  Payout Wallet: {payout_wallet_address}\n"
            f"  Confirmations: {confirmation_blocks}"
        )

    async def connect(self) -> None:
        """Connect to blockchain providers and initialize components."""
        if self._initialized:
            logger.warning("BlockchainService already initialized")
            return

        # Connect providers
        await self.provider_manager.connect()

        # Get Web3 instance
        web3 = self.provider_manager.get_http_web3()

        # Initialize component services
        self._event_monitor = EventMonitor(
            web3=web3,
            usdt_contract_address=self.usdt_contract_address,
            poll_interval=self._poll_interval,
        )

        self._deposit_processor = DepositProcessor(
            web3=web3,
            usdt_contract_address=self.usdt_contract_address,
            confirmation_blocks=self.confirmation_blocks,
        )

        self._payment_sender = PaymentSender(
            web3=web3,
            usdt_contract_address=self.usdt_contract_address,
            payout_wallet_private_key=self._payout_wallet_private_key,
            session_factory=self._session_factory,
        )

        # Initialize operation modules
        self._deposit_operations = DepositOperations(
            provider_manager=self.provider_manager,
            deposit_processor=self._deposit_processor,
            system_wallet_address=self.system_wallet_address,
            usdt_contract_address=self.usdt_contract_address,
        )

        self._payment_operations = PaymentOperations(
            payment_sender=self._payment_sender,
        )

        self._balance_operations = BalanceOperations(
            payment_sender=self._payment_sender,
        )

        self._validation = Validation()

        self._health_check = HealthCheck(
            provider_manager=self.provider_manager,
            balance_operations=self._balance_operations,
            event_monitor=self._event_monitor,
            system_wallet_address=self.system_wallet_address,
            payout_wallet_address=self.payout_wallet_address,
        )

        self._failover = Failover(
            provider_manager=self.provider_manager,
        )

        self._initialized = True

        logger.success("BlockchainService connected and initialized")

    async def disconnect(self) -> None:
        """Disconnect from blockchain providers."""
        # Stop event monitoring if active
        if self._event_monitor and self._event_monitor.is_monitoring:
            await self._event_monitor.stop_monitoring()

        # Disconnect providers
        await self.provider_manager.disconnect()

        self._initialized = False
        logger.info("BlockchainService disconnected")

    # === Event Monitoring ===

    async def start_deposit_monitoring(
        self,
        event_callback: Callable | None = None,
        from_block: int | str = "latest",
    ) -> None:
        """
        Start monitoring USDT deposits to system wallet.

        Args:
            event_callback: Async callback for new deposits
            from_block: Starting block number or 'latest'
        """
        self._ensure_initialized()

        await self._event_monitor.start_monitoring(
            watch_address=self.system_wallet_address,
            from_block=from_block,
            event_callback=event_callback,
        )

    async def stop_deposit_monitoring(self) -> None:
        """Stop deposit monitoring."""
        self._ensure_initialized()
        await self._event_monitor.stop_monitoring()

    # === Deposit Processing ===

    async def check_deposit_transaction(
        self,
        tx_hash: str,
        expected_amount: Decimal | None = None,
        tolerance_percent: float = 0.05,
    ) -> dict[str, Any]:
        """
        Check deposit transaction status.

        Args:
            tx_hash: Transaction hash
            expected_amount: Expected USDT amount (optional)
            tolerance_percent: Amount tolerance (default 5%)

        Returns:
            Dict with valid, confirmed, confirmations, amount, etc.
        """
        self._ensure_initialized()

        # R7-5: Use failover wrapper
        return await self.execute_with_failover(
            self._deposit_operations.check_deposit_transaction,
            tx_hash=tx_hash,
            expected_amount=expected_amount,
            tolerance_percent=tolerance_percent,
        )

    async def get_transaction_confirmations(self, tx_hash: str) -> int:
        """
        Get number of confirmations for transaction.

        Args:
            tx_hash: Transaction hash

        Returns:
            Number of confirmations
        """
        self._ensure_initialized()

        # R7-5: Use failover wrapper
        return await self.execute_with_failover(
            self._deposit_operations.get_transaction_confirmations, tx_hash
        )

    async def search_blockchain_for_deposit(
        self,
        user_wallet: str,
        expected_amount: Decimal,
        from_block: int = 0,
        to_block: int | str = "latest",
        tolerance_percent: float = 0.05,
    ) -> dict[str, Any] | None:
        """
        Search blockchain history for USDT transfer matching deposit criteria.

        R3-6: Last attempt to find transaction before marking deposit as failed.

        Args:
            user_wallet: User's wallet address (from)
            expected_amount: Expected USDT amount
            from_block: Starting block number (default: 0)
            to_block: Ending block number or 'latest' (default: 'latest')
            tolerance_percent: Amount tolerance (default: 5%)

        Returns:
            Dict with tx_hash, block_number, amount, confirmations or None if not found
        """
        self._ensure_initialized()

        # Use failover wrapper for RPC calls
        return await self.execute_with_failover(
            self._deposit_operations.search_blockchain_for_deposit,
            user_wallet=user_wallet,
            expected_amount=expected_amount,
            from_block=from_block,
            to_block=to_block,
            tolerance_percent=tolerance_percent,
        )

    # === Payment Sending ===

    async def send_payment(
        self,
        to_address: str,
        amount_usdt: Decimal,
        max_retries: int = 5,
        previous_tx_hash: str | None = None,
    ) -> dict[str, Any]:
        """
        Send USDT payment.

        Args:
            to_address: Recipient wallet address
            amount_usdt: Amount in USDT (Decimal)
            max_retries: Maximum retry attempts
            previous_tx_hash: Previous transaction hash to check before retry

        Returns:
            Dict with success, tx_hash, error
        """
        self._ensure_initialized()

        # R7-5: Use failover wrapper
        return await self.execute_with_failover(
            self._payment_operations.send_payment,
            to_address=to_address,
            amount_usdt=amount_usdt,
            max_retries=max_retries,
            previous_tx_hash=previous_tx_hash,
        )

    async def estimate_gas_cost(
        self,
        to_address: str,
        amount_usdt: Decimal,
    ) -> dict[str, Any] | None:
        """
        Estimate gas cost for payment.

        Args:
            to_address: Recipient address
            amount_usdt: Amount in USDT (Decimal)

        Returns:
            Dict with gas_limit, gas_price_gwei, total_cost_bnb
        """
        self._ensure_initialized()

        return await self._payment_operations.estimate_gas_cost(
            to_address=to_address,
            amount_usdt=amount_usdt,
        )

    # === Balance Queries ===

    async def get_usdt_balance(
        self,
        address: str | None = None,
    ) -> Decimal | None:
        """
        Get USDT balance for address.

        Args:
            address: Wallet address (payout wallet if None)

        Returns:
            USDT balance or None
        """
        self._ensure_initialized()

        # R7-5: Use failover wrapper
        return await self.execute_with_failover(
            self._balance_operations.get_usdt_balance, address
        )

    async def get_bnb_balance(
        self,
        address: str | None = None,
    ) -> Decimal | None:
        """
        Get BNB balance for address (for gas fees).

        Args:
            address: Wallet address (payout wallet if None)

        Returns:
            BNB balance or None
        """
        self._ensure_initialized()
        return await self._balance_operations.get_bnb_balance(address)

    # === Wallet Validation ===

    async def validate_wallet_address(self, address: str) -> bool:
        """
        Validate BSC wallet address format.

        Args:
            address: Wallet address

        Returns:
            True if valid
        """
        return await self._validation.validate_wallet_address(address)

    # === Health & Status ===

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check on blockchain service.

        Returns:
            Dict with health status
        """
        return await self._health_check.health_check(self._initialized)

    async def execute_with_failover(
        self, operation: Callable, *args, **kwargs
    ) -> Any:
        """
        Execute blockchain operation with automatic failover (R7-5).

        Attempts operation with primary provider, falls back to HTTP if needed.

        Args:
            operation: Async function to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Operation result

        Raises:
            RuntimeError: If all providers fail and maintenance mode not set
        """
        self._ensure_initialized()
        return await self._failover.execute_with_failover(
            operation, *args, **kwargs
        )

    def _ensure_initialized(self) -> None:
        """
        Ensure service is initialized.

        Raises:
            RuntimeError: If not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "BlockchainService not initialized. Call connect() first."
            )
