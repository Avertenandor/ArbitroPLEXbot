"""
Gas operations for blockchain transactions.

This module handles:
- Gas price calculation and optimization
- Gas limit estimation
- Gas fee calculations
"""

from decimal import Decimal
from typing import Any

from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3
from web3.exceptions import ContractLogicError, Web3Exception

from .core_constants import (
    DEFAULT_USDT_GAS_LIMIT,
    GAS_LIMIT_MULTIPLIER,
    MAX_GAS_PRICE_WEI,
    MIN_GAS_PRICE_WEI,
    USDT_ABI,
    USDT_DECIMALS,
)


class GasManager:
    """
    Manages gas-related operations for blockchain transactions.
    """

    def __init__(self, usdt_contract_address: str) -> None:
        """
        Initialize gas manager.

        Args:
            usdt_contract_address: USDT contract address for gas estimation
        """
        self.usdt_contract_address = to_checksum_address(usdt_contract_address)

    def get_optimal_gas_price(self, w3: Web3) -> int:
        """
        Calculate optimal gas price with Smart Gas strategy.

        Logic:
        1. Get current RPC gas price.
        2. Clamp between MIN (0.01 Gwei) and MAX (0.1 Gwei).

        Args:
            w3: Web3 instance

        Returns:
            Gas price in Wei
        """
        try:
            rpc_gas = w3.eth.gas_price

            # Clamp logic
            final_gas = max(MIN_GAS_PRICE_WEI, min(MAX_GAS_PRICE_WEI, rpc_gas))

            # Log if capped
            if rpc_gas > MAX_GAS_PRICE_WEI:
                logger.warning(
                    f"Gas price capped! RPC: {rpc_gas / 1e9:.2f} Gwei, "
                    f"Used: {final_gas / 1e9:.2f} Gwei"
                )

            return int(final_gas)
        except Web3Exception as e:
            logger.warning(f"Failed to get gas price from RPC, using MIN: {e}")
            return int(MIN_GAS_PRICE_WEI)

    def estimate_gas_fee(
        self,
        w3: Web3,
        to_address: str,
        amount: Decimal,
        from_address: str,
    ) -> Decimal | None:
        """
        Estimate gas fee for USDT transfer.

        This is a synchronous method that performs blockchain calls.
        Should be run in a thread pool executor.

        Args:
            w3: Web3 instance
            to_address: Recipient wallet address
            amount: Amount in USDT (Decimal)
            from_address: Sender wallet address

        Returns:
            Estimated gas fee in BNB or None on error
        """
        try:
            to_address = to_checksum_address(to_address)
            # Convert Decimal to wei using proper precision handling
            from decimal import ROUND_DOWN
            amount_wei = int(
                (Decimal(str(amount)) * Decimal(10 ** USDT_DECIMALS))
                .to_integral_value(ROUND_DOWN)
            )

            contract = w3.eth.contract(address=self.usdt_contract_address, abi=USDT_ABI)
            func = contract.functions.transfer(to_address, amount_wei)

            try:
                func_gas = func.estimate_gas({"from": from_address})
            except (Web3Exception, ContractLogicError) as e:
                logger.warning(f"Gas estimation failed: {e}")
                func_gas = DEFAULT_USDT_GAS_LIMIT  # Fallback

            price = self.get_optimal_gas_price(w3)
            total_wei = func_gas * price
            return Decimal(total_wei) / Decimal(10 ** 18)
        except (ValueError, Web3Exception) as e:
            logger.error(f"Failed to estimate gas fee: {e}")
            return None

    def estimate_transaction_gas(
        self,
        w3: Web3,
        contract_address: str,
        function_call: Any,
        from_address: str,
    ) -> int:
        """
        Estimate gas limit for a transaction.

        Args:
            w3: Web3 instance
            contract_address: Contract address
            function_call: Contract function call
            from_address: Sender address

        Returns:
            Estimated gas limit with safety buffer
        """
        try:
            gas_est = function_call.estimate_gas({"from": from_address})
            # Add safety buffer
            return int(gas_est * GAS_LIMIT_MULTIPLIER)
        except (Web3Exception, ContractLogicError) as e:
            logger.warning(f"Gas estimation failed: {e}")
            return DEFAULT_USDT_GAS_LIMIT
