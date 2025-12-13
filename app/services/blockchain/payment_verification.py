"""
Payment verification operations for blockchain service.

This module handles:
- PLEX token payment verification
- PLEX token transfer verification
- PLEX payment scanning
- USDT deposit scanning
- Event log parsing and filtering
"""

from decimal import Decimal
from typing import Any

from eth_utils import to_checksum_address
from loguru import logger
from web3 import Web3

from app.utils.security import mask_address
from app.utils.validation import is_valid_wallet_for_transactions

from .core_constants import PLEX_ABI, PLEX_DECIMALS, USDT_ABI, USDT_DECIMALS


class PaymentVerifier:
    """
    Manages payment verification and deposit scanning operations.
    """

    def __init__(
        self,
        usdt_contract_address: str,
        plex_token_address: str | None,
        system_wallet_address: str,
    ) -> None:
        """
        Initialize payment verifier.

        Args:
            usdt_contract_address: USDT contract address
            plex_token_address: PLEX token contract address
            system_wallet_address: System wallet address for receiving payments
        """
        self.usdt_contract_address = to_checksum_address(usdt_contract_address)
        self.plex_token_address = (
            to_checksum_address(plex_token_address)
            if plex_token_address
            else None
        )
        self.system_wallet_address = to_checksum_address(system_wallet_address)

    def verify_plex_payment_sync(
        self,
        w3: Web3,
        sender_address: str,
        amount_plex: float | Decimal,
        lookback_blocks: int = 200,  # ~10 minutes on BSC (3 sec/block)
    ) -> dict[str, Any]:
        """
        Verify if user paid PLEX tokens to system wallet.

        Algorithm:
        1. Scan recent blocks in chunks (to avoid RPC limits)
        2. Get incoming PLEX transfers to system wallet
        3. Check if any transfer is from the user's wallet
        4. Verify amount >= required

        Args:
            w3: Web3 instance
            sender_address: User's wallet address
            amount_plex: Required PLEX amount (float or Decimal)
            lookback_blocks: Number of blocks to scan back

        Returns:
            Dict with success, tx_hash, amount, block, or error
        """
        if not self.plex_token_address:
            return {"success": False, "error": "PLEX token address not configured"}

        try:
            sender = to_checksum_address(sender_address)
            receiver = self.system_wallet_address
            token_address = self.plex_token_address
        except ValueError as e:
            return {"success": False, "error": f"Invalid address format: {e}"}

        # PLEX uses 9 decimals
        # Use Decimal arithmetic to avoid float precision issues
        decimals = PLEX_DECIMALS
        amount_decimal = Decimal(str(amount_plex))
        target_wei = int(amount_decimal * Decimal(10**decimals))

        logger.info(
            f"[PLEX Verify] Searching: sender={mask_address(sender)}, "
            f"receiver={mask_address(receiver)}, required={amount_plex} PLEX"
        )

        latest = w3.eth.block_number
        contract = w3.eth.contract(address=token_address, abi=USDT_ABI)

        # Scan in chunks to avoid RPC rate limits
        # BSC public RPCs limit to ~100-500 blocks per request
        chunk_size = 100
        total_blocks = lookback_blocks
        all_logs = []

        logger.info(f"[PLEX Verify] Scanning {total_blocks} blocks in chunks of {chunk_size}")

        for offset in range(0, total_blocks, chunk_size):
            from_blk = max(0, latest - offset - chunk_size)
            to_blk = latest - offset

            if from_blk >= to_blk:
                continue

            try:
                logs = contract.events.Transfer.get_logs(
                    fromBlock=from_blk, toBlock=to_blk, argument_filters={"to": receiver}
                )
                chunk_logs = list(logs)
                all_logs.extend(chunk_logs)
                logger.debug(f"[PLEX Verify] Chunk {from_blk}-{to_blk}: {len(chunk_logs)} logs")
            except Exception as chunk_err:
                # Log error but continue with other chunks
                logger.warning(f"[PLEX Verify] Chunk {from_blk}-{to_blk} failed: {chunk_err}")
                continue

        logger.info(f"[PLEX Verify] Total found: {len(all_logs)} incoming transfers")

        # Sort by block number (newest first)
        all_logs.sort(key=lambda x: x.get("blockNumber", 0), reverse=True)

        for log in all_logs:
            args = log.get("args", {})
            tx_from = str(args.get("from", ""))
            value = args.get("value", 0)
            tx_hash = log.get("transactionHash", b"").hex()
            block_num = log.get("blockNumber", 0)

            # Compare addresses case-insensitive
            if tx_from.lower() == sender.lower():
                logger.info(f"[PLEX Verify] Found TX from user: {tx_hash}")

                if value >= target_wei:
                    amount_found = Decimal(value) / Decimal(10**decimals)
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
                    logger.warning(f"[PLEX Verify] Amount insufficient: {value} < {target_wei}")

        logger.warning(f"[PLEX Verify] No payment found from {sender[:10]}...")
        return {"success": False, "error": "Transaction not found"}

    def scan_usdt_deposits_sync(
        self,
        w3: Web3,
        user_wallet: str,
        max_blocks: int = 50000,
        chunk_size: int = 5000,
    ) -> dict[str, Any]:
        """
        Scan all USDT Transfer events from user wallet to system wallet.

        Used to detect user's total deposit amount from blockchain history.
        Scans in chunks to avoid RPC block range limits.

        Args:
            w3: Web3 instance
            user_wallet: User's wallet address
            max_blocks: Maximum number of blocks to scan back (default 50000)
            chunk_size: Number of blocks per scan chunk (default 5000)

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

            contract = w3.eth.contract(address=usdt_address, abi=USDT_ABI)

            # Detailed logging for diagnostics
            logger.info(
                f"[USDT Scan] Starting deposit scan:\n"
                f"  User wallet (sender): {sender}\n"
                f"  System wallet (receiver): {receiver}\n"
                f"  USDT contract: {usdt_address}\n"
                f"  Block range: {from_block} - {latest} ({max_blocks} blocks)\n"
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
                        argument_filters={"from": sender, "to": receiver},
                    )

                    logger.debug(
                        f"[USDT Scan] Chunk {current_start}-{current_end}: "
                        f"{len(logs)} logs"
                    )

                    for log in logs:
                        args = log.get("args", {})
                        value = args.get("value", 0)
                        total_wei += value

                        transactions.append(
                            {
                                "tx_hash": log["transactionHash"].hex(),
                                "amount": Decimal(value) / Decimal(10**USDT_DECIMALS),
                                "block": log["blockNumber"],
                            }
                        )

                except Exception as chunk_error:
                    logger.warning(
                        f"[USDT Scan] Chunk {current_start}-{current_end} "
                        f"failed: {chunk_error}"
                    )

                current_end = current_start

            # Sort by block number (oldest first)
            transactions.sort(key=lambda x: x["block"])

            result = {
                "total_amount": Decimal(total_wei) / Decimal(10**USDT_DECIMALS),
                "tx_count": len(transactions),
                "transactions": transactions,
                "from_block": from_block,
                "to_block": latest,
                "success": True,
            }

            # Detailed result logging
            if result["tx_count"] > 0:
                logger.success(
                    f"[USDT Scan] Found deposits for {mask_address(user_wallet)}:\n"
                    f"  Total amount: {result['total_amount']} USDT\n"
                    f"  Transactions: {result['tx_count']}\n"
                    f"  Block range scanned: {from_block} - {latest}"
                )
                for tx in transactions:
                    logger.info(
                        f"  -> TX: {tx['tx_hash'][:16]}..., "
                        f"Amount: {tx['amount']} USDT, Block: {tx['block']}"
                    )
            else:
                logger.warning(
                    f"[USDT Scan] No deposits found for {mask_address(user_wallet)}:\n"
                    f"  Searched from={sender} to={receiver}\n"
                    f"  Block range: {from_block} - {latest}\n"
                    f"  Verify user sent USDT to correct address: {receiver}"
                )

            return result

        except Exception as e:
            logger.error(f"Deposit scan failed for {mask_address(user_wallet)}: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_amount": Decimal("0"),
                "tx_count": 0,
                "transactions": [],
            }

    def verify_plex_transfer(
        self,
        w3: Web3,
        from_address: str,
        amount: Decimal,
        lookback_blocks: int = 200,
    ) -> dict[str, Any]:
        """
        Verify PLEX token transfer from address to system wallet.

        This is an alias for verify_plex_payment_sync with a different signature
        to match the requested interface.

        Args:
            w3: Web3 instance
            from_address: Sender's wallet address
            amount: Required PLEX amount (Decimal)
            lookback_blocks: Number of blocks to scan back

        Returns:
            Dict with success, tx_hash, amount, block, timestamp, or error
        """
        if not self.plex_token_address:
            return {"success": False, "error": "PLEX token address not configured"}

        try:
            sender = to_checksum_address(from_address)
            receiver = self.system_wallet_address
            token_address = self.plex_token_address
        except ValueError as e:
            return {"success": False, "error": f"Invalid address format: {e}"}

        # Convert Decimal to wei (PLEX uses 9 decimals)
        target_wei = int(amount * Decimal(10**PLEX_DECIMALS))

        logger.info(
            f"[PLEX Transfer Verify] from={mask_address(sender)}, "
            f"to={mask_address(receiver)}, amount={amount} PLEX"
        )

        latest = w3.eth.block_number
        contract = w3.eth.contract(address=token_address, abi=PLEX_ABI)

        # Scan in chunks to avoid RPC rate limits
        chunk_size = 100
        total_blocks = lookback_blocks
        all_logs = []

        logger.info(
            f"[PLEX Transfer Verify] Scanning {total_blocks} blocks "
            f"in chunks of {chunk_size}"
        )

        for offset in range(0, total_blocks, chunk_size):
            from_blk = max(0, latest - offset - chunk_size)
            to_blk = latest - offset

            if from_blk >= to_blk:
                continue

            try:
                logs = contract.events.Transfer.get_logs(
                    fromBlock=from_blk,
                    toBlock=to_blk,
                    argument_filters={"from": sender, "to": receiver},
                )
                chunk_logs = list(logs)
                all_logs.extend(chunk_logs)
                logger.debug(
                    f"[PLEX Transfer Verify] Chunk {from_blk}-{to_blk}: "
                    f"{len(chunk_logs)} logs"
                )
            except Exception as chunk_err:
                logger.warning(
                    f"[PLEX Transfer Verify] Chunk {from_blk}-{to_blk} "
                    f"failed: {chunk_err}"
                )
                continue

        logger.info(f"[PLEX Transfer Verify] Total found: {len(all_logs)} transfers")

        # Sort by block number (newest first)
        all_logs.sort(key=lambda x: x.get("blockNumber", 0), reverse=True)

        for log in all_logs:
            args = log.get("args", {})
            value = args.get("value", 0)
            tx_hash = log.get("transactionHash", b"").hex()
            block_num = log.get("blockNumber", 0)

            if value >= target_wei:
                amount_found = Decimal(value) / Decimal(10**PLEX_DECIMALS)

                # Get block timestamp
                try:
                    block = w3.eth.get_block(block_num)
                    timestamp = block.get("timestamp", 0)
                except Exception as e:
                    logger.warning(f"Failed to get block timestamp: {e}")
                    timestamp = 0

                logger.success(
                    f"[PLEX Transfer Verify] VERIFIED! TX={tx_hash}, "
                    f"amount={amount_found} PLEX, block={block_num}"
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
        return {"success": False, "error": "Transfer not found or amount insufficient"}

    def scan_plex_payments(
        self,
        w3: Web3,
        from_address: str,
        since_block: int | None = None,
        max_blocks: int = 100000,
    ) -> list[dict[str, Any]]:
        """
        Scan all PLEX Transfer events from user wallet to system wallet.

        Args:
            w3: Web3 instance
            from_address: User's wallet address
            since_block: Starting block number (if None, scan from max_blocks ago)
            max_blocks: Maximum number of blocks to scan back (if since_block is None)

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
                f"[PLEX Scan] Scanning PLEX payments from {mask_address(sender)} "
                f"to {mask_address(receiver)}, blocks {from_block} to {latest}"
            )

            contract = w3.eth.contract(address=token_address, abi=PLEX_ABI)

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
                    logger.warning(f"Failed to get block {block_num} timestamp: {e}")
                    timestamp = 0

                payments.append(
                    {
                        "tx_hash": tx_hash,
                        "amount": Decimal(value) / Decimal(10**PLEX_DECIMALS),
                        "block": block_num,
                        "timestamp": timestamp,
                    }
                )

            # Sort by block number (oldest first)
            payments.sort(key=lambda x: x["block"])

            logger.info(
                f"[PLEX Scan] Found {len(payments)} PLEX payments "
                f"from {mask_address(sender)}"
            )

            return payments

        except Exception as e:
            logger.error(f"PLEX payment scan failed for {mask_address(from_address)}: {e}")
            return []
