"""
PLEX token payment scanning operations.

This module handles:
- PLEX payment history scanning
- Transaction aggregation and filtering
"""

from decimal import Decimal
from typing import Any

from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3

from app.utils.security import mask_address

from .core_constants import PLEX_ABI, PLEX_DECIMALS


class PlexPaymentScanner:
    """
    Manages PLEX token payment scanning operations.
    """

    def __init__(
        self,
        plex_token_address: str | None,
        system_wallet_address: str,
    ) -> None:
        """
        Initialize PLEX payment scanner.

        Args:
            plex_token_address: PLEX token contract address
            system_wallet_address: System wallet address
        """
        self.plex_token_address = (
            to_checksum_address(plex_token_address)
            if plex_token_address
            else None
        )
        self.system_wallet_address = to_checksum_address(
            system_wallet_address
        )

    def scan_plex_payments(
        self,
        w3: Web3,
        from_address: str,
        since_block: int | None = None,
        max_blocks: int = 100000,
    ) -> list[dict[str, Any]]:
        """
        Scan all PLEX Transfer events from user to system wallet.

        Args:
            w3: Web3 instance
            from_address: User's wallet address
            since_block: Starting block number
                (if None, scan from max_blocks ago)
            max_blocks: Maximum number of blocks to scan back
                (if since_block is None)

        Returns:
            List of payment dictionaries with:
            - tx_hash: str - transaction hash
            - amount: Decimal - PLEX amount transferred
            - block: int - block number
            - timestamp: int - block timestamp
        """
        if not self.plex_token_address:
            logger.error("PLEX token address not configured")
            return []

        try:
            sender = to_checksum_address(from_address)
            receiver = self.system_wallet_address
            token_address = self.plex_token_address

            latest = w3.eth.block_number

            # Determine starting block
            if since_block is not None:
                from_block = max(0, since_block)
            else:
                from_block = max(0, latest - max_blocks)

            logger.info(
                f"[PLEX Scan] Scanning PLEX payments from "
                f"{mask_address(sender)} to "
                f"{mask_address(receiver)}, "
                f"blocks {from_block} to {latest}"
            )

            contract = w3.eth.contract(
                address=token_address, abi=PLEX_ABI
            )

            # Get all Transfer events from user to system wallet
            logs = contract.events.Transfer.get_logs(
                fromBlock=from_block,
                toBlock="latest",
                argument_filters={"from": sender, "to": receiver},
            )

            payments = []

            for log in logs:
                args = log.get("args", {})
                value = args.get("value", 0)
                tx_hash = log["transactionHash"].hex()
                block_num = log["blockNumber"]

                # Get block timestamp
                try:
                    block = w3.eth.get_block(block_num)
                    timestamp = block.get("timestamp", 0)
                except Exception as e:
                    logger.warning(
                        f"Failed to get block {block_num} "
                        f"timestamp: {e}"
                    )
                    timestamp = 0

                payments.append(
                    {
                        "tx_hash": tx_hash,
                        "amount": (
                            Decimal(value) /
                            Decimal(10**PLEX_DECIMALS)
                        ),
                        "block": block_num,
                        "timestamp": timestamp,
                    }
                )

            # Sort by block number (oldest first)
            payments.sort(key=lambda x: x["block"])

            logger.info(
                f"[PLEX Scan] Found {len(payments)} PLEX "
                f"payments from {mask_address(sender)}"
            )

            return payments

        except Exception as e:
            logger.error(
                f"PLEX payment scan failed for "
                f"{mask_address(from_address)}: {e}"
            )
            return []
