"""
USDT deposit scanning operations.

This module handles:
- USDT deposit scanning from user wallets
- Transfer event parsing and filtering
"""

from decimal import Decimal
from typing import Any

from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3

from app.utils.security import mask_address
from app.utils.validation import validate_bsc_address

from .core_constants import USDT_ABI, USDT_DECIMALS


class UsdtDepositScanner:
    """
    Manages USDT deposit scanning operations.
    """

    def __init__(
        self,
        usdt_contract_address: str,
        system_wallet_address: str,
    ) -> None:
        """
        Initialize USDT deposit scanner.

        Args:
            usdt_contract_address: USDT contract address
            system_wallet_address: System wallet address for deposits
        """
        self.usdt_contract_address = to_checksum_address(
            usdt_contract_address
        )
        self.system_wallet_address = to_checksum_address(
            system_wallet_address
        )

    def scan_usdt_deposits_sync(
        self,
        w3: Web3,
        user_wallet: str,
        max_blocks: int = 50000,
        chunk_size: int = 5000,
    ) -> dict[str, Any]:
        """
        Scan all USDT Transfer events from user to system wallet.

        Used to detect user's total deposit amount from blockchain
        history. Scans in chunks to avoid RPC block range limits.

        Args:
            w3: Web3 instance
            user_wallet: User's wallet address
            max_blocks: Maximum number of blocks to scan back
                (default 50000)
            chunk_size: Number of blocks per scan chunk
                (default 5000)

        Returns:
            Dict with:
            - total_amount: Decimal - sum of all USDT transfers
            - tx_count: int - number of transactions found
            - transactions: list - list of transaction details
            - from_block: int - starting block
            - to_block: int - ending block
            - success: bool
            - error: str (if failed)
        """
        try:
            # Validate wallet address before sending to blockchain
            if not user_wallet or not validate_bsc_address(
                user_wallet, checksum=False
            ):
                error_msg = (
                    f"Invalid wallet address format: "
                    f"{user_wallet[:30] if user_wallet else 'None'}..."
                    if user_wallet
                    else "Wallet address is empty"
                )
                logger.warning(f"[USDT Scan] {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "total_amount": Decimal("0"),
                    "tx_count": 0,
                    "transactions": [],
                }

            sender = to_checksum_address(user_wallet)
            receiver = self.system_wallet_address
            usdt_address = self.usdt_contract_address

            latest = w3.eth.block_number
            from_block = max(0, latest - max_blocks)

            contract = w3.eth.contract(
                address=usdt_address, abi=USDT_ABI
            )

            # Detailed logging for diagnostics
            logger.info(
                f"[USDT Scan] Starting deposit scan:\n"
                f"  User wallet (sender): {sender}\n"
                f"  System wallet (receiver): {receiver}\n"
                f"  USDT contract: {usdt_address}\n"
                f"  Block range: {from_block} - {latest} "
                f"({max_blocks} blocks)\n"
                f"  Chunk size: {chunk_size}"
            )

            transactions = []
            total_wei = 0

            # Scan in chunks from newest to oldest
            current_end = latest
            while current_end > from_block:
                current_start = max(from_block, current_end - chunk_size)

                try:
                    logs = contract.events.Transfer.get_logs(
                        fromBlock=current_start,
                        toBlock=current_end,
                        argument_filters={
                            "from": sender,
                            "to": receiver
                        },
                    )

                    logger.debug(
                        f"[USDT Scan] Chunk "
                        f"{current_start}-{current_end}: "
                        f"{len(logs)} logs"
                    )

                    for log in logs:
                        args = log.get("args", {})
                        value = args.get("value", 0)
                        total_wei += value

                        transactions.append(
                            {
                                "tx_hash": log[
                                    "transactionHash"
                                ].hex(),
                                "amount": (
                                    Decimal(value) /
                                    Decimal(10**USDT_DECIMALS)
                                ),
                                "block": log["blockNumber"],
                            }
                        )

                except Exception as chunk_error:
                    logger.warning(
                        f"[USDT Scan] Chunk "
                        f"{current_start}-{current_end} "
                        f"failed: {chunk_error}"
                    )

                current_end = current_start

            # Sort by block number (oldest first)
            transactions.sort(key=lambda x: x["block"])

            result = {
                "total_amount": (
                    Decimal(total_wei) / Decimal(10**USDT_DECIMALS)
                ),
                "tx_count": len(transactions),
                "transactions": transactions,
                "from_block": from_block,
                "to_block": latest,
                "success": True,
            }

            # Detailed result logging
            if result["tx_count"] > 0:
                logger.success(
                    f"[USDT Scan] Found deposits for "
                    f"{mask_address(user_wallet)}:\n"
                    f"  Total amount: {result['total_amount']} USDT\n"
                    f"  Transactions: {result['tx_count']}\n"
                    f"  Block range scanned: {from_block} - {latest}"
                )
                for tx in transactions:
                    logger.info(
                        f"  -> TX: {tx['tx_hash'][:16]}..., "
                        f"Amount: {tx['amount']} USDT, "
                        f"Block: {tx['block']}"
                    )
            else:
                logger.warning(
                    f"[USDT Scan] No deposits found for "
                    f"{mask_address(user_wallet)}:\n"
                    f"  Searched from={sender} to={receiver}\n"
                    f"  Block range: {from_block} - {latest}\n"
                    f"  Verify user sent USDT to correct address: "
                    f"{receiver}"
                )

            return result

        except Exception as e:
            logger.error(
                f"Deposit scan failed for "
                f"{mask_address(user_wallet)}: {e}"
            )
            return {
                "success": False,
                "error": str(e),
                "total_amount": Decimal("0"),
                "tx_count": 0,
                "transactions": [],
            }
