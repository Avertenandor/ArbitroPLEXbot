"""
Payment verification operations for blockchain service.

This module provides a unified facade for:
- PLEX token payment verification (delegated to PlexPaymentVerifier)
- PLEX payment scanning (delegated to PlexPaymentScanner)
- USDT deposit scanning (delegated to UsdtDepositScanner)

The PaymentVerifier class maintains backward compatibility while
delegating operations to specialized verifiers.
"""

from decimal import Decimal
from typing import Any

from web3 import Web3

from .plex_payment_scanner import PlexPaymentScanner
from .plex_payment_verifier import PlexPaymentVerifier
from .usdt_deposit_scanner import UsdtDepositScanner


class PaymentVerifier:
    """
    Unified facade for payment verification and deposit scanning.

    Delegates operations to specialized verifiers:
    - PlexPaymentVerifier: PLEX token verification
    - PlexPaymentScanner: PLEX payment scanning
    - UsdtDepositScanner: USDT deposit operations
    """

    def __init__(
        self,
        usdt_contract_address: str,
        plex_token_address: str | None,
        system_wallet_address: str,
    ) -> None:
        """
        Initialize payment verifier with specialized sub-verifiers.

        Args:
            usdt_contract_address: USDT contract address
            plex_token_address: PLEX token contract address
            system_wallet_address: System wallet for receiving payments
        """
        # Initialize specialized verifiers
        self.plex_verifier = PlexPaymentVerifier(
            plex_token_address=plex_token_address,
            system_wallet_address=system_wallet_address,
        )

        self.plex_scanner = PlexPaymentScanner(
            plex_token_address=plex_token_address,
            system_wallet_address=system_wallet_address,
        )

        self.usdt_scanner = UsdtDepositScanner(
            usdt_contract_address=usdt_contract_address,
            system_wallet_address=system_wallet_address,
        )

        # Store addresses for backward compatibility
        self.usdt_contract_address = (
            self.usdt_scanner.usdt_contract_address
        )
        self.plex_token_address = (
            self.plex_verifier.plex_token_address
        )
        self.system_wallet_address = (
            self.plex_verifier.system_wallet_address
        )

    # PLEX verification methods - delegated to PlexPaymentVerifier

    def verify_plex_payment_sync(
        self,
        w3: Web3,
        sender_address: str,
        amount_plex: float | Decimal,
        lookback_blocks: int = 200,
    ) -> dict[str, Any]:
        """
        Verify if user paid PLEX tokens to system wallet.

        Delegates to PlexPaymentVerifier.

        Args:
            w3: Web3 instance
            sender_address: User's wallet address
            amount_plex: Required PLEX amount (float or Decimal)
            lookback_blocks: Number of blocks to scan back

        Returns:
            Dict with success, tx_hash, amount, block, or error
        """
        return self.plex_verifier.verify_plex_payment_sync(
            w3=w3,
            sender_address=sender_address,
            amount_plex=amount_plex,
            lookback_blocks=lookback_blocks,
        )

    def verify_plex_transfer(
        self,
        w3: Web3,
        from_address: str,
        amount: Decimal,
        lookback_blocks: int = 200,
    ) -> dict[str, Any]:
        """
        Verify PLEX token transfer from address to system wallet.

        Delegates to PlexPaymentVerifier.

        Args:
            w3: Web3 instance
            from_address: Sender's wallet address
            amount: Required PLEX amount (Decimal)
            lookback_blocks: Number of blocks to scan back

        Returns:
            Dict with success, tx_hash, amount, block, timestamp,
            or error
        """
        return self.plex_verifier.verify_plex_transfer(
            w3=w3,
            from_address=from_address,
            amount=amount,
            lookback_blocks=lookback_blocks,
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

        Delegates to PlexPaymentScanner.

        Args:
            w3: Web3 instance
            from_address: User's wallet address
            since_block: Starting block number
                (if None, scan from max_blocks ago)
            max_blocks: Maximum blocks to scan back
                (if since_block is None)

        Returns:
            List of payment dictionaries with tx_hash, amount,
            block, timestamp
        """
        return self.plex_scanner.scan_plex_payments(
            w3=w3,
            from_address=from_address,
            since_block=since_block,
            max_blocks=max_blocks,
        )

    # USDT scanning methods - delegated to UsdtDepositScanner

    def scan_usdt_deposits_sync(
        self,
        w3: Web3,
        user_wallet: str,
        max_blocks: int = 50000,
        chunk_size: int = 5000,
    ) -> dict[str, Any]:
        """
        Scan all USDT Transfer events from user to system wallet.

        Delegates to UsdtDepositScanner.

        Args:
            w3: Web3 instance
            user_wallet: User's wallet address
            max_blocks: Maximum number of blocks to scan back
            chunk_size: Number of blocks per scan chunk

        Returns:
            Dict with total_amount, tx_count, transactions,
            from_block, to_block, success, error
        """
        return self.usdt_scanner.scan_usdt_deposits_sync(
            w3=w3,
            user_wallet=user_wallet,
            max_blocks=max_blocks,
            chunk_size=chunk_size,
        )
