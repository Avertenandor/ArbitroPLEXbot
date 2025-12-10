"""
AI Deposits Management Service.

Provides comprehensive deposit management for AI assistant:
- View deposits (user, platform-wide)
- Create/modify deposits (TRUSTED ADMINS ONLY)
- Level management
- Pending deposits

SECURITY: Deposit modifications require TRUSTED_ADMIN access.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.models.user import User
from app.repositories.admin_repository import AdminRepository
from app.repositories.deposit_repository import DepositRepository
from app.repositories.global_settings_repository import GlobalSettingsRepository
from app.repositories.user_repository import UserRepository


class AIDepositsService:
    """
    AI-powered deposits management service.

    Provides full deposit management for ARIA.
    ALL ADMINS are now trusted to manage deposits via ARIA.
    """

    def __init__(
        self,
        session: AsyncSession,
        admin_data: dict[str, Any] | None = None,
    ):
        self.session = session
        self.admin_data = admin_data or {}
        self.admin_telegram_id = self.admin_data.get("ID")
        self.admin_username = self.admin_data.get("username")
        self.deposit_repo = DepositRepository(session)
        self.user_repo = UserRepository(session)

    async def _verify_admin(self) -> tuple[Any | None, str | None]:
        """Verify admin credentials."""
        if not self.admin_telegram_id:
            return None, "❌ Не удалось определить администратора"

        admin_repo = AdminRepository(self.session)
        admin = await admin_repo.get_by_telegram_id(self.admin_telegram_id)

        if not admin or admin.is_blocked:
            return None, "❌ Администратор не найден или заблокирован"

        return admin, None

    def _is_trusted_admin(self) -> bool:
        """Check if current admin can modify deposits. ALL admins are trusted."""
        # Все админы доверенные — просто проверяем что есть telegram_id
        return self.admin_telegram_id is not None

    async def _find_user(self, identifier: str) -> tuple[User | None, str | None]:
        """Find user by @username or telegram_id."""
        identifier = identifier.strip()

        if identifier.startswith("@"):
            username = identifier[1:]
            user = await self.user_repo.get_by_username(username)
            if user:
                return user, None
            return None, f"❌ Пользователь @{username} не найден"

        if identifier.isdigit():
            telegram_id = int(identifier)
            user = await self.user_repo.get_by_telegram_id(telegram_id)
            if user:
                return user, None
            return None, f"❌ Пользователь с ID {telegram_id} не найден"

        return None, "❌ Укажите @username или telegram_id"

    # ========================================================================
    # READ OPERATIONS (All admins)
    # ========================================================================

    async def get_deposit_levels_config(self) -> dict[str, Any]:
        """
        Get current deposit levels configuration.

        Returns:
            Levels config with enabled status and limits
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        settings_repo = GlobalSettingsRepository(self.session)
        settings = await settings_repo.get_settings()

        # Get level configs from roi_settings
        levels = []
        for level in range(1, 6):
            roi_min = settings.roi_settings.get(f"LEVEL_{level}_ROI_MIN", "0.8")
            roi_max = settings.roi_settings.get(f"LEVEL_{level}_ROI_MAX", "10.0")
            roi_mode = settings.roi_settings.get(f"LEVEL_{level}_ROI_MODE", "custom")

            # Level thresholds (approximate)
            thresholds = {
                1: (30, 499),
                2: (500, 999),
                3: (1000, 2999),
                4: (3000, 4999),
                5: (5000, 100000),
            }
            min_amount, max_amount = thresholds.get(level, (0, 0))

            is_enabled = level <= settings.max_open_deposit_level

            levels.append(
                {
                    "level": level,
                    "enabled": is_enabled,
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "roi_min": float(roi_min),
                    "roi_max": float(roi_max),
                    "roi_mode": roi_mode,
                }
            )

        return {
            "success": True,
            "max_open_level": settings.max_open_deposit_level,
            "levels": levels,
            "message": "📊 Конфигурация уровней депозитов",
        }

    async def get_user_deposits(self, user_identifier: str) -> dict[str, Any]:
        """
        Get all deposits for a specific user.

        Args:
            user_identifier: @username or telegram_id
        """
        from loguru import logger

        logger.info(
            f"AI_DEPOSITS: get_user_deposits called by admin_telegram_id={self.admin_telegram_id}, admin_data={self.admin_data}"
        )

        admin, error = await self._verify_admin()
        if error:
            logger.warning(f"AI_DEPOSITS: verify_admin failed: {error}")
            return {"success": False, "error": error}

        # Only trusted admins can view user deposits
        if not self._is_trusted_admin():
            logger.warning(f"AI_DEPOSITS: admin {self.admin_telegram_id} not in TRUSTED_ADMIN_IDS={TRUSTED_ADMIN_IDS}")
            return {"success": False, "error": "❌ Недостаточно прав для просмотра депозитов"}

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        # Get deposits
        stmt = select(Deposit).where(Deposit.user_id == user.id).order_by(Deposit.created_at.desc())
        result = await self.session.execute(stmt)
        deposits = list(result.scalars().all())

        deposits_list = []
        for d in deposits:
            status_emoji = {
                TransactionStatus.PENDING.value: "⏳",
                TransactionStatus.CONFIRMED.value: "✅",
                TransactionStatus.FAILED.value: "❌",
            }.get(d.status, "❓")

            roi_progress = 0
            if d.roi_cap_amount and d.roi_cap_amount > 0:
                roi_progress = float((d.roi_paid_amount or 0) / d.roi_cap_amount * 100)

            deposits_list.append(
                {
                    "id": d.id,
                    "level": d.level,
                    "amount": float(d.amount),
                    "status": f"{status_emoji} {d.status}",
                    "roi_paid": float(d.roi_paid_amount or 0),
                    "roi_cap": float(d.roi_cap_amount or 0),
                    "roi_progress": f"{roi_progress:.1f}%",
                    "is_roi_complete": d.is_roi_complete,
                    "created": d.created_at.strftime("%d.%m.%Y") if d.created_at else None,
                    "tx_hash": d.tx_hash[:16] + "..." if d.tx_hash else None,
                }
            )

        total_deposited = sum(d.amount for d in deposits if d.status == TransactionStatus.CONFIRMED.value)
        active_count = sum(
            1 for d in deposits if d.status == TransactionStatus.CONFIRMED.value and not d.is_roi_complete
        )

        return {
            "success": True,
            "user": f"@{user.username}" if user.username else f"ID:{user.telegram_id}",
            "summary": {
                "total_deposited": float(total_deposited),
                "total_count": len(deposits),
                "active_count": active_count,
            },
            "deposits": deposits_list,
            "message": "📊 Депозиты пользователя",
        }

    async def get_pending_deposits(self, limit: int = 20) -> dict[str, Any]:
        """
        Get pending deposits awaiting confirmation.

        Args:
            limit: Max results
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        stmt = (
            select(Deposit)
            .where(Deposit.status == TransactionStatus.PENDING.value)
            .order_by(Deposit.created_at.asc())
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        deposits = list(result.scalars().all())

        if not deposits:
            return {"success": True, "count": 0, "deposits": [], "message": "✅ Нет ожидающих депозитов"}

        deposits_list = []
        for d in deposits:
            # Get user
            user = await self.user_repo.get_by_id(d.user_id)
            user_info = f"@{user.username}" if user and user.username else f"ID:{d.user_id}"

            deposits_list.append(
                {
                    "id": d.id,
                    "user": user_info,
                    "level": d.level,
                    "amount": float(d.amount),
                    "tx_hash": d.tx_hash[:20] + "..." if d.tx_hash else "N/A",
                    "created": d.created_at.strftime("%d.%m.%Y %H:%M") if d.created_at else None,
                }
            )

        return {
            "success": True,
            "count": len(deposits_list),
            "deposits": deposits_list,
            "message": f"⏳ Ожидающих депозитов: {len(deposits_list)}",
        }

    async def get_deposit_details(self, deposit_id: int) -> dict[str, Any]:
        """
        Get detailed info about a specific deposit.

        Args:
            deposit_id: Deposit ID
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Only trusted admins can view deposit details
        if not self._is_trusted_admin():
            return {"success": False, "error": "❌ Недостаточно прав для просмотра деталей депозита"}

        deposit = await self.deposit_repo.get_by_id(deposit_id)
        if not deposit:
            return {"success": False, "error": f"❌ Депозит #{deposit_id} не найден"}

        user = await self.user_repo.get_by_id(deposit.user_id)
        user_info = f"@{user.username}" if user and user.username else f"ID:{deposit.user_id}"

        status_emoji = {
            TransactionStatus.PENDING.value: "⏳ Ожидает",
            TransactionStatus.CONFIRMED.value: "✅ Активен",
            TransactionStatus.FAILED.value: "❌ Отклонён",
        }.get(deposit.status, deposit.status)

        return {
            "success": True,
            "deposit": {
                "id": deposit.id,
                "user": user_info,
                "user_id": deposit.user_id,
                "level": deposit.level,
                "amount": float(deposit.amount),
                "status": status_emoji,
                "deposit_type": deposit.deposit_type,
                "roi_paid": float(deposit.roi_paid_amount or 0),
                "roi_cap": float(deposit.roi_cap_amount or 0),
                "is_roi_complete": deposit.is_roi_complete,
                "tx_hash": deposit.tx_hash,
                "from_address": deposit.from_address,
                "block_number": deposit.block_number,
                "created_at": deposit.created_at.strftime("%d.%m.%Y %H:%M") if deposit.created_at else None,
                "confirmed_at": deposit.usdt_confirmed_at.strftime("%d.%m.%Y %H:%M")
                if deposit.usdt_confirmed_at
                else None,
            },
            "message": f"📋 Детали депозита #{deposit_id}",
        }

    async def get_platform_deposit_stats(self) -> dict[str, Any]:
        """
        Get platform-wide deposit statistics.
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Total confirmed deposits
        total_stmt = select(func.count(Deposit.id), func.sum(Deposit.amount)).where(
            Deposit.status == TransactionStatus.CONFIRMED.value
        )
        total_result = await self.session.execute(total_stmt)
        total_row = total_result.one()
        total_count = total_row[0] or 0
        total_amount = total_row[1] or Decimal("0")

        # By level
        level_stmt = (
            select(Deposit.level, func.count(Deposit.id), func.sum(Deposit.amount))
            .where(Deposit.status == TransactionStatus.CONFIRMED.value)
            .group_by(Deposit.level)
            .order_by(Deposit.level)
        )

        level_result = await self.session.execute(level_stmt)
        by_level = [{"level": row[0], "count": row[1], "amount": float(row[2] or 0)} for row in level_result.all()]

        # Pending
        pending_stmt = select(func.count(Deposit.id)).where(Deposit.status == TransactionStatus.PENDING.value)
        pending_result = await self.session.execute(pending_stmt)
        pending_count = pending_result.scalar() or 0

        # Active (ROI not complete)
        active_stmt = select(func.count(Deposit.id)).where(
            Deposit.status == TransactionStatus.CONFIRMED.value, Deposit.is_roi_complete == False
        )
        active_result = await self.session.execute(active_stmt)
        active_count = active_result.scalar() or 0

        return {
            "success": True,
            "stats": {
                "total_count": total_count,
                "total_amount": float(total_amount),
                "pending_count": pending_count,
                "active_count": active_count,
            },
            "by_level": by_level,
            "message": "📊 Статистика депозитов платформы",
        }

    # ========================================================================
    # WRITE OPERATIONS (TRUSTED ADMINS ONLY)
    # ========================================================================

    async def change_max_deposit_level(self, new_max: int) -> dict[str, Any]:
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
                f"AI DEPOSITS SECURITY: Untrusted admin {self.admin_telegram_id} attempted to change max level"
            )
            return {"success": False, "error": "❌ Нет прав на изменение настроек депозитов"}

        if new_max < 1 or new_max > 5:
            return {"success": False, "error": "❌ Уровень должен быть от 1 до 5"}

        settings_repo = GlobalSettingsRepository(self.session)
        old_settings = await settings_repo.get_settings()
        old_max = old_settings.max_open_deposit_level

        await settings_repo.update_settings(max_open_deposit_level=new_max)
        await self.session.commit()

        logger.info(f"AI DEPOSITS: Admin {self.admin_telegram_id} changed max level: {old_max} → {new_max}")

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
                f"AI DEPOSITS SECURITY: Untrusted admin {self.admin_telegram_id} attempted to create manual deposit"
            )
            return {"success": False, "error": "❌ Нет прав на создание депозитов вручную"}

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        if level < 1 or level > 5:
            return {"success": False, "error": "❌ Уровень должен быть от 1 до 5"}

        if amount <= 0:
            return {"success": False, "error": "❌ Сумма должна быть положительной"}

        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину (минимум 5 символов)"}

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
        user.total_deposited_usdt = (user.total_deposited_usdt or Decimal("0")) + Decimal(str(amount))
        user.deposit_tx_count = (user.deposit_tx_count or 0) + 1

        await self.session.commit()

        logger.info(
            f"AI DEPOSITS: Admin {self.admin_telegram_id} created manual deposit "
            f"for user {user.telegram_id}: Level {level}, {amount} USDT. Reason: {reason}"
        )

        return {
            "success": True,
            "deposit_id": deposit.id,
            "user": f"@{user.username}" if user.username else f"ID:{user.telegram_id}",
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
                f"AI DEPOSITS SECURITY: Untrusted admin {self.admin_telegram_id} attempted to modify deposit ROI"
            )
            return {"success": False, "error": "❌ Нет прав на изменение ROI депозитов"}

        deposit = await self.deposit_repo.get_by_id(deposit_id)
        if not deposit:
            return {"success": False, "error": f"❌ Депозит #{deposit_id} не найден"}

        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину изменения"}

        old_paid = float(deposit.roi_paid_amount or 0)
        old_cap = float(deposit.roi_cap_amount or 0)

        if new_roi_paid is not None:
            if new_roi_paid < 0:
                return {"success": False, "error": "❌ ROI paid не может быть отрицательным"}
            deposit.roi_paid_amount = Decimal(str(new_roi_paid))

        if new_roi_cap is not None:
            if new_roi_cap <= 0:
                return {"success": False, "error": "❌ ROI cap должен быть положительным"}
            deposit.roi_cap_amount = Decimal(str(new_roi_cap))

        # Check if ROI complete
        if deposit.roi_paid_amount >= deposit.roi_cap_amount:
            deposit.is_roi_complete = True
        else:
            deposit.is_roi_complete = False

        await self.session.commit()

        logger.info(
            f"AI DEPOSITS: Admin {self.admin_telegram_id} modified deposit #{deposit_id} ROI: "
            f"paid {old_paid} → {float(deposit.roi_paid_amount)}, "
            f"cap {old_cap} → {float(deposit.roi_cap_amount)}. Reason: {reason}"
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
            return {"success": False, "error": "❌ Нет прав на отмену депозитов"}

        deposit = await self.deposit_repo.get_by_id(deposit_id)
        if not deposit:
            return {"success": False, "error": f"❌ Депозит #{deposit_id} не найден"}

        if deposit.status == TransactionStatus.FAILED.value:
            return {"success": False, "error": "❌ Депозит уже отменён"}

        if not reason or len(reason) < 5:
            return {"success": False, "error": "❌ Укажите причину отмены"}

        old_status = deposit.status
        deposit.status = TransactionStatus.FAILED.value

        # If was confirmed, reduce user's total
        if old_status == TransactionStatus.CONFIRMED.value:
            user = await self.user_repo.get_by_id(deposit.user_id)
            if user:
                user.total_deposited_usdt = max(
                    Decimal("0"), (user.total_deposited_usdt or Decimal("0")) - deposit.amount
                )

        await self.session.commit()

        logger.warning(f"AI DEPOSITS: Admin {self.admin_telegram_id} cancelled deposit #{deposit_id}. Reason: {reason}")

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
                f"AI DEPOSITS SECURITY: Untrusted admin {self.admin_telegram_id} "
                f"attempted to confirm deposit #{deposit_id}"
            )
            return {"success": False, "error": "❌ Нет прав на подтверждение депозитов"}

        deposit = await self.deposit_repo.get_by_id(deposit_id)
        if not deposit:
            return {"success": False, "error": f"❌ Депозит #{deposit_id} не найден"}

        if deposit.status == TransactionStatus.CONFIRMED.value:
            return {"success": False, "error": "❌ Депозит уже подтверждён"}

        if deposit.status == TransactionStatus.FAILED.value:
            return {"success": False, "error": "❌ Депозит отменён, нельзя подтвердить"}

        # Only pending deposits can be confirmed
        if deposit.status not in [
            TransactionStatus.PENDING.value,
            TransactionStatus.PROCESSING.value,
            TransactionStatus.PENDING_NETWORK_RECOVERY.value,
        ]:
            return {"success": False, "error": f"❌ Статус '{deposit.status}' не позволяет подтвердить"}

        old_status = deposit.status
        deposit.status = TransactionStatus.CONFIRMED.value
        deposit.confirmed_at = datetime.now(UTC)

        # Update user's total_deposited_usdt
        user = await self.user_repo.get_by_id(deposit.user_id)
        if user:
            user.total_deposited_usdt = (user.total_deposited_usdt or Decimal("0")) + deposit.amount

        await self.session.commit()

        user_info = f"@{user.username}" if user and user.username else f"ID:{deposit.user_id}"

        logger.info(
            f"AI DEPOSITS: Admin {self.admin_telegram_id} CONFIRMED deposit #{deposit_id} "
            f"for user {user_info}. Amount: {deposit.amount}. Reason: {reason or 'manual'}"
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
            "message": f"✅ Депозит #{deposit_id} подтверждён ({deposit.amount} USDT)",
        }
