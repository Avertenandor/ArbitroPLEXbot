"""
Wallet verification service.

Performs on-chain checks for PLEX/USDT balances and basic level detection.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from loguru import logger

from app.services.blockchain_service import get_blockchain_service
from app.utils.validation import validate_bsc_address
from bot.constants import rules


@dataclass
class WalletVerificationResult:
    """Result of on-chain wallet verification."""

    address: str
    is_format_valid: bool
    is_onchain_ok: bool
    plex_balance: Decimal | None = None
    usdt_balance: Decimal | None = None
    detected_level: int = 0
    has_required_plex: bool = False
    has_required_rabbits: bool = False
    error: str | None = None


class WalletVerificationService:
    """Service for verifying user wallet on-chain."""

    async def verify_wallet(self, address: str) -> WalletVerificationResult:
        """
        Verify wallet format and fetch PLEX/USDT balances.

        Args:
            address: BSC wallet address string from user input.

        Returns:
            WalletVerificationResult with balances and flags.
        """
        raw_address = (address or "").strip()
        is_format_valid = validate_bsc_address(raw_address, checksum=False)

        result = WalletVerificationResult(
            address=raw_address,
            is_format_valid=is_format_valid,
            is_onchain_ok=False,
        )

        if not is_format_valid:
            result.error = "Invalid wallet format"
            return result

        try:
            blockchain = get_blockchain_service()
        except RuntimeError as exc:
            # BlockchainService not initialised (e.g. tests or maintenance)
            logger.warning(f"Wallet verification skipped: {exc}")
            result.error = "Blockchain service not available"
            return result

        try:
            plex_balance = await blockchain.get_plex_balance(raw_address)
            usdt_balance = await blockchain.get_usdt_balance(raw_address)
            result.plex_balance = plex_balance
            result.usdt_balance = usdt_balance

            if plex_balance is None or usdt_balance is None:
                result.error = "Failed to fetch wallet balances"
                return result

            result.is_onchain_ok = True

            # Level detection based on PLEX balance (integer tokens)
            try:
                plex_int = int(plex_balance)
            except (TypeError, ValueError):
                plex_int = 0

            result.detected_level = rules.get_user_level(plex_int)
            result.has_required_plex = plex_int >= rules.MINIMUM_PLEX_BALANCE

            # TODO: has_required_rabbits will be implemented when on-chain
            # rabbit token checks are available.
            result.has_required_rabbits = False

            logger.info(
                "Wallet verification result",
                extra={
                    "address": raw_address,
                    "plex_balance": str(plex_balance),
                    "usdt_balance": str(usdt_balance),
                    "detected_level": result.detected_level,
                    "has_required_plex": result.has_required_plex,
                },
            )
            return result
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"Wallet verification failed for {raw_address}: {exc}")
            result.error = str(exc)
            return result


