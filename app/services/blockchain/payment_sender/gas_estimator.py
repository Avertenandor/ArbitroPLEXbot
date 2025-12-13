"""
Gas Estimator for Payment Sender.

Provides gas cost estimation functionality for USDT transfers.
"""

import asyncio
from decimal import ROUND_DOWN, Decimal
from typing import Any

from loguru import logger
from web3 import AsyncWeb3
from web3.contract import AsyncContract
from web3.exceptions import ContractLogicError, Web3Exception

from app.config.constants import BLOCKCHAIN_TIMEOUT

from ..constants import USDT_DECIMALS


class GasEstimator:
    """
    Estimates gas costs for USDT transfers.

    Features:
    - Gas limit estimation
    - Gas price queries
    - Total cost calculation in BNB
    """

    def __init__(
        self,
        web3: AsyncWeb3,
        usdt_contract: AsyncContract,
        payout_address: str,
    ):
        """
        Initialize gas estimator.

        Args:
            web3: AsyncWeb3 instance
            usdt_contract: USDT contract instance
            payout_address: Payout wallet address
        """
        self.web3 = web3
        self.usdt_contract = usdt_contract
        self.payout_address = payout_address

    async def estimate_gas_cost(
        self,
        to_address: str,
        amount_usdt: Decimal,
    ) -> dict[str, Any] | None:
        """
        Estimate gas cost for USDT transfer.

        Args:
            to_address: Recipient address
            amount_usdt: Amount in USDT

        Returns:
            Dict with gas_limit, gas_price, total_cost_bnb
        """
        try:
            to_address_checksum = self.web3.to_checksum_address(to_address)
            # Convert Decimal to wei using proper precision handling
            amount_wei = int(
                (Decimal(str(amount_usdt)) * Decimal(10 ** USDT_DECIMALS))
                .to_integral_value(ROUND_DOWN)
            )

            # Estimate gas with timeout
            transfer_function = self.usdt_contract.functions.transfer(
                to_address_checksum,
                amount_wei,
            )

            try:
                gas_estimate = await asyncio.wait_for(
                    transfer_function.estimate_gas(
                        {"from": self.payout_address}
                    ),
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except TimeoutError:
                logger.error("Timeout estimating gas cost")
                return None

            # Get gas price with timeout
            try:
                gas_price_wei = await asyncio.wait_for(
                    self.web3.eth.gas_price,
                    timeout=BLOCKCHAIN_TIMEOUT,
                )
            except TimeoutError:
                logger.error("Timeout getting gas price for cost estimation")
                return None

            # Calculate total cost in BNB
            total_cost_wei = gas_estimate * gas_price_wei
            total_cost_bnb = self.web3.from_wei(total_cost_wei, "ether")

            return {
                "gas_limit": gas_estimate,
                "gas_price_gwei": float(
                    self.web3.from_wei(gas_price_wei, "gwei")
                ),
                "total_cost_bnb": float(total_cost_bnb),
            }

        except ValueError as e:
            logger.error(
                f"Invalid address or amount for gas estimation: {e}",
                extra={
                    "to_address": to_address,
                    "amount_usdt": str(amount_usdt),
                },
            )
            return None
        except ContractLogicError as e:
            logger.error(
                f"Contract logic error during gas estimation: {e}",
                extra={
                    "to_address": to_address,
                    "amount_usdt": str(amount_usdt),
                },
            )
            return None
        except Web3Exception as e:
            logger.error(
                f"Web3 error during gas estimation: {e}",
                extra={
                    "to_address": to_address,
                    "amount_usdt": str(amount_usdt),
                },
            )
            return None
        except Exception as e:
            logger.exception(
                f"Unexpected error during gas estimation: {e}",
                extra={
                    "to_address": to_address,
                    "amount_usdt": str(amount_usdt),
                },
            )
            return None
