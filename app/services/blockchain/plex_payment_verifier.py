"""
PLEX token payment verification operations.

This module handles:
- PLEX token payment verification
- PLEX token transfer verification
"""

from decimal import Decimal
from typing import Any

from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3

from app.utils.security import mask_address

from .core_constants import PLEX_ABI, PLEX_DECIMALS


class PlexPaymentVerifier:
    """Manages PLEX token payment verification operations."""

    def __init__(
        self,
        plex_token_address: str | None,
        system_wallet_address: str,
    ) -> None:
        """
        Initialize PLEX payment verifier.

        Args:
            plex_token_address: PLEX token contract address
            system_wallet_address: System wallet address for payments
        """
        self.plex_token_address = (
            to_checksum_address(plex_token_address)
            if plex_token_address
            else None
        )
        self.system_wallet_address = to_checksum_address(
            system_wallet_address
        )

    def _scan_transfer_logs(
        self,
        w3: Web3,
        lookback_blocks: int,
        argument_filters: dict[str, str],
        log_prefix: str,
    ) -> list[Any]:
        """Internal method to scan PLEX transfer logs."""
        latest = w3.eth.block_number
        contract = w3.eth.contract(
            address=self.plex_token_address, abi=PLEX_ABI
        )
        chunk_size = 100
        all_logs = []
        logger.info(
            f"[{log_prefix}] Scanning {lookback_blocks} blocks "
            f"in chunks of {chunk_size}"
        )
        for offset in range(0, lookback_blocks, chunk_size):
            from_blk = max(0, latest - offset - chunk_size)
            to_blk = latest - offset
            if from_blk >= to_blk:
                continue
            try:
                logs = contract.events.Transfer.get_logs(
                    fromBlock=from_blk,
                    toBlock=to_blk,
                    argument_filters=argument_filters,
                )
                chunk_logs = list(logs)
                all_logs.extend(chunk_logs)
                logger.debug(
                    f"[{log_prefix}] Chunk {from_blk}-{to_blk}: "
                    f"{len(chunk_logs)} logs"
                )
            except Exception as chunk_err:
                logger.warning(
                    f"[{log_prefix}] Chunk {from_blk}-{to_blk} "
                    f"failed: {chunk_err}"
                )
                continue
        logger.info(f"[{log_prefix}] Total found: {len(all_logs)} logs")
        return all_logs

    def verify_plex_payment_sync(
        self,
        w3: Web3,
        sender_address: str,
        amount_plex: float | Decimal,
        lookback_blocks: int = 200,
    ) -> dict[str, Any]:
        """Verify if user paid PLEX tokens to system wallet."""
        if not self.plex_token_address:
            return {
                "success": False,
                "error": "PLEX token address not configured"
            }
        try:
            sender = to_checksum_address(sender_address)
            receiver = self.system_wallet_address
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid address format: {e}"
            }
        amount_decimal = Decimal(str(amount_plex))
        target_wei = int(amount_decimal * Decimal(10**PLEX_DECIMALS))
        logger.info(
            f"[PLEX Verify] Searching: "
            f"sender={mask_address(sender)}, "
            f"receiver={mask_address(receiver)}, "
            f"required={amount_plex} PLEX"
        )
        all_logs = self._scan_transfer_logs(
            w3=w3,
            lookback_blocks=lookback_blocks,
            argument_filters={"to": receiver},
            log_prefix="PLEX Verify",
        )
        # Sort by block number (newest first)
        all_logs.sort(key=lambda x: x.get("blockNumber", 0), reverse=True)
        for log in all_logs:
            args = log.get("args", {})
            tx_from = str(args.get("from", ""))
            value = args.get("value", 0)
            tx_hash = log.get("transactionHash", b"").hex()
            block_num = log.get("blockNumber", 0)
            if tx_from.lower() == sender.lower():
                logger.info(
                    f"[PLEX Verify] Found TX from user: {tx_hash}"
                )
                if value >= target_wei:
                    amount_found = (
                        Decimal(value) / Decimal(10**PLEX_DECIMALS)
                    )
                    logger.success(
                        f"[PLEX Verify] VERIFIED! TX={tx_hash}, "
                        f"amount={amount_found} PLEX"
                    )
                    return {
                        "success": True,
                        "tx_hash": tx_hash,
                        "amount": amount_found,
                        "block": block_num,
                    }
                else:
                    logger.warning(
                        f"[PLEX Verify] Amount insufficient: "
                        f"{value} < {target_wei}"
                    )
        logger.warning(
            f"[PLEX Verify] No payment found from {sender[:10]}..."
        )
        return {"success": False, "error": "Transaction not found"}

    def verify_plex_transfer(
        self,
        w3: Web3,
        from_address: str,
        amount: Decimal,
        lookback_blocks: int = 200,
    ) -> dict[str, Any]:
        """Verify PLEX token transfer from address to system wallet."""
        if not self.plex_token_address:
            return {
                "success": False,
                "error": "PLEX token address not configured"
            }
        try:
            sender = to_checksum_address(from_address)
            receiver = self.system_wallet_address
        except ValueError as e:
            return {
                "success": False,
                "error": f"Invalid address format: {e}"
            }
        target_wei = int(amount * Decimal(10**PLEX_DECIMALS))
        logger.info(
            f"[PLEX Transfer Verify] from={mask_address(sender)}, "
            f"to={mask_address(receiver)}, amount={amount} PLEX"
        )
        all_logs = self._scan_transfer_logs(
            w3=w3,
            lookback_blocks=lookback_blocks,
            argument_filters={"from": sender, "to": receiver},
            log_prefix="PLEX Transfer Verify",
        )
        # Sort by block number (newest first)
        all_logs.sort(key=lambda x: x.get("blockNumber", 0), reverse=True)
        for log in all_logs:
            args = log.get("args", {})
            value = args.get("value", 0)
            tx_hash = log.get("transactionHash", b"").hex()
            block_num = log.get("blockNumber", 0)
            if value >= target_wei:
                amount_found = (
                    Decimal(value) / Decimal(10**PLEX_DECIMALS)
                )
                # Get block timestamp
                try:
                    block = w3.eth.get_block(block_num)
                    timestamp = block.get("timestamp", 0)
                except Exception as e:
                    logger.warning(
                        f"Failed to get block timestamp: {e}"
                    )
                    timestamp = 0
                logger.success(
                    f"[PLEX Transfer Verify] VERIFIED! "
                    f"TX={tx_hash}, amount={amount_found} PLEX, "
                    f"block={block_num}"
                )
                return {
                    "success": True,
                    "tx_hash": tx_hash,
                    "amount": amount_found,
                    "block": block_num,
                    "timestamp": timestamp,
                }
        logger.warning(
            f"[PLEX Transfer Verify] No transfer found from "
            f"{mask_address(sender)} with amount >= {amount} PLEX"
        )
        return {
            "success": False,
            "error": "Transfer not found or amount insufficient"
        }
