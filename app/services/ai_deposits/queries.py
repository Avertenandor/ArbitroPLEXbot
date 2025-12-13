"""
AI Deposits Service - Queries Module.

Contains read-only operations for deposits:
- View user deposits
- Get deposit details
- Platform statistics
- Pending deposits
"""

import time
from typing import Any

from loguru import logger
from sqlalchemy import func, select

from app.models.deposit import Deposit
from app.models.enums import TransactionStatus
from app.repositories.global_settings_repository import (
    GlobalSettingsRepository,
)
from app.utils.formatters import format_user_identifier

from .core import AIDepositsServiceCore

# Cache for deposit levels configuration
_levels_cache = None
_levels_cache_time = 0
LEVELS_CACHE_TTL = 300  # 5 minutes


class AIDepositsQueriesService(AIDepositsServiceCore):
    """
    AI Deposits Service - Read Operations.

    All admins can access these methods.
    """

    async def get_deposit_levels_config(self) -> dict[str, Any]:
        """
        Get current deposit levels configuration.

        Returns:
            Levels config with enabled status and limits

        Performance: Uses 5-minute cache to reduce DB queries.
        """
        global _levels_cache, _levels_cache_time

        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Check cache
        current_time = time.time()
        cache_valid = (
            _levels_cache
            and (current_time - _levels_cache_time) < LEVELS_CACHE_TTL
        )
        if cache_valid:
            logger.debug("Returning cached deposit levels config")
            return _levels_cache

        settings_repo = GlobalSettingsRepository(self.session)
        settings = await settings_repo.get_settings()

        # Get level configs from roi_settings
        levels = []
        for level in range(1, 6):
            roi_min = settings.roi_settings.get(
                f"LEVEL_{level}_ROI_MIN",
                "0.8",
            )
            roi_max = settings.roi_settings.get(
                f"LEVEL_{level}_ROI_MAX",
                "10.0",
            )
            roi_mode = settings.roi_settings.get(
                f"LEVEL_{level}_ROI_MODE",
                "custom",
            )

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

        result = {
            "success": True,
            "max_open_level": settings.max_open_deposit_level,
            "levels": levels,
            "message": "📊 Конфигурация уровней депозитов",
        }

        # Update cache
        _levels_cache = result
        _levels_cache_time = current_time
        logger.debug("Cached deposit levels configuration")

        return result

    async def get_user_deposits(
        self,
        user_identifier: str,
    ) -> dict[str, Any]:
        """
        Get all deposits for a specific user.

        Args:
            user_identifier: @username or telegram_id
        """
        logger.info(
            f"AI_DEPOSITS: get_user_deposits called by "
            f"admin_telegram_id={self.admin_telegram_id}, "
            f"admin_data={self.admin_data}"
        )

        admin, error = await self._verify_admin()
        if error:
            logger.warning(f"AI_DEPOSITS: verify_admin failed: {error}")
            return {"success": False, "error": error}

        # Any verified admin can view user deposits
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Недостаточно прав для просмотра депозитов",
            }

        user, error = await self._find_user(user_identifier)
        if error:
            return {"success": False, "error": error}

        # Get deposits
        stmt = (
            select(Deposit)
            .where(Deposit.user_id == user.id)
            .order_by(Deposit.created_at.desc())
        )
        result = await self.session.execute(stmt)
        deposits = list(result.scalars().all())

        deposits_list = []
        for deposit in deposits:
            status_emoji = {
                TransactionStatus.PENDING.value: "⏳",
                TransactionStatus.CONFIRMED.value: "✅",
                TransactionStatus.FAILED.value: "❌",
            }.get(deposit.status, "❓")

            roi_progress = 0
            if (
                deposit.roi_cap_amount
                and deposit.roi_cap_amount > 0
            ):
                roi_paid = deposit.roi_paid_amount or 0
                roi_progress = float(
                    roi_paid / deposit.roi_cap_amount * 100
                )

            tx_hash_short = None
            if deposit.tx_hash:
                tx_hash_short = deposit.tx_hash[:16] + "..."

            created_str = None
            if deposit.created_at:
                created_str = deposit.created_at.strftime("%d.%m.%Y")

            deposits_list.append(
                {
                    "id": deposit.id,
                    "level": deposit.level,
                    "amount": float(deposit.amount),
                    "status": f"{status_emoji} {deposit.status}",
                    "roi_paid": float(deposit.roi_paid_amount or 0),
                    "roi_cap": float(deposit.roi_cap_amount or 0),
                    "roi_progress": f"{roi_progress:.1f}%",
                    "is_roi_complete": deposit.is_roi_complete,
                    "created": created_str,
                    "tx_hash": tx_hash_short,
                }
            )

        total_deposited = sum(
            deposit.amount
            for deposit in deposits
            if deposit.status == TransactionStatus.CONFIRMED.value
        )
        active_count = sum(
            1
            for deposit in deposits
            if (
                deposit.status == TransactionStatus.CONFIRMED.value
                and not deposit.is_roi_complete
            )
        )

        return {
            "success": True,
            "user": format_user_identifier(user),
            "summary": {
                "total_deposited": float(total_deposited),
                "total_count": len(deposits),
                "active_count": active_count,
            },
            "deposits": deposits_list,
            "message": "📊 Депозиты пользователя",
        }

    async def get_pending_deposits(
        self,
        limit: int = 20,
    ) -> dict[str, Any]:
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
            return {
                "success": True,
                "count": 0,
                "deposits": [],
                "message": "✅ Нет ожидающих депозитов",
            }

        deposits_list = []
        for deposit in deposits:
            # Get user
            user = await self.user_repo.get_by_id(deposit.user_id)
            user_info = (
                format_user_identifier(user)
                if user
                else f"ID:{deposit.user_id}"
            )

            tx_hash_short = "N/A"
            if deposit.tx_hash:
                tx_hash_short = deposit.tx_hash[:20] + "..."

            created_str = None
            if deposit.created_at:
                created_str = deposit.created_at.strftime(
                    "%d.%m.%Y %H:%M"
                )

            deposits_list.append(
                {
                    "id": deposit.id,
                    "user": user_info,
                    "level": deposit.level,
                    "amount": float(deposit.amount),
                    "tx_hash": tx_hash_short,
                    "created": created_str,
                }
            )

        return {
            "success": True,
            "count": len(deposits_list),
            "deposits": deposits_list,
            "message": f"⏳ Ожидающих депозитов: {len(deposits_list)}",
        }

    async def get_deposit_details(
        self,
        deposit_id: int,
    ) -> dict[str, Any]:
        """
        Get detailed info about a specific deposit.

        Args:
            deposit_id: Deposit ID
        """
        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Any verified admin can view deposit details
        if not self._is_trusted_admin():
            return {
                "success": False,
                "error": "❌ Недостаточно прав для просмотра деталей",
            }

        deposit = await self.deposit_repo.get_by_id(deposit_id)
        if not deposit:
            return {
                "success": False,
                "error": f"❌ Депозит #{deposit_id} не найден",
            }

        user = await self.user_repo.get_by_id(deposit.user_id)
        user_info = (
            f"@{user.username}"
            if user and user.username
            else f"ID:{deposit.user_id}"
        )

        status_emoji = {
            TransactionStatus.PENDING.value: "⏳ Ожидает",
            TransactionStatus.CONFIRMED.value: "✅ Активен",
            TransactionStatus.FAILED.value: "❌ Отклонён",
        }.get(deposit.status, deposit.status)

        created_str = None
        if deposit.created_at:
            created_str = deposit.created_at.strftime("%d.%m.%Y %H:%M")

        confirmed_str = None
        if deposit.usdt_confirmed_at:
            confirmed_str = deposit.usdt_confirmed_at.strftime(
                "%d.%m.%Y %H:%M"
            )

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
                "created_at": created_str,
                "confirmed_at": confirmed_str,
            },
            "message": f"📋 Детали депозита #{deposit_id}",
        }

    async def get_platform_deposit_stats(self) -> dict[str, Any]:
        """
        Get platform-wide deposit statistics.
        """
        from decimal import Decimal

        admin, error = await self._verify_admin()
        if error:
            return {"success": False, "error": error}

        # Total confirmed deposits
        total_stmt = select(
            func.count(Deposit.id),
            func.sum(Deposit.amount),
        ).where(Deposit.status == TransactionStatus.CONFIRMED.value)
        total_result = await self.session.execute(total_stmt)
        total_row = total_result.one()
        total_count = total_row[0] or 0
        total_amount = total_row[1] or Decimal("0")

        # By level
        level_stmt = (
            select(
                Deposit.level,
                func.count(Deposit.id),
                func.sum(Deposit.amount),
            )
            .where(Deposit.status == TransactionStatus.CONFIRMED.value)
            .group_by(Deposit.level)
            .order_by(Deposit.level)
        )

        level_result = await self.session.execute(level_stmt)
        by_level = [
            {
                "level": row[0],
                "count": row[1],
                "amount": float(row[2] or 0),
            }
            for row in level_result.all()
        ]

        # Pending
        pending_stmt = select(func.count(Deposit.id)).where(
            Deposit.status == TransactionStatus.PENDING.value
        )
        pending_result = await self.session.execute(pending_stmt)
        pending_count = pending_result.scalar() or 0

        # Active (ROI not complete)
        active_stmt = select(func.count(Deposit.id)).where(
            Deposit.status == TransactionStatus.CONFIRMED.value,
            Deposit.is_roi_complete == False,  # noqa: E712
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
