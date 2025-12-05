"""
PLEX Payment Service.

Manages PLEX payment requirements, verification, and access level checks.
"""

from datetime import datetime
from decimal import Decimal

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plex_payment import PlexPaymentRequirement, PlexPaymentStatus
from app.repositories.deposit_repository import DepositRepository
from app.repositories.plex_payment_repository import PlexPaymentRepository
from app.repositories.user_repository import UserRepository
from app.services.blockchain_service import get_blockchain_service
from bot.constants.rules import (
    LEVELS,
    PLEX_PER_DOLLAR_DAILY,
    get_max_deposits_for_plex_balance,
    get_user_level,
)


class PlexPaymentService:
    """
    Service for managing PLEX payments.

    Handles:
    - User level verification based on PLEX balance
    - Daily payment tracking and verification
    - Warning and blocking for non-payment
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service with database session."""
        self._session = session
        self._plex_repo = PlexPaymentRepository(session)
        self._deposit_repo = DepositRepository(session)
        self._user_repo = UserRepository(session)

    async def check_user_plex_level(
        self, user_id: int
    ) -> dict:
        """
        Check user's PLEX level and access permissions.

        Args:
            user_id: User ID

        Returns:
            Dict with level info and access status
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.wallet_address:
            return {
                "level": 0,
                "plex_balance": Decimal("0"),
                "can_access": False,
                "error": "User not found or no wallet",
            }

        blockchain = get_blockchain_service()
        plex_balance = await blockchain.get_plex_balance(user.wallet_address)

        if plex_balance is None:
            logger.error(f"Failed to get PLEX balance for user {user_id} - denying access")
            return {
                "level": 0,
                "plex_balance": Decimal("0"),
                "can_access": False,  # Безопасный дефолт - запретить доступ при ошибке
                "error": "Could not verify PLEX balance. Please try again later.",
            }

        level = get_user_level(plex_balance)
        max_deposits = get_max_deposits_for_plex_balance(plex_balance)

        # Get user's active deposits count
        active_deposits = await self._deposit_repo.get_active_deposits(user_id)
        current_deposits = len(active_deposits) if active_deposits else 0

        # Check if user can create new deposit based on their PLEX level
        # Use strict < to allow room for new deposit
        can_access = current_deposits < max_deposits

        return {
            "level": level,
            "plex_balance": plex_balance,
            "max_deposits": max_deposits,
            "current_deposits": current_deposits,
            "can_access": can_access,
            "required_plex": LEVELS.get(level + 1, {}).get("plex", 0) if level < 5 else 0,
        }

    async def create_payment_requirement(
        self,
        user_id: int,
        deposit_id: int,
        deposit_amount: Decimal,
        deposit_created_at: datetime,
    ) -> PlexPaymentRequirement:
        """
        Create PLEX payment requirement for a new deposit.

        Args:
            user_id: User ID
            deposit_id: Deposit ID
            deposit_amount: Deposit amount in USD
            deposit_created_at: When deposit was created

        Returns:
            Created PlexPaymentRequirement
        """
        daily_plex = deposit_amount * Decimal(str(PLEX_PER_DOLLAR_DAILY))

        return await self._plex_repo.create(
            user_id=user_id,
            deposit_id=deposit_id,
            daily_plex_required=daily_plex,
            deposit_created_at=deposit_created_at,
        )

    async def get_user_payment_status(
        self, user_id: int
    ) -> dict:
        """
        Get comprehensive payment status for user.

        Args:
            user_id: User ID

        Returns:
            Dict with payment status details
        """
        payments = await self._plex_repo.get_active_by_user_id(user_id)

        total_daily_required = Decimal("0")
        overdue_count = 0
        warning_count = 0
        blocked_count = 0

        payment_details = []

        for payment in payments:
            total_daily_required += payment.daily_plex_required

            if payment.status == PlexPaymentStatus.WARNING_SENT:
                warning_count += 1
            elif payment.status == PlexPaymentStatus.BLOCKED:
                blocked_count += 1
            elif payment.is_payment_overdue():
                overdue_count += 1

            payment_details.append({
                "deposit_id": payment.deposit_id,
                "daily_required": payment.daily_plex_required,
                "status": payment.status,
                "next_due": payment.next_payment_due,
                "is_overdue": payment.is_payment_overdue(),
            })

        return {
            "total_daily_plex": total_daily_required,
            "active_deposits": len(payments),
            "overdue_count": overdue_count,
            "warning_count": warning_count,
            "blocked_count": blocked_count,
            "has_issues": overdue_count > 0 or warning_count > 0 or blocked_count > 0,
            "payment_details": payment_details,
        }

    async def verify_daily_payment(
        self,
        user_id: int,
        sender_wallet: str,
    ) -> dict:
        """
        Verify PLEX payment from user's wallet to system wallet.

        Checks recent transfers from sender to system wallet.

        Args:
            user_id: User ID
            sender_wallet: User's wallet address

        Returns:
            Dict with verification result
        """
        blockchain = get_blockchain_service()

        # Get required amount for user's deposits
        required = await self._plex_repo.get_total_daily_plex_required(user_id)

        # Check for PLEX transfers to system wallet
        # lookback_blocks=200 covers ~10 minutes on BSC (3 sec/block)
        # Note: verify_plex_payment accepts float for amount_plex (non-financial display value)
        # OK to use float here - verification only, not financial calculation
        result = await blockchain.verify_plex_payment(
            sender_address=sender_wallet,
            amount_plex=float(required),
            lookback_blocks=200,
        )

        if not result.get("success"):
            return {
                "success": False,
                "error": "Payment not found",
            }

        # Check if received amount is sufficient
        received = Decimal(str(result.get("amount", 0)))

        if received < required:
            error_msg = (
                f"Insufficient payment: received {received} PLEX, "
                f"required {required} PLEX"
            )
            return {
                "success": False,
                "error": error_msg,
                "received": received,
                "required": required,
            }

        return {
            "success": True,
            "tx_hash": result.get("tx_hash"),
            "amount": received,
            "required": required,
        }

    async def process_payment_for_deposit(
        self,
        deposit_id: int,
        tx_hash: str,
        amount: Decimal,
    ) -> PlexPaymentRequirement | None:
        """
        Process confirmed PLEX payment for a deposit.

        Args:
            deposit_id: Deposit ID
            tx_hash: Transaction hash
            amount: Amount paid

        Returns:
            Updated payment requirement or None
        """
        payment = await self._plex_repo.get_by_deposit_id(deposit_id)
        if not payment:
            logger.warning(f"No payment requirement for deposit {deposit_id}")
            return None

        return await self._plex_repo.mark_paid(payment.id, tx_hash, amount)

    async def check_plex_balance_sufficient(
        self, user_id: int
    ) -> dict:
        """
        Check if user has sufficient PLEX balance for their deposits.

        Args:
            user_id: User ID

        Returns:
            Dict with check result
        """
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.wallet_address:
            return {
                "sufficient": False,
                "error": "User not found or no wallet",
            }

        # Get PLEX balance
        blockchain = get_blockchain_service()
        plex_balance = await blockchain.get_plex_balance(user.wallet_address)

        if plex_balance is None:
            logger.error(
                f"Failed to verify PLEX balance for user {user_id} - "
                f"reporting insufficient"
            )
            return {
                "sufficient": False,  # Безопасный дефолт - запретить при ошибке
                "error": "Could not verify balance. Please try again later.",
            }

        # Get user's level and allowed deposits
        level = get_user_level(plex_balance)
        max_deposits = get_max_deposits_for_plex_balance(plex_balance)

        # Get current active deposits
        active_deposits = await self._deposit_repo.get_active_deposits(user_id)
        current_count = len(active_deposits) if active_deposits else 0

        sufficient = current_count <= max_deposits

        if not sufficient:
            required_level = 0
            for lvl in range(1, 6):
                if LEVELS[lvl]["deposits"] >= current_count:
                    required_level = lvl
                    break

            required_plex = LEVELS.get(required_level, {}).get("plex", 0)
            shortage = Decimal(required_plex) - plex_balance

            return {
                "sufficient": False,
                "plex_balance": plex_balance,
                "level": level,
                "current_deposits": current_count,
                "max_allowed": max_deposits,
                "required_plex": required_plex,
                "shortage": shortage,
            }

        return {
            "sufficient": True,
            "plex_balance": plex_balance,
            "level": level,
            "current_deposits": current_count,
            "max_allowed": max_deposits,
        }

    async def get_insufficient_plex_message(
        self, user_id: int
    ) -> str | None:
        """
        Get warning message if user has insufficient PLEX.

        Args:
            user_id: User ID

        Returns:
            Warning message or None if sufficient
        """
        check = await self.check_plex_balance_sufficient(user_id)

        if check.get("sufficient"):
            return None

        if check.get("error"):
            return None  # Don't block on check errors

        shortage = check.get("shortage", 0)
        required = check.get("required_plex", 0)
        current = check.get("plex_balance", 0)

        return (
            f"⚠️ **ВНИМАНИЕ: Недостаточный баланс PLEX!**\n\n"
            f"Для работы с вашими депозитами требуется:\n"
            f"• Баланс PLEX: **{required:,}** токенов\n"
            f"• Ваш баланс: **{int(current):,}** токенов\n"
            f"• Недостаток: **{shortage:,}** токенов\n\n"
            f"❌ **Без достаточного баланса PLEX:**\n"
            f"• Новые депозиты будут заблокированы\n"
            f"• Существующие депозиты могут быть возвращены\n\n"
            f"Пополните баланс PLEX на кошельке для продолжения работы."
        )

    async def calculate_plex_forecast(self, user_id: int) -> dict:
        """
        Calculate PLEX consumption forecast for user.

        Calculates daily PLEX cost based on active deposits and estimates
        how many days the current PLEX balance will last.

        Args:
            user_id: User ID

        Returns:
            Dict containing:
                - daily_plex: Daily PLEX consumption (Decimal)
                - plex_balance: Current PLEX balance (Decimal)
                - days_left: Days until PLEX runs out (float)
                - warning: True if balance is critically low (bool)
                - active_deposits_sum: Total sum of active deposits in USD (Decimal)
                - error: Error message if unable to calculate (str | None)
        """
        # Get user data
        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.wallet_address:
            return {
                "daily_plex": Decimal("0"),
                "plex_balance": Decimal("0"),
                "days_left": 0.0,
                "warning": True,
                "active_deposits_sum": Decimal("0"),
                "error": "User not found or no wallet",
            }

        # Get total daily PLEX required
        daily_plex = await self._plex_repo.get_total_daily_plex_required(user_id)

        # Get active deposits to calculate total deposit amount
        active_deposits = await self._deposit_repo.get_active_deposits(user_id)
        active_deposits_sum = sum((d.amount for d in active_deposits), Decimal("0"))

        # Get current PLEX balance
        blockchain = get_blockchain_service()
        plex_balance = await blockchain.get_plex_balance(user.wallet_address)

        if plex_balance is None:
            logger.error(f"Failed to get PLEX balance for forecast for user {user_id}")
            return {
                "daily_plex": daily_plex,
                "plex_balance": Decimal("0"),
                "days_left": 0.0,
                "warning": True,
                "active_deposits_sum": active_deposits_sum,
                "error": "Could not verify PLEX balance. Please try again later.",
            }

        # Calculate days left
        if daily_plex > 0:
            days_left = float(plex_balance / daily_plex)
        else:
            # No active deposits - no daily cost
            days_left = float('inf')

        # Warning if less than 3 days of PLEX left
        warning = days_left < 3.0 and daily_plex > 0

        return {
            "daily_plex": daily_plex,
            "plex_balance": plex_balance,
            "days_left": days_left,
            "warning": warning,
            "active_deposits_sum": active_deposits_sum,
            "error": None,
        }
