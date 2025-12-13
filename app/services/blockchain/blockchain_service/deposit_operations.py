"""
Deposit Operations Module.

Contains all deposit-related functionality for the BlockchainService.
"""

from __future__ import annotations

from decimal import ROUND_DOWN, Decimal
from typing import TYPE_CHECKING, Any

from loguru import logger

from app.config.constants import BLOCKCHAIN_LONG_TIMEOUT, BLOCKCHAIN_TIMEOUT

from ..constants import USDT_ABI, USDT_DECIMALS
from ..rpc_wrapper import with_timeout

if TYPE_CHECKING:
    from ..deposit_processor import DepositProcessor
    from ..provider_manager import ProviderManager


class DepositOperations:
    """
    Handles deposit-related operations.

    Features:
    - Transaction verification
    - Confirmation tracking
    - Blockchain history searching
    """

    def __init__(
        self,
        provider_manager: ProviderManager,
        deposit_processor: DepositProcessor,
        system_wallet_address: str,
        usdt_contract_address: str,
    ) -> None:
        """
        Initialize deposit operations.

        Args:
            provider_manager: Provider manager instance
            deposit_processor: Deposit processor instance
            system_wallet_address: System wallet address
            usdt_contract_address: USDT contract address
        """
        self.provider_manager = provider_manager
        self.deposit_processor = deposit_processor
        self.system_wallet_address = system_wallet_address
        self.usdt_contract_address = usdt_contract_address

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
        return await self.deposit_processor.check_transaction(
            tx_hash=tx_hash,
            expected_to_address=self.system_wallet_address,
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
        return await self.deposit_processor.get_confirmations(tx_hash)

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
        try:
            return await self._search_deposit_in_history(
                user_wallet=user_wallet,
                expected_amount=expected_amount,
                from_block=from_block,
                to_block=to_block,
                tolerance_percent=tolerance_percent,
            )
        except Exception as e:
            logger.error(
                f"Error searching blockchain for deposit from {user_wallet}: {e}"
            )
            return None

    async def _search_deposit_in_history(
        self,
        user_wallet: str,
        expected_amount: Decimal,
        from_block: int,
        to_block: int | str,
        tolerance_percent: float,
    ) -> dict[str, Any] | None:
        """Internal method to search blockchain history."""

        web3 = await self.provider_manager.get_web3()
        usdt_contract = web3.eth.contract(
            address=self.usdt_contract_address, abi=USDT_ABI
        )

        # Convert to checksum address
        user_wallet_checksum = web3.to_checksum_address(user_wallet)
        system_wallet_checksum = web3.to_checksum_address(
            self.system_wallet_address
        )

        # Calculate tolerance
        tolerance = expected_amount * Decimal(tolerance_percent)
        min_amount = expected_amount - tolerance
        max_amount = expected_amount + tolerance

        # Convert amounts to wei for comparison using proper precision
        min_amount_wei = int(
            (min_amount * Decimal(10**USDT_DECIMALS)).to_integral_value(ROUND_DOWN)
        )
        max_amount_wei = int(
            (max_amount * Decimal(10**USDT_DECIMALS)).to_integral_value(ROUND_DOWN)
        )

        try:
            # Get current block if 'latest' with timeout
            if to_block == "latest":
                to_block = await with_timeout(
                    web3.eth.block_number,
                    timeout=BLOCKCHAIN_TIMEOUT,
                    operation_name="Get current block for deposit search"
                )

            # Limit search to last 100k blocks (about 3 days on BSC)
            # to avoid excessive RPC calls
            max_search_blocks = 100000
            if from_block < to_block - max_search_blocks:
                from_block = to_block - max_search_blocks
                logger.info(
                    f"Limiting search to last {max_search_blocks} blocks "
                    f"(from_block={from_block}, to_block={to_block})"
                )

            # Create filter for Transfer events with timeout
            # Filter: from=user_wallet, to=system_wallet
            event_filter = await with_timeout(
                usdt_contract.events.Transfer.create_filter(
                    from_block=from_block,
                    to_block=to_block,
                    argument_filters={
                        "from": user_wallet_checksum,
                        "to": system_wallet_checksum,
                    },
                ),
                timeout=BLOCKCHAIN_LONG_TIMEOUT,
                operation_name="Create deposit search filter"
            )

            # Get all matching events with timeout
            events = await with_timeout(
                event_filter.get_all_entries(),
                timeout=BLOCKCHAIN_LONG_TIMEOUT,
                operation_name="Get deposit search events"
            )

            # Find matching event by amount
            for event in events:
                value_wei = event["args"]["value"]
                amount_usdt = Decimal(value_wei) / Decimal(10**USDT_DECIMALS)

                # Check if amount matches (within tolerance)
                if min_amount_wei <= value_wei <= max_amount_wei:
                    # Get transaction details
                    tx_hash = event["transactionHash"].hex()
                    block_number = event["blockNumber"]

                    # Get current block for confirmations with timeout
                    current_block = await with_timeout(
                        web3.eth.block_number,
                        timeout=BLOCKCHAIN_TIMEOUT,
                        operation_name="Get current block for confirmations"
                    )
                    confirmations = current_block - block_number

                    logger.info(
                        f"Found matching deposit transaction: "
                        f"tx_hash={tx_hash}, amount={amount_usdt}, "
                        f"block={block_number}, confirmations={confirmations}"
                    )

                    return {
                        "tx_hash": tx_hash,
                        "block_number": block_number,
                        "amount": amount_usdt,
                        "confirmations": confirmations,
                    }

            logger.debug(
                f"No matching deposit found for {user_wallet} "
                f"amount {expected_amount} in blocks {from_block}-{to_block}"
            )
            return None

        except Exception as e:
            logger.error(f"Error in _search_deposit_in_history: {e}")
            return None
