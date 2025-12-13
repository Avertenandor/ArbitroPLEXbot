"""
Deposit service facade.

Provides backward compatibility with the original DepositService API
while delegating to specialized modules.
"""

from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.repositories.deposit_repository import DepositRepository
from app.repositories.user_repository import UserRepository
from app.services.deposit.lifecycle.confirmer import DepositConfirmer
from app.services.deposit.lifecycle.creator import DepositCreator
from app.services.deposit.lifecycle.status_manager import DepositStatusManager
from app.services.deposit.roi.calculator import ROICalculator


class DepositService:
    """
    Deposit service facade.

    Maintains backward compatibility with original DepositService API.
    Delegates operations to specialized modules:
    - DepositCreator: Deposit creation and validation
    - DepositConfirmer: Confirmation and activation
    - DepositStatusManager: Status transitions
    - ROICalculator: ROI calculations
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize deposit service facade."""
        self.session = session
        self.deposit_repo = DepositRepository(session)
        self.user_repo = UserRepository(session)

        # Initialize specialized modules
        self.creator = DepositCreator(session)
        self.confirmer = DepositConfirmer(session)
        self.status_manager = DepositStatusManager(session)
        self.roi_calculator = ROICalculator(session)

    async def create_deposit(
        self,
        user_id: int,
        level: int,
        amount: Decimal,
        tx_hash: str | None = None,
        redis_client: Any | None = None,
    ) -> Deposit:
        """
        Create new deposit with proper error handling.

        Delegates to DepositCreator.validate_and_create().

        Args:
            user_id: User ID
            level: Deposit level (1-5)
            amount: Deposit amount
            tx_hash: Blockchain transaction hash
            redis_client: Optional Redis client for distributed lock

        Returns:
            Created deposit

        Raises:
            ValueError: If level or amount is invalid
        """
        return await self.creator.validate_and_create(
            user_id=user_id,
            level_type=level,
            amount=amount,
            tx_hash=tx_hash,
            redis_client=redis_client,
        )

    async def confirm_deposit(
        self, deposit_id: int, block_number: int
    ) -> Deposit | None:
        """
        Confirm deposit after blockchain confirmation.

        Delegates to DepositConfirmer.activate_deposit().

        Args:
            deposit_id: Deposit ID
            block_number: Confirmation block number

        Returns:
            Updated deposit
        """
        return await self.confirmer.activate_deposit(
            deposit_id=deposit_id,
            block_number=block_number,
        )

    async def get_active_deposits(
        self, user_id: int
    ) -> list[Deposit]:
        """Get user's active deposits (ROI not completed)."""
        return await self.deposit_repo.get_active_deposits(user_id)

    async def get_level1_roi_progress(self, user_id: int) -> dict:
        """
        Get ROI progress for level 1 deposits.

        Delegates to ROICalculator.get_level1_roi_progress().

        Args:
            user_id: User ID

        Returns:
            Dict with ROI progress information
        """
        return await self.roi_calculator.get_level1_roi_progress(user_id)

    async def get_platform_stats(self) -> dict:
        """
        Get platform-wide deposit statistics.

        Uses SQL aggregation to avoid OOM on large datasets.

        Returns:
            Dict with total deposits, amounts, and breakdown by level
        """
        from sqlalchemy import func, select

        from app.models.enums import TransactionStatus

        # Aggregate stats through SQL
        stats_stmt = select(
            func.count(Deposit.id).label('total'),
            func.sum(Deposit.amount).label('total_amount'),
            func.count(func.distinct(Deposit.user_id)).label('unique_users')
        ).where(Deposit.status == TransactionStatus.CONFIRMED.value)

        result = await self.session.execute(stats_stmt)
        stats = result.one()

        # Count by level using SQL group by
        level_stats_stmt = select(
            Deposit.level,
            func.count(Deposit.id).label('count')
        ).where(
            Deposit.status == TransactionStatus.CONFIRMED.value
        ).group_by(Deposit.level)

        level_result = await self.session.execute(level_stats_stmt)
        level_rows = level_result.all()

        # Build deposits_by_level dict
        deposits_by_level = {level: 0 for level in [1, 2, 3, 4, 5]}
        for row in level_rows:
            deposits_by_level[row.level] = row.count

        return {
            "total_deposits": stats.total or 0,
            "total_amount": stats.total_amount or Decimal("0"),
            "total_users": stats.unique_users or 0,
            "deposits_by_level": deposits_by_level,
        }

    async def get_detailed_stats(self) -> list[dict]:
        """
        Get detailed deposit statistics for admin.

        Returns:
            List of dicts with deposit details
        """
        from sqlalchemy import select

        from app.models.enums import TransactionStatus
        from app.models.user import User

        # Join User to get username
        stmt = (
            select(Deposit, User)
            .join(User, Deposit.user_id == User.id)
            .where(
                Deposit.status == TransactionStatus.CONFIRMED.value,
                Deposit.is_roi_completed.is_(False)
            )
            .order_by(Deposit.created_at.desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        stats = []
        for deposit, user in rows:
            stats.append({
                "deposit_id": deposit.id,
                "user_id": user.id,
                "username": user.username or str(user.telegram_id),
                "amount": deposit.amount,
                "roi_paid": deposit.roi_paid_amount,
                "roi_cap": deposit.roi_cap_amount,
                "next_accrual_at": deposit.next_accrual_at,
                "level": deposit.level
            })

        return stats

    async def get_deposit_status_with_confirmations(
        self, deposit_id: int
    ) -> dict[str, Any]:
        """
        Get deposit status with blockchain confirmations.

        Args:
            deposit_id: Deposit ID

        Returns:
            Dict with deposit info and confirmation count
        """
        from app.models.enums import TransactionStatus
        from app.services.blockchain.rpc_wrapper import (
            BlockchainError,
            BlockchainTimeoutError,
        )
        from app.services.blockchain_service import get_blockchain_service

        deposit = await self.deposit_repo.find_by_id(deposit_id)

        if not deposit:
            return {
                "success": False,
                "error": "Депозит не найден"
            }

        result: dict[str, Any] = {
            "success": True,
            "deposit": deposit,
            "confirmations": 0,
            "required_confirmations": 12,
            "status": deposit.status,
            "estimated_time": "неизвестно"
        }

        # If deposit has tx_hash and is pending, check blockchain
        if deposit.tx_hash and deposit.status == TransactionStatus.PENDING.value:
            try:
                blockchain_service = get_blockchain_service()
                tx_status = await blockchain_service.check_transaction_status(
                    deposit.tx_hash
                )

                confirmations = tx_status.get("confirmations", 0)
                result["confirmations"] = confirmations

                # Estimate time: BSC ~3 sec/block
                remaining_blocks = max(0, 12 - confirmations)
                estimated_seconds = remaining_blocks * 3

                if estimated_seconds < 60:
                    result["estimated_time"] = f"~{estimated_seconds} сек"
                else:
                    estimated_minutes = estimated_seconds // 60
                    result["estimated_time"] = f"~{estimated_minutes} мин"

            except BlockchainTimeoutError:
                logger.warning(
                    f"Blockchain timeout while checking confirmations for deposit {deposit_id}"
                )
                result["estimated_time"] = "2-5 минут"
            except BlockchainError as e:
                logger.error(
                    f"Blockchain error checking confirmations for deposit {deposit_id}: {e}"
                )
                result["estimated_time"] = "2-5 минут"
            except (ConnectionError, TimeoutError) as e:
                logger.warning(
                    f"Network error checking confirmations for deposit {deposit_id}: {e}"
                )
                result["estimated_time"] = "2-5 минут"
            except (KeyError, ValueError, AttributeError) as e:
                logger.error(
                    f"Data parsing error for deposit {deposit_id}: {e}",
                    exc_info=True
                )
                result["estimated_time"] = "2-5 минут"
            except RuntimeError as e:
                logger.error(
                    f"Runtime error checking deposit {deposit_id}: {e}"
                )
                result["estimated_time"] = "2-5 минут"

        return result
