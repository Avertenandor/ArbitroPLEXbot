"""
AI Deposits Service - Operations Module.

Contains write operations for deposits (TRUSTED ADMIN ONLY):
- Change max deposit level
- Create manual deposits
- Modify deposit ROI
- Cancel deposits
- Confirm pending deposits
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from loguru import logger

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from app.utils.formatters import format_user_identifier

from .core import AIDepositsServiceCore


class AIDepositsOperationsService(AIDepositsServiceCore):
    """
    AI Deposits Service - Write Operations.

    SECURITY: All operations require TRUSTED ADMIN access.
    """

    async def change_max_deposit_level(
        self,
        new_max: int,
    ) -> dict[str, Any]:
        """
        Change maximum open deposit level.

        SECURITY: TRUSTED ADMIN only!

        Args:
            new_max: New maximum level (1-5)
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_trusted_admin():
            logger.warning(
                f"AI DEPOSITS SECURITY: Untrusted admin "
                f"{self.admin_telegram_id} attempted to change max level"
            )
            return {
                "success": False,
                "error": "❌ Нет прав на изменение настроек депозитов",
            }

        if new_max < 1 or new_max > 5:
            return {
                "success": False,
                "error": "❌ Уровень должен быть от 1 до 5",
            }

        settings_repo = GlobalSettingsRepository(self.session)
        old_settings = await settings_repo.get_settings()
        old_max = old_settings.max_open_deposit_level

        await settings_repo.update_settings(
            max_open_deposit_level=new_max
        )
        await self.session.commit()

        logger.info(
            f"AI DEPOSITS: Admin {self.admin_telegram_id} "
            f"changed max level: {old_max} → {new_max}"
        )

        return {
            "success": True,
            "old_max": old_max,
            "new_max": new_max,
            "message": f"✅ Макс. уровень изменён: {old_max} → {new_max}",
            "admin": f"@{self.admin_username}",
        }

    async def create_manual_deposit(
        self,
        user_identifier: str,
        level: int,
        amount: float,
        reason: str,
    ) -> dict[str, Any]:
        """
        Create a manual deposit for user (admin adjustment).

        SECURITY: TRUSTED ADMIN only!

        Args:
            user_identifier: @username or telegram_id
            level: Deposit level (1-5)
            amount: Amount in USDT
            reason: Reason for manual deposit
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_trusted_admin():
            logger.warning(
                f"AI DEPOSITS SECURITY: Untrusted admin "
                f"{self.admin_telegram_id} attempted to create "
                f"manual deposit"
            )
            return {
                "success": False,
                "error": "❌ Нет прав на создание депозитов вручную",
            }

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        if level < 1 or level > 5:
            return {
                "success": False,
                "error": "❌ Уровень должен быть от 1 до 5",
            }

        if amount <= 0:
            return {
                "success": False,
                "error": "❌ Сумма должна быть положительной",
            }

        if not reason or len(reason) < 5:
            return {
                "success": False,
                "error": "❌ Укажите причину (минимум 5 символов)",
            }

        # Calculate ROI cap (example: 300% for regular deposits)
        roi_multiplier = Decimal("3.0")  # 300%
        roi_cap = Decimal(str(amount)) * roi_multiplier

        # Create deposit
        deposit = Deposit(
            user_id=user.id,
            level=level,
            amount=Decimal(str(amount)),
            deposit_type=f"level_{level}",
            status=TransactionStatus.CONFIRMED.value,
            roi_cap_amount=roi_cap,
            roi_paid_amount=Decimal("0"),
            is_roi_complete=False,
            usdt_confirmed=True,
            usdt_confirmed_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            plex_daily_required=Decimal(str(amount)) * Decimal("10"),
        )
        self.session.add(deposit)

        # Update user total
        user.total_deposited_usdt = (
            user.total_deposited_usdt or Decimal("0")
        ) + Decimal(str(amount))
        user.deposit_tx_count = (user.deposit_tx_count or 0) + 1

        await self.session.commit()

        logger.info(
            f"AI DEPOSITS: Admin {self.admin_telegram_id} created "
            f"manual deposit for user {user.telegram_id}: "
            f"Level {level}, {amount} USDT. Reason: {reason}"
        )

        return {
            "success": True,
            "deposit_id": deposit.id,
            "user": format_user_identifier(user),
            "level": level,
            "amount": amount,
            "roi_cap": float(roi_cap),
            "reason": reason,
            "admin": f"@{self.admin_username}",
            "message": f"✅ Создан ручной депозит #{deposit.id}",
        }

    async def modify_deposit_roi(
        self,
        deposit_id: int,
        new_roi_paid: float | None = None,
        new_roi_cap: float | None = None,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Modify deposit ROI values.

        SECURITY: TRUSTED ADMIN only!

        Args:
            deposit_id: Deposit ID
            new_roi_paid: New ROI paid amount (optional)
            new_roi_cap: New ROI cap amount (optional)
            reason: Reason for modification
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_trusted_admin():
            logger.warning(
                f"AI DEPOSITS SECURITY: Untrusted admin "
                f"{self.admin_telegram_id} attempted to modify "
                f"deposit ROI"
            )
            return {
                "success": False,
                "error": "❌ Нет прав на изменение ROI депозитов",
            }

        deposit = await self.deposit_repo.get_by_id(deposit_id)
        if not deposit:
            return {
                "success": False,
                "error": f"❌ Депозит #{deposit_id} не найден",
            }

        if not reason or len(reason) < 5:
            return {
                "success": False,
                "error": "❌ Укажите причину изменения",
            }

        old_paid = float(deposit.roi_paid_amount or 0)
        old_cap = float(deposit.roi_cap_amount or 0)

        if new_roi_paid is not None:
            if new_roi_paid < 0:
                return {
                    "success": False,
                    "error": "❌ ROI paid не может быть отрицательным",
                }
            deposit.roi_paid_amount = Decimal(str(new_roi_paid))

        if new_roi_cap is not None:
            if new_roi_cap <= 0:
                return {
                    "success": False,
                    "error": "❌ ROI cap должен быть положительным",
                }
            deposit.roi_cap_amount = Decimal(str(new_roi_cap))

        # Check if ROI complete
        if deposit.roi_paid_amount >= deposit.roi_cap_amount:
            deposit.is_roi_complete = True
        else:
            deposit.is_roi_complete = False

        await self.session.commit()

        logger.info(
            f"AI DEPOSITS: Admin {self.admin_telegram_id} modified "
            f"deposit #{deposit_id} ROI: "
            f"paid {old_paid} → {float(deposit.roi_paid_amount)}, "
            f"cap {old_cap} → {float(deposit.roi_cap_amount)}. "
            f"Reason: {reason}"
        )

        return {
            "success": True,
            "deposit_id": deposit_id,
            "old_values": {"roi_paid": old_paid, "roi_cap": old_cap},
            "new_values": {
                "roi_paid": float(deposit.roi_paid_amount),
                "roi_cap": float(deposit.roi_cap_amount),
                "is_complete": deposit.is_roi_complete,
            },
            "reason": reason,
            "admin": f"@{self.admin_username}",
            "message": f"✅ ROI депозита #{deposit_id} изменён",
        }

    async def cancel_deposit(
        self,
        deposit_id: int,
        reason: str,
    ) -> dict[str, Any]:
        """
        Cancel/reject a deposit.

        SECURITY: TRUSTED ADMIN only!

        Args:
            deposit_id: Deposit ID
            reason: Cancellation reason
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Нет прав на отмену депозитов",
            }

        deposit = await self.deposit_repo.get_by_id(deposit_id)
        if not deposit:
            return {
                "success": False,
                "error": f"❌ Депозит #{deposit_id} не найден",
            }

        if deposit.status == TransactionStatus.FAILED.value:
            return {
                "success": False,
                "error": "❌ Депозит уже отменён",
            }

        if not reason or len(reason) < 5:
            return {
                "success": False,
                "error": "❌ Укажите причину отмены",
            }

        old_status = deposit.status
        deposit.status = TransactionStatus.FAILED.value

        # If was confirmed, reduce user's total
        if old_status == TransactionStatus.CONFIRMED.value:
            user = await self.user_repo.get_by_id(deposit.user_id)
            if user:
                user.total_deposited_usdt = max(
                    Decimal("0"),
                    (user.total_deposited_usdt or Decimal("0"))
                    - deposit.amount,
                )

        await self.session.commit()

        logger.warning(
            f"AI DEPOSITS: Admin {self.admin_telegram_id} "
            f"cancelled deposit #{deposit_id}. Reason: {reason}"
        )

        return {
            "success": True,
            "deposit_id": deposit_id,
            "old_status": old_status,
            "new_status": TransactionStatus.FAILED.value,
            "reason": reason,
            "admin": f"@{self.admin_username}",
            "message": f"❌ Депозит #{deposit_id} отменён",
        }

    async def confirm_deposit(
        self,
        deposit_id: int,
        reason: str = "",
    ) -> dict[str, Any]:
        """
        Manually confirm a pending deposit.

        SECURITY: TRUSTED ADMIN only!

        Use when:
        - Deposit stuck in pending due to network issues
        - Manual verification completed
        - Blockchain confirmation received but not detected

        Args:
            deposit_id: Deposit ID
            reason: Confirmation reason/notes
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        if not self._is_trusted_admin():
            logger.warning(
                f"AI DEPOSITS SECURITY: Untrusted admin "
                f"{self.admin_telegram_id} attempted to confirm "
                f"deposit #{deposit_id}"
            )
            return {
                "success": False,
                "error": "❌ Нет прав на подтверждение депозитов",
            }

        deposit = await self.deposit_repo.get_by_id(deposit_id)
        if not deposit:
            return {
                "success": False,
                "error": f"❌ Депозит #{deposit_id} не найден",
            }

        if deposit.status == TransactionStatus.CONFIRMED.value:
            return {
                "success": False,
                "error": "❌ Депозит уже подтверждён",
            }

        if deposit.status == TransactionStatus.FAILED.value:
            return {
                "success": False,
                "error": "❌ Депозит отменён, нельзя подтвердить",
            }

        # Only pending deposits can be confirmed
        allowed_statuses = [
            TransactionStatus.PENDING.value,
            TransactionStatus.PROCESSING.value,
            TransactionStatus.PENDING_NETWORK_RECOVERY.value,
        ]
        if deposit.status not in allowed_statuses:
            return {
                "success": False,
                "error": (
                    f"❌ Статус '{deposit.status}' "
                    f"не позволяет подтвердить"
                ),
            }

        old_status = deposit.status
        deposit.status = TransactionStatus.CONFIRMED.value
        deposit.confirmed_at = datetime.now(UTC)

        # Update user's total_deposited_usdt
        user = await self.user_repo.get_by_id(deposit.user_id)
        if user:
            user.total_deposited_usdt = (
                user.total_deposited_usdt or Decimal("0")
            ) + deposit.amount

        await self.session.commit()

        user_info = (
            f"@{user.username}"
            if user and user.username
            else f"ID:{deposit.user_id}"
        )

        logger.info(
            f"AI DEPOSITS: Admin {self.admin_telegram_id} CONFIRMED "
            f"deposit #{deposit_id} for user {user_info}. "
            f"Amount: {deposit.amount}. Reason: {reason or 'manual'}"
        )

        return {
            "success": True,
            "deposit_id": deposit_id,
            "user": user_info,
            "amount": float(deposit.amount),
            "level": deposit.level,
            "old_status": old_status,
            "new_status": TransactionStatus.CONFIRMED.value,
            "reason": reason or "Ручное подтверждение через ARIA",
            "admin": f"@{self.admin_username}",
            "message": (
                f"✅ Депозит #{deposit_id} подтверждён "
                f"({deposit.amount} USDT)"
            ),
        }
