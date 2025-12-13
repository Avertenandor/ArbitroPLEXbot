"""
Deposit Scan Service.

Scans blockchain for user deposits (USDT transfers to system wallet).
Uses cached transactions first, then scans blockchain for new data.
"""

from datetime import UTC, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.services.blockchain_service import get_blockchain_service
from app.utils.security import mask_address
from app.utils.validation import is_placeholder_wallet, is_valid_wallet_for_transactions


# Minimum deposit to be considered an active depositor
MINIMUM_DEPOSIT_USDT = Decimal("30")


class DepositScanService:
    """
    Service for scanning and tracking user deposits from blockchain.

    Uses a two-tier approach:
    1. First check cached transactions in database
    2. If insufficient, scan blockchain and cache new transactions

    Responsibilities:
    - Scan USDT transfers from user wallet to system wallet
    - Update user's total_deposited_usdt and is_active_depositor
    - Check minimum deposit requirements
    - Calculate required PLEX amount
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self._session = session
        self._user_repo = UserRepository(session)

    async def scan_user_deposits(self, user_id: int) -> dict:
        """
        Scan for user's USDT deposits to system wallet.

        Uses cache-first strategy:
        1. Check cached transactions in database
        2. If needed, scan blockchain and update cache

        Args:
            user_id: User ID

        Returns:
            Dict with scan results:
            - success: bool
            - total_amount: Decimal
            - tx_count: int
            - is_active: bool (>= 30 USDT)
            - required_plex: Decimal
            - from_cache: bool
            - error: str (if failed)
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            logger.warning(f"[Deposit Scan] User {user_id} not found")
            return {
                "success": False,
                "error": "User not found",
            }

        if not user.wallet_address:
            logger.warning(f"[Deposit Scan] User {user_id} has no wallet address")
            return {
                "success": False,
                "error": "User has no wallet address",
            }

        # Validate wallet address is a proper hex address (not a placeholder)
        wallet = user.wallet_address
        if is_placeholder_wallet(wallet):
            logger.warning(
                f"[Deposit Scan] User {user_id} has placeholder/invalid wallet address: "
                f"{wallet[:20]}... - skipping blockchain scan"
            )
            return {
                "success": False,
                "error": "У пользователя нет реального кошелька (временный адрес). "
                "Попросите пользователя привязать свой кошелёк.",
            }

        if not is_valid_wallet_for_transactions(wallet):
            logger.warning(
                f"[Deposit Scan] User {user_id} has invalid wallet "
                f"address: {wallet[:20]}..."
            )
            return {
                "success": False,
                "error": "Некорректный формат адреса кошелька. "
                "Адрес должен быть валидным BSC-адресом (0x + 40 hex символов).",
            }

        logger.info(
            f"[Deposit Scan] Starting scan for user {user_id}, "
            f"wallet: {mask_address(user.wallet_address)}"
        )

        # Try cache first
        try:
            from app.services.blockchain_tx_cache_service import BlockchainTxCacheService

            cache_service = BlockchainTxCacheService(self._session)
            cached_result = await cache_service.get_cached_deposits(
                user_wallet=user.wallet_address,
                token_type="USDT",
            )

            if cached_result.get("success") and cached_result.get("tx_count", 0) > 0:
                total_amount = cached_result.get("total_amount", Decimal("0"))

                # If we have enough from cache, use it
                if total_amount >= MINIMUM_DEPOSIT_USDT:
                    tx_count = cached_result.get("tx_count", 0)
                    is_active = True
                    required_plex = total_amount * Decimal("10")

                    # Update user in database
                    now = datetime.now(UTC)
                    user.total_deposited_usdt = total_amount
                    user.is_active_depositor = is_active
                    user.last_deposit_scan_at = now
                    user.deposit_tx_count = tx_count

                    await self._session.flush()

                    logger.info(
                        f"[CACHE HIT] Deposit data for user {user_id}: "
                        f"total={total_amount} USDT, txs={tx_count}"
                    )

                    return {
                        "success": True,
                        "total_amount": total_amount,
                        "tx_count": tx_count,
                        "is_active": is_active,
                        "required_plex": required_plex,
                        "transactions": cached_result.get("transactions", []),
                        "from_cache": True,
                    }

        except ImportError:
            logger.debug("Cache service not available, falling back to blockchain")
        except Exception as cache_error:
            logger.warning(f"Cache lookup failed: {cache_error}, falling back to blockchain")

        # Fall back to blockchain scan
        blockchain = get_blockchain_service()

        # Scan blockchain for deposits (with smaller block range)
        scan_result = await blockchain.get_user_usdt_deposits(
            user_wallet=user.wallet_address,
            max_blocks=50000,  # Reduced from 100000 to avoid RPC limits
        )

        if not scan_result.get("success"):
            logger.error(f"Deposit scan failed for user {user_id}: {scan_result.get('error')}")
            return {
                "success": False,
                "error": scan_result.get("error", "Scan failed"),
            }

        total_amount = scan_result.get("total_amount", Decimal("0"))
        tx_count = scan_result.get("tx_count", 0)
        is_active = total_amount >= MINIMUM_DEPOSIT_USDT
        required_plex = total_amount * Decimal("10")  # 10 PLEX per dollar per day

        # Cache the transactions we found
        try:
            from app.config.settings import settings
            from app.repositories.blockchain_tx_cache_repository import (
                BlockchainTxCacheRepository,
            )
            from app.services.blockchain_tx_cache_service import (
                BlockchainTxCacheService,
            )

            cache_repo = BlockchainTxCacheRepository(self._session)

            for tx in scan_result.get("transactions", []):
                await cache_repo.cache_transaction(
                    tx_hash=tx.get("tx_hash", ""),
                    block_number=tx.get("block", 0),
                    from_address=user.wallet_address,
                    to_address=settings.system_wallet_address or "",
                    token_type="USDT",
                    token_address=settings.usdt_contract_address,
                    amount=tx.get("amount", Decimal("0")),
                    direction="incoming",
                    user_id=user_id,
                )

            await self._session.commit()
            logger.info(f"[CACHE UPDATE] Cached {tx_count} transactions for user {user_id}")

        except Exception as cache_error:
            logger.warning(f"Failed to cache transactions: {cache_error}")

        # Update user in database
        now = datetime.now(UTC)
        user.total_deposited_usdt = total_amount
        user.is_active_depositor = is_active
        user.last_deposit_scan_at = now
        user.deposit_tx_count = tx_count

        await self._session.flush()

        logger.info(
            f"[BLOCKCHAIN] Deposit scan for user {user_id}: "
            f"total={total_amount} USDT, txs={tx_count}, active={is_active}"
        )

        return {
            "success": True,
            "total_amount": total_amount,
            "tx_count": tx_count,
            "is_active": is_active,
            "required_plex": required_plex,
            "transactions": scan_result.get("transactions", []),
            "from_cache": False,
        }

    async def check_minimum_deposit(self, user_id: int) -> dict:
        """
        Check if user meets minimum deposit requirement (>= 30 USDT).

        Args:
            user_id: User ID

        Returns:
            Dict with:
            - meets_minimum: bool
            - current_deposit: Decimal
            - minimum_required: Decimal
            - shortage: Decimal (if not meeting minimum)
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return {
                "meets_minimum": False,
                "error": "User not found",
            }

        current = user.total_deposited_usdt or Decimal("0")
        meets_minimum = current >= MINIMUM_DEPOSIT_USDT
        shortage = max(Decimal("0"), MINIMUM_DEPOSIT_USDT - current)

        return {
            "meets_minimum": meets_minimum,
            "current_deposit": current,
            "minimum_required": MINIMUM_DEPOSIT_USDT,
            "shortage": shortage,
        }

    async def get_required_plex(self, user_id: int) -> Decimal:
        """
        Calculate required daily PLEX based on user's deposit amount.

        Formula: deposit_amount * 10 PLEX per day.

        Args:
            user_id: User ID

        Returns:
            Required PLEX amount per day
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return Decimal("0")

        return (user.total_deposited_usdt or Decimal("0")) * Decimal("10")

    async def get_deposit_status(self, user_id: int) -> dict:
        """
        Get comprehensive deposit status for user.

        Args:
            user_id: User ID

        Returns:
            Dict with deposit status details
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "User not found",
            }

        current_deposit = user.total_deposited_usdt or Decimal("0")
        is_active = user.is_active_depositor
        required_plex = current_deposit * Decimal("10")

        return {
            "success": True,
            "user_id": user_id,
            "wallet_address": user.wallet_address,
            "current_deposit": current_deposit,
            "is_active_depositor": is_active,
            "required_daily_plex": required_plex,
            "minimum_deposit": MINIMUM_DEPOSIT_USDT,
            "shortage": max(Decimal("0"), MINIMUM_DEPOSIT_USDT - current_deposit),
            "tx_count": user.deposit_tx_count or 0,
            "last_scan_at": user.last_deposit_scan_at,
        }

    async def get_insufficient_deposit_message(self, user_id: int) -> str | None:
        """
        Get message explaining insufficient deposit.

        Args:
            user_id: User ID

        Returns:
            Warning message or None if deposit is sufficient
        """
        from app.config.settings import settings

        check = await self.check_minimum_deposit(user_id)

        if check.get("meets_minimum"):
            return None

        current = check.get("current_deposit", Decimal("0"))
        shortage = check.get("shortage", MINIMUM_DEPOSIT_USDT)

        return (
            f"⚠️ **НЕДОСТАТОЧНЫЙ ДЕПОЗИТ**\n\n"
            f"Для работы в боте необходимо внести минимум **30 USDT**.\n\n"
            f"📊 **Ваш текущий депозит:** {current:.2f} USDT\n"
            f"📊 **Минимум:** {MINIMUM_DEPOSIT_USDT:.2f} USDT\n"
            f"📊 **Недостаток:** {shortage:.2f} USDT\n\n"
            f"💳 **Кошелек для пополнения:**\n"
            f"`{settings.system_wallet_address}`\n\n"
            f"⚠️ Отправляйте только **USDT (BEP-20)** на сети BSC!\n\n"
            f"После пополнения нажмите кнопку «Обновить депозит» "
            f"или дождитесь автоматического обновления (каждый час)."
        )

    async def scan_and_validate(self, user_id: int) -> dict:
        """
        Scan deposits and validate minimum requirement.

        Combines scan and validation in one call.
        Used at authorization.

        Args:
            user_id: User ID

        Returns:
            Dict with scan results and validation status
        """
        # First scan
        scan_result = await self.scan_user_deposits(user_id)

        if not scan_result.get("success"):
            return scan_result

        # Then validate
        is_valid = scan_result.get("is_active", False)

        if not is_valid:
            message = await self.get_insufficient_deposit_message(user_id)
            scan_result["validation_message"] = message
            scan_result["is_valid"] = False
        else:
            scan_result["is_valid"] = True
            scan_result["validation_message"] = None

        return scan_result
