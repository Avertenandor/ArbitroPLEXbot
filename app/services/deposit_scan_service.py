"""
Deposit Scan Service.

Scans blockchain for user deposits (USDT transfers to system wallet).
Used for automatic deposit detection at authorization and periodic updates.
"""

from datetime import UTC, datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.services.blockchain_service import get_blockchain_service

# Minimum deposit to be considered an active depositor
MINIMUM_DEPOSIT_USDT = Decimal("30")


class DepositScanService:
    """
    Service for scanning and tracking user deposits from blockchain.

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
        Scan blockchain for user's USDT deposits to system wallet.

        Updates user's deposit tracking fields in database.

        Args:
            user_id: User ID

        Returns:
            Dict with scan results:
            - success: bool
            - total_amount: Decimal
            - tx_count: int
            - is_active: bool (>= 30 USDT)
            - required_plex: Decimal
            - error: str (if failed)
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            return {
                "success": False,
                "error": "User not found",
            }

        if not user.wallet_address:
            return {
                "success": False,
                "error": "User has no wallet address",
            }

        blockchain = get_blockchain_service()

        # Scan blockchain for deposits
        scan_result = await blockchain.get_user_usdt_deposits(
            user_wallet=user.wallet_address,
            max_blocks=100000,  # ~3.5 days on BSC
        )

        if not scan_result.get("success"):
            logger.error(
                f"Deposit scan failed for user {user_id}: "
                f"{scan_result.get('error')}"
            )
            return {
                "success": False,
                "error": scan_result.get("error", "Scan failed"),
            }

        total_amount = scan_result.get("total_amount", Decimal("0"))
        tx_count = scan_result.get("tx_count", 0)
        is_active = total_amount >= MINIMUM_DEPOSIT_USDT
        required_plex = total_amount * Decimal("10")  # 10 PLEX per dollar per day

        # Update user in database
        now = datetime.now(UTC)
        user.total_deposited_usdt = total_amount
        user.is_active_depositor = is_active
        user.last_deposit_scan_at = now
        user.deposit_tx_count = tx_count

        await self._session.flush()

        logger.info(
            f"Deposit scan completed for user {user_id}: "
            f"total={total_amount} USDT, txs={tx_count}, active={is_active}"
        )

        return {
            "success": True,
            "total_amount": total_amount,
            "tx_count": tx_count,
            "is_active": is_active,
            "required_plex": required_plex,
            "transactions": scan_result.get("transactions", []),
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
